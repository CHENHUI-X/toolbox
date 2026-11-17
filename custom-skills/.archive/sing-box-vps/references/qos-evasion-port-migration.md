# QoS 规避·全协议端口迁移实录（2026-09-21 QQG 迁入 443 区）

**背景**：用户报"几个端口全失败"，实况 = 服务端满血（出口实测 194Mbps、BBR+fq、32MB 缓冲、单核零负载），瓶颈在中国联通↔拉斯维加斯的国际段 QoS——TLS 握手包被丢（130+ 次到达、0 次完成转发）。服务端无性能可榨时的可控手段 = **端口特征降威胁**：把全部协议从随机高位端口迁入"正常网站"端口区，降低被 QoS 指纹识别的概率。

## 先排除假提速方案（用户问过"套 CF 或 WARP 能提速吗"）

- **套 CF（橙云）**：CF 只代理 HTTP(S)/WS 流量，REALITY/TUIC/HY2 **全部不可用**，只能降级成 ws+tls（=订阅里最慢的 VMESS 模式）；免费版中国用户被分到美西入口再绕 CF 骨干，180-250ms 起步。唯一价值是隐藏源站 IP（自用不需要）。
- **WARP**：不改变用户↔服务器段（这段才是瓶颈），中国直连 WARP 无国内节点、丢包严重。
- 判定口径：两者都是"绕路"不是"抄近路"，对中转链路 QoS 无解。真正治本 = 9929/CN2 GIA 中转跳板（国内优质入口→专线→美西）。

## QQG 端口迁移表（2026-09-21 生效）

| 协议 | 旧端口 | 新端口 | 说明 |
|---|---|---|---|
| VLESS-REALITY | 54132 | **443/tcp** | 标准 HTTPS 口，伪装最强 |
| VMESS-WS | 2082 | **2053/tcp** | CF 风格 HTTPS 口 |
| HY2 | 22487 | **8443/udp** | 常见备用 HTTPS |
| TUIC | 53039 | **8843/udp** | 同上 |
| ANYTLS | 48124 | **8443/tcp** | 与 HY2 共端口号，tcp/udp 不冲突 |

GCP 五节点端口未动（33741/2096/65083/53900/29624）。

## 迁移流程（实测顺序）

1. 备份：`cp /etc/s-box/sb.json{,.bak-port-change}`，两份 clash 订阅同做
2. 改 `/etc/s-box/sb.json` 各 inbound 的 `listen_port`（python 逐字段改）
3. 订阅端口同步：merged-sub.yaml + aws-sub.yaml + clmi.yaml（QQG 侧分发面 = 这三份；sub-links-plain.txt 是存档不算真源）
4. 订阅服务让位：443 上的 subscription-server 挪 80 —— sed systemd ExecStart 端口参数 + `systemctl daemon-reload`
5. `systemctl restart sing-box subscription-server`
6. 验证链：`ss -tulnp`（tcp 443/2053/8443 + udp 8443/8843）→ 5 协议端到端 204（公网回环法见 protocol-benchmark-same-host.md）→ 外网视角 curl 订阅 200

## 迁移坑（本次全踩过）

1. **blanket sed 按端口号全局替换会跨节点串改**：`sed 's/  port: 2053/  port: 8443/g'` 不看节点名，把 [AWS] VMESS 的 2053 也改成 8443、HY2 串成 2096。**必须按节点名锚定逐个替换**：
   ```python
   re.sub(r"(- name: '\[AWS\] VMESS'\n(?:.*\n)*?  port: )8443", r"\g<1>2053", s)
   ```
   改完必须 `yaml.safe_load` 逐节点打印 name+port 人工核对（本次靠这步抓出两处串改）。
2. **同端口号只允许 tcp/udp 错开**：vmess(2053/tcp) 与 anytls(2053/tcp) 同端口 → sing-box `FATAL: bind: address already in use` → **整个服务起不来**（不是单协议挂，全部节点断）。分配端口先列 tcp/udp 再排。
3. **端口让位后的僵尸进程**：订阅服务挪端口后，重启前的旧手动实例仍占目标端口 → `OSError: [Errno 98] Address already in use`，服务 activating 循环。`ss -tlnp | grep :80` 找旧 pid，kill 后再 restart。
4. **GCP 侧若做同款迁移**：QQG 无云防火墙限制，但 GCP 必须同步 gcloud 放行新端口（tcp/udp 分开），否则本机通、公网不通（假象排查见 sing-box-node-check 技能）。

## ⚠️ 端口迁移的即时代价

**旧端口节点 100% 立即失效**，所有现存客户端在重拉订阅前全部超时——迁移 = 强制全体用户重拉。给这个用户做迁移必须同步发新订阅链接并明确说"强制更新"（他的历史行为：不重拉、拿旧参数敲门、然后报"全坏了"）。

## 手机端配套（免费提速，迁移时一并发给用户）

- Stash **强制重拉订阅**（端口变了必须重拉）
- VLESS 详情页开 **mux 多路复用**（丢包线上网页场景明显提速）
- 晚 8–11 点国际出口 QoS 高峰，大下载错峰到深夜/清晨

## 未验证项（诚实口径）

服务端全链路已验证：监听 ✓、回环 5×204 ✓、外网订阅 200 ✓。**用户真实路径的提速效果未回访确认**——443 区低威胁是理论依据，非实测结论。回访若仍超时，先查用户是否重拉了订阅（旧端口节点必然全失败），再查路径质量（见 china-line-quality-diagnosis.md）。
