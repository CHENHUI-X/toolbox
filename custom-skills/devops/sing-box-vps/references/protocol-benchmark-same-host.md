# 同机多协议对比实测方法论（2026-09-15 实测）

用户问"这几种协议哪个最快"。在服务器本机起 5 个单节点 sing-box 实例（每协议一个本地 mixed 入站 18001-18005）做延迟+下载对比。

## 出站配置字段陷阱（手写测试配置必错清单）

| 协议 | 客户端出站关键字段 | 易错点 |
|---|---|---|
| vless-reality | uuid + flow: xtls-rprx-vision + tls.reality{public_key, short_id} + utls fingerprint | short_id 必须用 sb.json 真值；**本机回环连接可能报 reality verification failed——这是环境假失败（hairpin 依赖），不是服务端坏**：同机经公网域名自连也可能成功，成功即服务端+真实路径的强豁免证据；失败时判"未定"，换对机实测或看真实用户连接，不要据失败下服务端故障的结论。优先复用已验证的测试配置（如 /tmp/qqg-itunes-test.json）而不是手写出站 |
| vmess | uuid + transport{type: ws, path: sb.json 真值, max_early_data, early_data_header_name} | **2082 端口服务器端 tls.enabled=false（ws 明文）**——客户端挂 tls 必报 "first record does not look like a TLS handshake" |
| hysteria2 | **password**（不是 uuid）| 写 uuid 直接 FATAL unknown field "uuid" |
| tuic | uuid + password + congestion_control: bbr + tls.alpn=["h3"] | 缺 alpn h3 报 CRYPTO_ERROR no application protocol |
| anytls | **password**（不是 uuid）| 同 hy2 |

字段真值一律从 `/etc/s-box/sb.json` inbounds 读（hy2/anytls 的 password 就是 UUID 格式，但字段名不同），别猜。

## 实测结论（QQG，同机同出口）

- 延迟（curl 204 三次取最优）：HY2 0.198s ≈ ANYTLS 0.200s ≈ TUIC 0.200s < VMESS-WS 0.454s（多一层 ws 升级）。VLESS 回环 4.7s 是假象，真实用户路径 51ms 最快
- 下载 10MB（cloudflare __down）：五个全部 ~1.8MB/s——回环瓶颈。**同机带宽测速对协议无区分度**：协议开销不是瓶颈，用户↔服务器线路质量才是
- 给用户的口径：**日常 VLESS-REALITY；丢包/晚高峰切 HY2/TUIC（QUIC 系抗丢包）；VMESS-WS 仅备用穿透**

## 测试流程

1. 从 sb.json 读 5 协议参数，生成 5 个单节点配置（入站 mixed 127.0.0.1:1800x，出站各协议）
2. 后台起 5 个 sing-box 实例（terminal background=true——前台命令带 `&` 会被拒）
3. `curl -x socks5h://127.0.0.1:PORT -w "%{http_code} %{time_total}" https://www.gstatic.com/generate_204` 各 3 次取最优
4. 下载测试仅验证连通性，回环无区分度
5. 测完 `pkill -f proto-` 清理实例，`ss -tlnp | grep 1800` 确认清零

## 中断与恢复

- 测试中途被用户打断（"死了？"）后实例仍存活：**先 `ss -tlnp | grep 1800` 确认状态再决定重启还是续跑**，不要从头重来（9-19 实测 5 实例全活着，直接续跑测试即可）
- 大量 ssh 弹幕式 null 日志 = tuic 服务器在刷 CRYPTO_ERROR，属正常重试噪音，看 tail 即可
- 被打断后继续测试：用同一批端口续测，别再起新实例叠加占端口
