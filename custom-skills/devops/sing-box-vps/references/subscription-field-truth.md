# sb.json → Stash/Clash 订阅逐字段真值映射（防硬编码）

> 来源：2026-09-06/07 双机（GCP + QQG）订阅连环事故复盘。核心教训：**生成订阅时每个字段都必须从服务端 sb.json 读真值，禁止硬编码**。两台服务器的同类协议配置可能本来就不同。

## VMess (ws)

| sb.json 字段 | 订阅字段 | 坑 |
|---|---|---|
| `transport.path` | `ws-opts.path` | 实际值是 `{uuid}-vm`，**带 -vm 后缀**，不是裸 `/{uuid}` |
| `transport.max_early_data` (2048) | `ws-opts.max-early-data` | 不带则握手失败 |
| `transport.early_data_header_name` (Sec-WebSocket-Protocol) | `ws-opts.early-data-header-name` | 与 ed 成对 |
| `tls.enabled` | `tls: true/false` | **两台机器不同**：GCP=true（真证书 /root/ygkkkca/cert.crt），QQG=false（纯 ws 无 TLS）。客户端tls与服务端不一致=000秒失败 |
| `tls.server_name` | `servername` | GCP=google.cloud.eosphor.dpdns.org |

## VLESS Reality

| sb.json 字段 | 订阅字段 | 坑 |
|---|---|---|
| `tls.server_name` | `servername` | **客户端 sni 必须与此完全一致** |
| `tls.reality.handshake.server` | —（服务端） | **必须与 server_name 同值**（sing-box 不支持分体；实测 2026-09-06） |
| `tls.reality.private_key` | `reality-opts.public-key` | 公钥由私钥 x25519 推导，换钥对必同步 |
| `tls.reality.short_id[0]` | `reality-opts.short-id` | |
| `users[].flow` | `flow` | xtls-rprx-vision |

### QQG 线路特殊坑

**QQG（FASTNET 洛杉矶）线路到 apple.com:443 的 TLS 握手会被丢** → Reality 的 server_name 和 handshake.server **都只能用 itunes.apple.com**（唯一实测稳定组合，204/0.24s）。GCP 机器无此限制（用 apple.com 正常）。改 sni 后必须端到端实测，不能想当然。

## 自签证书协议：HY2 / TUIC / AnyTLS

两台服务器的 hy2/tuic/anytls 证书均为**自签**（CN=www.bing.com，100年有效期）→ 订阅**必须带** `skip-cert-verify: true`，否则客户端证书校验必失败 = 「UDP 超时」假象（2026-09-07 实锤：conntrack 显示 UDP 双向 [ASSURED]，包通了但 TLS 校验挂）。

| sb.json 字段 | 订阅字段 | 坑 |
|---|---|---|
| `users[].password` | `password` | hy2/anytls 只有 password |
| hy2/tuic `tls.alpn: [h3]` | tuic 订阅 `alpn: [h3]` | hy2 订阅不需要 alpn |
| tuic `congestion_control: bbr` | — | |
| tuic users[].uuid + password | `uuid` + `password` | 双凭据都要 |

## TUIC 测试假阴性（勿误判）

- 本机 sing-box 1.13.12 的 tuic **outbound** 不认顶层 `alpn` 字段（FATAL unknown field）→ 本机起 client 测试时去掉 alpn
- GCP hairpin：本机连自己公网 IP 的 UDP 不可靠
- **真凭据 = 服务端 journalctl 出现用户真实 IP 的 `inbound/tuic: inbound connection ... [转发目标]` 成功记录**

## 端到端矩阵测试模板（改配置后必跑）

对每个节点：本机起临时 sing-box client（按订阅参数）→ socks 出口 curl `https://www.google.com/generate_204` → 期待 204。**全部节点全部协议跑完才算修复完成**，只测刚改的一项会把下一个坑留给用户。

实测基线（2026-09-07）：GCP/AWS × VLESS/VMESS/ANYTLS = 6/6 204；HY2 两台 204；TUIC 服务端日志证实转发正常。

## 统一同步器

`/root/.hermes/scripts/sync-all-subs.py`：真源=两台 sb.json → 生成规范 10 节点 Stash 订阅 → 同步三份订阅（本机 merged-sub / 本机 custom-sub 覆写段[PayPal规则保留] / QQG aws-sub）→ 重启两边订阅服务 → TCP 端口验证。节点参数变更后必跑；QQG 的 aws-sub.yaml 禁止手改（会被覆盖），改规则→改脚本。QQG SSH 密码在 `/root/.hermes/vault/qqg-ssh.txt`。

## 服务端被外部改动的检测

任何时候「上网不通」，第一步：`ls -la /etc/s-box/sb.json` 看 mtime + 对比订阅关键参数（sni/servername/uuid/password/公钥）。yg 脚本重跑/另一台 agent 改动都会改 sb.json 且不通知。
