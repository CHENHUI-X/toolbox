# VLESS REALITY 超时诊断：握手目标站被线路阻断（2026-09-06 实战）

**症状**：用户报 hy2/tuic/vless 三节点超时。GCP 节点正常，QQG(50.114.172.17, FASTNET DDoS 防护线路) 节点全挂。

**根因**：QQG 线路 → apple.com (17.253.144.10, Akamai) 的 **TCP 三次握手成功但 TLS 握手（ClientHello 后）永远无响应**。REALITY 服务端握手时要实时连伪装站 (apple.com:443) 借证书 → 服务端卡死在 dial 半路 → 客户端表现为"超时"。itunes.apple.com / www.google.com / www.cloudflare.com 同机同刻全部毫秒级 TLS 通过 —— 只有 apple.com 主域这个 CDN 端点被丢。

## 与"凭据不匹配"的鉴别（同样报 invalid connection，两码事）

| 信号 | 旧钥/参数不匹配 | 握手目标被阻断（本次） |
|---|---|---|
| invalid connection 出现延迟 | 秒拒（<1s） | **~5m30s 才报**（服务端 dial 目标站挂住到超时） |
| 服务端→伪装站:443 | 正常 | TCP 通，TLS 永远超时（openssl / python ssl 复现一致） |
| 同机其他 TLS 站 | 正常 | 正常（只有伪装站异常） |

服务端本机决定性测试：
```bash
timeout 8 openssl s_client -connect apple.com:443 -servername apple.com </dev/null 2>&1 | head -3
python3 -c "import socket,ssl; s=socket.create_connection(('apple.com',443),timeout=5); ssl.create_default_context().wrap_socket(s,server_hostname='apple.com')"
# 对照组: itunes.apple.com / www.bing.com 应秒通
```
干扰项提示：ping -s 1472 -M do 丢包但 1200 通（PMTU 略小）与 TLS 挂无因果关系，别被带偏。

## 修复

**方案 B（推荐）：不对称配置，客户端零操作**
REALITY 的 `tls.server_name`（校验客户端 SNI）和 `reality.handshake.server`（借证书的目标）**可以不同**。保留 `server_name=apple.com`（旧客户端带旧 sni 照样通过校验），只把 `handshake.server` 改成实测通的站：
```json
"tls": {"server_name": "apple.com",
        "reality": {"handshake": {"server": "itunes.apple.com", "server_port": 443}, ...}}
```
重启 sing-box 后，拿着旧参数（旧 sni）的客户端**立即恢复**，实测 204/33ms、带宽 100MB/s+。适用场景：用户不配合重拉订阅 / 手机端懒得动 / 先恢复服务再说。

⚠️ **铁律：订阅文件里的 sni 必须永远等于 `tls.server_name`（校验名），绝不能同步成 `handshake.server`** —— 把订阅 sni 同步成 itunes.apple.com 曾导致重拉订阅的用户全被秒拒（二次事故复盘见 reality-asymmetric-sni-rule.md）。

**方案 A（对称）：**
1. sb.json：vless inbound 的 `tls.server_name` + `reality.handshake.server` → 实测通的站（itunes.apple.com）
2. 全部分发订阅同步 sni：sub-links-plain.txt / sub-links-b64.txt（改完重编码 base64）/ sub-singbox.json / aws-sub.yaml（字段名是 `servername:`）/ sub-surfboard.ini
3. `sing-box check` → `systemctl restart sing-box`
4. 客户端重新拉订阅才生效（旧客户端会因 sni 不匹配秒拒）

**用户报"还是超时"时先查日志再说话**：`journalctl -u sing-box --since '20 min ago' | grep <用户IP>`。三种状态：①有到达+秒拒 invalid+订阅访问日志无拉取记录 = 客户端没重拉订阅（sni 不匹配）→ 直接上方案 B 别等用户；②有到达但无代理完成 = 服务端问题（查握手目标）；③UDP 类零到达 = 中国路径丢包（见文末）。

## 双机端到端测试法（绕开中国线路定性"服务端无罪"）

在服务端本机或另一台美国机起最小 sing-box 客户端：
```json
{"log":{"level":"warn"},
 "inbounds":[{"type":"mixed","tag":"in","listen":"127.0.0.1","listen_port":17897}],
 "outbounds":[{"type":"vless","tag":"out","server":"<域名或127.0.0.1>","server_port":54132,
   "uuid":"...","flow":"xtls-rprx-vision",
   "tls":{"enabled":true,"server_name":"<必须=服务端server_name>",
          "utls":{"enabled":true,"fingerprint":"chrome"},
          "reality":{"enabled":true,"public_key":"<从私钥推导>","short_id":"..."}}}],
 "route":{"final":"out"}}
```
- `curl -x socks5h://127.0.0.1:17897 https://www.google.com/generate_204` → 204 = 服务端无罪，问题在中国路径
- 客户端 sni 必须 == 服务端 server_name；握手目标改了之后旧 sni 会**秒拒 invalid**（这正好反向验证修复生效）
- 坑：连自家公网 IP = hairpin 回环，conntrack 显示 CLOSE_WAIT 挂死，用域名或 127.0.0.1
- 测完 `pgrep -f 'net-tune.*json' | xargs -r kill` 清理

## 排除调优嫌疑：回滚 A/B
用户会怀疑刚做过的内核调优。决定性排除法：`sysctl -w` 回滚旧值 → 复测 → 照样挂 → 调优无罪 → 恢复调优。10 分钟，比争论快。

## 服务端无罪后：查中国路径 UDP（hy2/tuic 类）
- 服务端日志 24h 内用户 IP 的 hy2/tuic 到达数 = 0，且跨机 UDP 探测能到本机网卡 → 中国→该线路 UDP 被丢（DDoS 防护线路常见），TCP 系节点不受影响
- 混合探测法：peer dm 让另一台机器发 UDP 垃圾包，本机 `tcpdump -i eth0 -n udp port X`（抓到 = 线路没丢）+ `grep /proc/net/nf_conntrack`（`[UNREPLIED]` 正常，QUIC 对垃圾包沉默）

## REALITY invalid 第三形态：客户端旧节点残留（2026-09-19/20 QQG）
前两形态的鉴别树之外补第三支：**sb.json 真值 ≡ 订阅下发参数逐字一致、5协议端到端全 204（服务端完全无罪），用户仍秒拒 invalid 130+ 次/0 成功** → 客户端在用旧参数敲门（Stash 里残留的旧订阅条目如已删的 /nx4hspzb、手加旧节点、非强制更新用缓存）。服务端任何折腾都是无用功，修复在客户端：删全部旧订阅只留现役 URL + 强制更新 + 飞行模式开关；用户 2 秒自检：Stash 节点详情 pbk/sid 对照服务端真值。排除轮换论看密钥 mtime（`ls -la /etc/s-box/*.key`）。完整复盘：`references/reality-client-stale-params.md`（含两个日志陷阱：用户出口 IP 数天一换别拿单一 IP grep 日志；`to` 完成行不带客户端 IP，按用户统计成功数恒为 0，要用 [reqid] 关联）。
