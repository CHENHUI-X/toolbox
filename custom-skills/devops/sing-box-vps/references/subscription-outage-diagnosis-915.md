# "订阅全部超时"排查补遗（2026-09-15 实战）

接 subscription-outage-diagnosis.md 的判定表，补两个当天的进阶结论。

## 第三种故障形态：REALITY 握手挂起（非拒非成）

journalctl 里客户端 TCP 能连上、`inbound connection from <IP>` 正常打印，但**之后零日志**（无 invalid、无 connection to），0ms 即无后续，同 IP 几小时重复上千次（实测 1269 到达/0 完成/0 拒绝）。

**鉴别**：≠被拒（invalid=参数错）、≠服务端挂（本地订阅参数实测 204 通）。是客户端→服务端路径上 REALITY TLS 握手往返被丢（中国出口 QoS 对握手包特征识别），服务端两端都好，纯路径问题。

**处置**：服务端无解（BBR/fq 兜不住握手中段丢包）；让用户**切另一台机器的节点**（不同路径独立路况）或等出口 IP 更换/时段变化。

## 多机排查的对机验证纪律

- 从 QQG 对 GCP 旧 IP 测端口全 timeout 是**必然**的，别当成"GCP 挂了"的证据——用 peer dm 让 GCP 自查（`curl api.ipify.org` + metadata external-ip + `systemctl is-active sing-box`）。
- GCP 临时 IP 变更已有开机自检 service（gcp-ip-check-boot）+ DDNS 全域名化自动兜住；怀疑 DNS 缓存残留时，对 223.5/119.29/114/8.8.8.8/1.1.1.1 五大公共 DNS 逐一解析订阅域名验证（全部返回新 IP = 无残留）。
- 本机订阅文件未必含全部节点（aws-sub.yaml 只有 QQG 5 件套，GCP 5 件套在 GCP 侧分发）——先对齐节点清单再排查。

## 单源测速的反面教训（补 china-line-quality-diagnosis.md）

QQG 线路对华为云镜像实测 49MB/s、走 vless 代理 37MB/s——之前"中国方向 0.5~3MB/s 天花板"的结论是被腾讯 CDN 单源限速骗了。测中国方向带宽**至少用华为云镜像 + 清华 TUNA 两个源**（华为云对海外最慷慨，常给出真实干线速度）。

## 用户沟通纪律（9/15 挨骂复盘）

- 用户说"这个 IP/这个节点"没指名机器时，**先确认是哪台再答**——把 QQG 的 IP 问题答成 GCP 会挨骂（"你他妈是qqg 傻逼"）。
- 用户催（"快点""死了？""草"）= 直接给当前最优结论 + 一句依据，不再铺排查过程。
- 答疑结构：结论先行一两句，表格证据放后面；发现自己答错立刻认错纠正，别绕。

## 9/19-20 追补（同一诊断树再长两支）

- **第四形态——客户端旧节点残留**（服务端无罪）：sb.json 真值 ≡ 订阅参数逐字一致、5 协议端到端全 204，用户仍秒拒 invalid 130+/0 成功 → Stash 残留旧订阅/手加节点在用旧参数敲门。修复全在客户端（删旧订阅+强制更新），详见 `references/reality-client-stale-params.md`。加上原文的握手挂起，REALITY 故障形态集齐：秒拒=参数不匹配（服务端旧钥或客户端旧参数两种方向）、5m30s 挂=伪装站被断、零后续挂起=路径 QoS 丢握手、全通仍拒=客户端残留。
- **" Give me the subscription"类交付前必修分发文件**：用户要订阅链接时先 curl 实测入口 200 + 检查该入口实际指向的文件（merged-sub.yaml 而非 aws-sub.yaml！）里规则源是否已镜像化——9/19 就是给链接时才发现 merged-sub 的 18 条规则源还是 raw，当场修完再交付（含 blackmatrix7 ChinaMax 非 ACL4SSR 的 raw 源）。
- **多文件同步陷阱复发两次**：镜像化/改参数类变更必须 `grep -rn` 枚举 /etc/s-box/ 全部分发文件，"只改了记得的那份"已造成 9/15、9/19 两次问题复发。
- **用户出口 IP 5 天换 5 个**（218.12.29.95→218.12.27.55→123.124.194.215→124.126.141.113→61.148.244.244）：统计用户连接必须先枚举全部来源 IP，且 `to` 完成行不含客户端 IP（按用户 grep 成功数恒 0），用 [reqid] 关联。

## 服务端豁免两步法（全超时、要快速归因时）

服务端排查收敛为两步；两步都过就停止动服务端——故障必在手机/客户端侧（旧订阅残留、key 错、手机网络对 UDP 的 QoS），此时服务端任何改动都是瞎修：

1. **真值客户端实测（豁免服务端+真实路径）**：从 `/etc/s-box/sb.json` inbounds 真值生成临时 sing-box 客户端配置（本地 socks 入站 + 单协议出站，REALITY public_key/short_id 用服务器真值），`terminal(background=true)` 起进程，`curl -x socks5h://127.0.0.1:<port> http://www.gstatic.com/generate_204` 实测 204 + 出口 IP 正确即通过；测完 kill 进程并 `ss -tlnp` 确认端口清零。字段陷阱见 `references/protocol-benchmark-same-host.md`。
2. **分发文件逐字段 diff（豁免订阅）**：订阅 yaml vs sb.json 逐协议核对 uuid/password、vmess ws path（前缀一致，`?ed=` 后缀可差异）、tuic alpn h3、vless flow、REALITY public-key/short-id——全一致即通过。

配套判定：

- **扫描器噪音 ≠ 故障**：journal 里扫描段 IP 的 `REALITY: processed invalid`、anytls `unknown user password`、TLS handshake 报错是背景噪音；判健康只看真实用户 IP 的 INFO `inbound connection` 成功线 + 端到端探针，不看 ERROR 量。
- **中国方向 DNS 污染排查**：对 223.5.5.5/119.29.29.29/114.114.114.114 用 python 原生 UDP DNS 查询（无 dig/nslookup 也能跑）逐一解析订阅域名，全部返回服务器真 IP = 无污染。
- **订阅 key 401 ≠ 节点坏**：各机 sub-key 相互独立，订阅更新 401 只影响拉配置，已缓存节点照常工作；向用户汇报时把两者分开说。
