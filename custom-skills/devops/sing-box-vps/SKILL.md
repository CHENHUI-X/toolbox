---
name: sing-box-vps
description: Set up and manage sing-box proxy servers on VPS using popular community scripts (yonggekkk/sing-box-yg, etc.). Supports Vless-reality-vision, Vmess-ws/Argo, Hysteria-2, Tuic-v5, Anytls protocols.
tags: [sing-box, proxy, vps, vpn, yonggekkk, reality, hysteria, tuic, troubleshooting]
---

# Sing-box VPS Proxy Setup

Set up sing-box proxy protocols on a VPS using the popular **yonggekkk/sing-box-yg** ("甬哥精装桶") script. 8847⭐ on GitHub.

## Quick Install

```bash
bash <(curl -Ls https://raw.githubusercontent.com/yonggekkk/sing-box-yg/main/sb.sh)
```

After install, management shortcut: `sb`

## Supported Protocols

| Protocol | Transport | Notes |
|----------|-----------|-------|
| Vless-reality-vision | Reality | No cert needed, no domain needed |
| Vmess-ws(tls) | WebSocket + TLS | Works with Argo CDN |
| Hysteria-2 | QUIC-based | UDP-friendly, fast |
| Tuic-v5 | QUIC-based | Low latency |
| Anytls | TLS-based | Latest addition |

## Features

- **No domain required** — self-signed certs work out of the box
- **ACME certs** — can switch to real domain certs via acme-yg
- **Argo tunnels** — supports both fixed and temporary Argo tunnels (can coexist)
- **Psiphon VPN** — integrates 30-country Psiphon VPN as WARP alternative
- **Pure IPv4 / IPv6 / dual-stack** support
- **amd64 + arm64** architecture support
- **Alpine / Ubuntu / Debian / CentOS** support
- **Local subscription generation** — no third-party subscription converters

## Management Commands

After install, run `sb` to enter the management menu:
- Add/remove protocols
- Switch cert type (self-signed ↔ ACME)
- Configure Argo tunnels
- View subscription links
- Uninstall

## Subscription Output

The script generates locally:
- **Sing-box** client config (SFA/SFI/SFW)
- **Clash/Mihomo** compatible config
- **Share links** for copying to client apps at `/etc/s-box/vl_reality.txt`, `/etc/s-box/vm_ws_tls.txt`, `/etc/s-box/hy2.txt`, `/etc/s-box/tuic5.txt`, `/etc/s-box/an.txt`
- **Clash subscription** at `/etc/s-box/clmi.yaml`
- **Combined subscription text** at `/etc/s-box/jhsub.txt`

## Pushing Subscriptions to GitHub

After generating a local subscription file (e.g., `/etc/s-box/clmi.yaml` or a combined `custom.yaml`), you can host it on GitHub so client apps fetch it via raw URL.

### Typical Workflow

```bash
# 1. Clone the target repo
git clone https://USER:PAT@github.com/OWNER/REPO.git /tmp/sub-repo

# 2. Copy or generate the subscription file
cp /etc/s-box/clmi.yaml /tmp/sub-repo/custom.yaml
# Or: combine proxies from /etc/s-box/clmi.yaml into custom.yaml

# 3. Push
cd /tmp/sub-repo
git add -A
git commit -m "update: subscription config $(date +%Y-%m-%d)"
git push
```

### Token Requirements

| Token type | Permission | Works? |
|-----------|-----------|--------|
| **Fine-grained PAT** (`github_pat_...`) | Contents: Read & Write on target repo | ✅ Preferred |
| **Classic PAT** (`ghp_...`) | `repo` scope (full) | ✅ Fallback |
| **Classic PAT** (fine-grained scopes only) | Needs `repo` scope | ❌ 401 |

### Authentication Troubleshooting

If authentication fails, the symptom differs by what's wrong:

| Symptom | Likely cause |
|---------|-------------|
| `401 Bad credentials` with `Authorization: Bearer` | Token can't authenticate at all — wrong token, or token was created for a different account/repo |
| `401` with **every** method (Bearer, token header, basic auth) | Token doesn't belong to the repo's owner, or repo not in the token's allowed list |
| `404 Not Found` on **write** (PUT) but `200` on **read** (GET) | **Fine-grained PAT with read-only permissions** — GitHub returns 404 instead of 403 by design. Not a path issue, not a token validity issue. Fix: regenerate with `Contents: Read and write`. |
| Clone works (`git clone https://TOKEN@github.com/...`) but push fails | See special-char token section below |

#### Token with `[` `]` or other special URL characters

Some tokens contain `[` or `]` which are reserved in URLs. Git URL-encodes them to `%5B`/`%5D` and fails authentication.

**Fix: Use the GitHub API instead of git push:**

```bash
# Works for both read and write with tokens that pass basic auth
curl -s -u "TOKEN:x-oauth-basic" https://api.github.com/repos/OWNER/REPO/contents/custom.yaml | jq '.sha'

# Then PUT the updated content with the SHA
curl -s -X PUT -u "TOKEN:x-oauth-basic" \
  -H "Content-Type: application/json" \
  -d '{"message":"update","content":"BASE64_CONTENT","sha":"FILE_SHA"}' \
  https://api.github.com/repos/OWNER/REPO/contents/custom.yaml
```

#### Bearer vs Basic auth

Some tokens work with `-u TOKEN:x-oauth-basic` (basic auth) but **not** `Authorization: Bearer TOKEN`. Always try both when debugging:

```bash
# Try #1 — Bearer (may fail)
curl -H "Authorization: Bearer ghp_xxx" https://api.github.com/repos/OWNER/REPO

# Try #2 — basic auth (often works when Bearer doesn't)
curl -u "ghp_xxx:x-oauth-basic" https://api.github.com/repos/OWNER/REPO
```

#### Steps to diagnose

```bash
# 1. Can you reach GitHub at all?
curl -s -o /dev/null -w "%{http_code}" --connect-timeout 5 https://api.github.com

# 2. Can the token read the repo?
curl -s -u "TOKEN:x-oauth-basic" \
  https://api.github.com/repos/OWNER/REPO/contents/custom.yaml | jq '{sha: .sha, name: .name}'

# 3. Check token scopes (from response headers)
curl -sv -u "TOKEN:x-oauth-basic" -o /dev/null \
  https://api.github.com/repos/OWNER/REPO 2>&1 | grep -i x-oauth-scopes

# 4. Can the token write? (returns 200 vs 404)
curl -s -X PUT -u "TOKEN:x-oauth-basic" \
  -H "Content-Type: application/json" \
  -d '{"message":"test","content":"'$(echo test | base64)'","sha":"$(curl -s -u TOKEN:x-oauth-basic https://api.github.com/repos/OWNER/REPO/contents/custom.yaml | jq -r '.sha')"}' \
  https://api.github.com/repos/OWNER/REPO/contents/custom.yaml
# 200 = write works. 404 = read-only token.
```

#### Verdict quick reference

| `GET` result | `PUT` result | Verdict | Action |
|-------------|-------------|---------|--------|
| `200` (data) | `200` (ok) | Token has write access ✅ | Push freely |
| `200` (data) | `404` (not found) | Token is **read-only** — GitHub hides write-404 intentionally | Regenerate with `Contents: Read and write` |
| `401` or `404` | `401` or `404` | Token can't even read | Check owner, repo name, token list |
| Clone works | Push auth fails | URL-special chars in token | Use API, credential store, or SSH key |

If the user insists the token is valid but still fails: ask them to verify the **account the token belongs to** matches the repo owner, and that the repo is in the token's `Repository access` list. Alternative: **SSH deploy key** — generate a key pair and add the public key as a deploy key on the repo with write access.

See `references/github-subscription-push.md` for full error transcripts and step-by-step debugging from real sessions.

## Serv00/Hostuno Edition

For free Serv00 / paid Hostuno accounts:

```bash
bash <(curl -Ls https://raw.githubusercontent.com/yonggekkk/sing-box-yg/main/serv00.sh)
```

Supports vless-reality, vmess-ws(argo), hysteria2 on Serv00 with argo tunnel.

## Health Check & Auto-Restart

After setup, set up a daily health check that verifies sing-box is running and auto-restarts on failure.

### Manual diagnostic commands

```bash
# Check process
pgrep -f "sing-box run"
# Check listening ports
ss -tlnp | grep sing-box
# Check config
/etc/s-box/sing-box check -c /etc/s-box/sb.json
# Check service
systemctl is-active sing-box.service
# Service logs
journalctl -u sing-box.service --no-pager -n 20
```

### Auto-restart script

Store at `~/.hermes/scripts/sing-box-check.sh` and set up as a daily cron job. The script exits silently (no output) when everything is normal — the user only receives a message when something actually went wrong and was fixed.

```bash
#! /bin/bash
# Checks: process running, ports listening, config valid
# On failure: restarts sing-box service
# On success: reports uptime, ports, memory usage
SERVICE="sing-box.service"
PID=$(pgrep -f "sing-box run" | head -1)
PORTS=$(ss -tlnp | grep sing-box | awk '{print $4}' | awk -F: '{print $NF}')
CONFIG_OK=$(/etc/s-box/sing-box check -c /etc/s-box/sb.json && echo true || echo false)
```

Cron job setup — use system crontab (see the [system-cron-setup](../devops/system-cron-setup/) skill for setup patterns):

```bash
# /etc/cron.d/sing-box-health-check
0 8 * * * root /root/.hermes/scripts/sing-box-check.sh
```

See `scripts/sing-box-check.sh` for the full implementation.

## Troubleshooting

### Config validation

```bash
/etc/s-box/sing-box check -c /etc/s-box/sb.json
```

Returns `FATAL ...` with the specific line/field that's wrong, or exits silently on success.

### Service status & logs

```bash
systemctl status sing-box.service
journalctl -u sing-box.service --no-pager -n 20
```

If the service shows `activating (auto-restart)` with `(Result: exit-code)`, check the journal for the fatal error. A high restart counter (e.g. "restart counter is at 56") indicates a persistent config problem that systemd retries aggressively and burns CPU.

### Restart loop escalation

If sing-box keeps restarting, **stop the service first** to stop the loop before fixing:

```bash
systemctl stop sing-box.service
# fix config, then:
systemctl start sing-box.service
```

### Tuic version field removed (sing-box ≥1.13.x)

Sing-box 1.13+ removed the `"version"` field from tuic inbound configuration. If `sb.json` contains:

```json
{
    "type": "tuic",
    "version": 4,
    "tag": "tuic5-sb",
    ...
}
```

sing-box will fail with:
```
FATAL decode config: inbounds[3].version: json: unknown field "version"
```

**Fix:** Remove the `"version": 4,` line from the tuic inbound block. Sing-box auto-detects tuic version in newer releases.

```bash
sed -i '/"version": 4,/d' /etc/s-box/sb.json
/etc/s-box/sing-box check -c /etc/s-box/sb.json  # verify
systemctl restart sing-box.service
```

See `references/tuic-version-field.md` for detailed error transcript.

## Server Prep & Cleanup

When setting up sing-box on a VPS that also runs Hermes Agent, strip unnecessary services to keep memory under 1GB. Common cloud VPS bloat includes BT Panel, Docker, Snapd, and Google Cloud Ops Agent.

**Use the [linux-server-audit](../linux-server-audit/) skill** for the complete server audit, cleanup checklist, cache cleanup, service masking, dpkg recovery, and kernel optimization. The notes below cover only sing-box-specific concerns.

## Kernel Optimization for Low-Memory (≤1GB) VPS

After stripping unnecessary services, apply sysctl tweaks to reduce memory pressure. See the **Kernel Optimization** section in [linux-server-audit](../linux-server-audit/) for the exact sysctl settings and tuning rationale.

Example before/after metrics from a real deployment:
| Metric | Before | After |
|--------|--------|-------|
| Available memory | ~286MB | ~440MB |
| Disk usage (29GB) | 8.5G | 5.3G |
| Service restarts (sing-box) | 59× loop | stable |

## Telegram WARP 路由（GCP 网络优化）

**问题:** GCP 连 Telegram API 频繁断连（每天 15~30 次），导致 Telegram 显示"正在输入"。
**解决:** 让 Telegram 流量经 sing-box 走 Cloudflare WARP 出口，不走 GCP 原生网络。

### 前置条件

- sing-box 配置中已有 `endpoints` 配置了 `warp-out`（WireGuard / Cloudflare WARP）
- sing-box 已配置 `socks-in` 入站（端口 10808）

### 步骤

**1. 添加路由规则**

在 `route.rules` 中 `warp-out` 出站规则之后插入：

```json
{
  "domain": ["api.telegram.org"],
  "outbound": "warp-out"
},
{
  "ip_cidr": [
    "149.154.166.0/24",
    "149.154.160.0/20",
    "91.108.4.0/22",
    "91.108.56.0/22"
  ],
  "outbound": "warp-out"
}
```

**2. 设置 Telegram 代理**

```bash
echo 'TELEGRAM_PROXY=socks5://127.0.0.1:10808' >> /root/.hermes/.env
```

⚠️ 一定走 `127.0.0.1` 本地 sing-box，不要走外部 IP（否则回环回 GCP 自身，等于没走）。

**3. 重启服务**

```bash
systemctl restart sing-box
systemctl restart hermes-gateway
```

**4. 验证**

```bash
grep "Proxy detected" ~/.hermes/logs/gateway.log | tail -3
grep "polling restarted after network error" ~/.hermes/logs/gateway.log | wc -l
```

### 效果

改之前：每天断连 15~30 次 → 改之后：连续运行 29+ 小时无断连。

### 注意事项

- Cloudflare WARP 免费且流量不限量
- 流量路径：Gateway → SOCKS5(127.0.0.1:10808) → sing-box 路由 → warp-out → Telegram API
- 如果 sing-box 中没有 warp-out 端点，需要先配置 WARP WireGuard

## 订阅服务器安全加固

订阅服务器（`subscription-server.py`）默认在 8888 端口以裸路径 `/custom.yaml` 提供 Clash 配置。这意味着任何人知道 IP 就能拉走完整的节点配置。

### 加固方法：换端口 + 随机路径

**1. 修改脚本，替换端口和路径：**

```python
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 40447    # 改端口
ALLOWED_PATH = '/nx4hspzb'                                    # 随机路径

class SubHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == ALLOWED_PATH:                          # 只响应对的路径
            ...
        else:
            self.send_response(404)                            # 路径不对一律 404
```

随机路径建议用 `random.choices(string.ascii_lowercase + string.digits, k=8)` 生成，不要人工取名。

**2. 更新 UFW：关旧端口，开新端口：**

```bash
ufw allow 40447/tcp        # 新端口
ufw delete allow 8888/tcp  # 关旧端口
```

**3. 确保旧进程被清理：**
```bash
ss -tlnp | grep 8888                    # 应无输出
kill $(pgrep -f "subscription-server.py 8888")  # 如果旧进程还在
```

**4. 启动订阅服务：**

```bash
pkill -f subscription-server.py
sleep 1
python3 /root/.hermes/scripts/subscription-server.py 40447
```

**5. 验证：**

```bash
curl -s http://localhost:40447/<新路径>     # ✅ 返回订阅
curl -s http://localhost:8888/custom.yaml  # ❌ 404 或连接拒绝
```

### 效果

| 防护层 | 旧 | 新 |
|--------|-----|-----|
| 端口 | 8888（易被扫） | 随机高位端口 |
| 路径 | `/custom.yaml`（可猜） | 随机 8 位字符串 |
| 未授权访问 | 返回首页 | 404 |
| 旧链接 | — | 永久失效 |

### 订阅服务器应使用 systemd 管理

⚠️ 手动启动的订阅服务器是**裸进程**，重启后会消失。应做成 systemd 服务实现开机自启和崩溃恢复：

```ini
# /etc/systemd/system/subscription-server.service
[Unit]
Description=Proxy Subscription Server
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
ExecStart=/usr/bin/python3 /root/.hermes/scripts/subscription-server.py 40447
Restart=always
RestartSec=5
User=root
Group=root
WorkingDirectory=/root

[Install]
WantedBy=multi-user.target
```

```bash
systemctl daemon-reload
systemctl enable --now subscription-server.service
```

之后管理命令改为：
```bash
systemctl restart subscription-server.service   # 重启
systemctl status subscription-server.service    # 查看状态
journalctl -u subscription-server.service -n 20 # 查看最近日志
```

**Pitfalls:**
- 创建 systemd 服务前先 `pkill -f subscription-server.py` 杀掉手动启动的旧进程，否则报端口占用
- `ExecStart` 路径必须用绝对路径
- 更新端口/路径后，同时更新 `gcp-ip-check.sh` 等关联脚本中的订阅 URL

### Cloudflare 代理 + 443 端口（隐藏真实 IP）

如果用户有一个域名配置了 Cloudflare 代理（橙色云），可以把订阅服务绑到 **443 端口上**，用域名拉取订阅，CF 代理会自动隐藏后端服务器真实 IP。

```python
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 443
# 不需要 ALLOWED_PATH — 用户要求无密码、无路径
class SubHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        with open(FILE_PATH, 'rb') as f:
            data = f.read()
        self.send_response(200)
        self.send_header('Content-Type', 'text/yaml; charset=utf-8')
        ...
```

需要：
1. UFW 开放 443 端口（通常已开）
2. Cloudflare SSL/TLS 设为 **Flexible**（CF→服务器走 HTTP）
3. 因为 443 需要 root 权限，python 以 root 跑即可

#### Subscription link delivery

**用户偏好（Parker）：** 给订阅链接时**只发链接本身**，不要附带任何说明文字。直接给出 URL 即可。不要问"要不要试试"、"这个行了没"之类的废话。

```
http://域名:443
# 或
https://域名/nx4hspzb  # 如果保留了路径保护
```

## 凭据轮换（清理蹭流用户）

sing-box 配置对外开放了代理端口后，订阅链接外泄会导致其他人蹭流量、GCP 出站费用飙升。实测月出站 ~500GB，入站 ~1TB，GCP 出站按 $0.12/GB 计会产生 ~$60+/月的费用。

### Pitfalls

- **订阅服务器会挂起** — sb.json 轮换后，`subscription-server.py`（端口 8888）可能因旧连接卡住而停止响应。Clash 端刷新订阅会拿到旧配置或空响应。**必须重启订阅服务：** `pkill -f subscription-server.py && sleep 1 && python3 /root/.hermes/scripts/subscription-server.py 8888 &`
- **订阅 YAML 也要同步更新** — 只改 `sb.json` 不够，`/etc/s-box/custom-sub.yaml`（Clash/Stash 拉的文件）也要同步改所有协议的 `uuid/password/public-key/short-id/token`。否则客户端刷新后还是旧凭据连不上。
- **端口没换，有心人仍可拉订阅** — 只换密钥不换端口，知道 IP:端口的旧用户重新拉订阅就能拿到新配置。要彻底封杀需要：换端口 + 加路径密码（如 `/custom.yaml` → `/aB3xK9mW.yaml`）。
- **Hysteria2 和 AnyTLS 的密码字段在 sb.json 里用的是旧 UUID** — yonggekkk 脚本生成的 hy2 和 anytls 密码就是 UUID 格式。轮换时需要注意这两个端口用的密码必须跟 UUID 同步，或者统一用一个独立密码（推荐独立密码 + 与 UUID 保持不同）。

### 完整操作流程

```bash
# 1. 生成新凭据
python3 << 'PYEOF'
import json, uuid, subprocess
result = {"uuid": str(uuid.uuid4()), "password": uuid.uuid4().hex[:20]}
r = subprocess.run(["/etc/s-box/sing-box", "generate", "reality-keypair"],
    capture_output=True, text=True, timeout=10)
for line in r.stdout.strip().split("\n"):
    if "PrivateKey" in line: result["private_key"] = line.split(": ")[1]
    if "PublicKey" in line: result["public_key"] = line.split(": ")[1]
r2 = subprocess.run(["/etc/s-box/sing-box", "generate", "rand", "4", "--hex"],
    capture_output=True, text=True, timeout=10)
result["short_id"] = r2.stdout.strip()[:8]
print(json.dumps(result))
PYEOF

# 2. 用 Python 脚本修改 /etc/s-box/sb.json（替换所有旧 uuid/password/private_key/short_id）

# 3. 同步更新 /etc/s-box/custom-sub.yaml — 每个协议的字段都要改：
#    - VLESS: uuid, public-key, short-id
#    - VMess: uuid, path (含 uuid 前缀)
#    - Hysteria2: password
#    - TUIC: token + uuid
#    - AnyTLS: password

# 4. 重启 sing-box
systemctl restart sing-box

# 5. 重启订阅服务器（关键！否则客户端拉到旧配置或空响应）
pkill -f subscription-server.py
sleep 1
nohup python3 /root/.hermes/scripts/subscription-server.py 8888 &

# 6. 验证
curl -s http://localhost:8888/custom.yaml | head -3          # 确认订阅服务器活着
ss -tnp | grep -E "33741|2096|65083|53900|29624" | wc -l    # 确认旧连接已断
cat /proc/net/dev | grep ens4 | awk '{print "出站: " $10/1024/1024/1024 " GB"}'
```

### 需要轮换的凭据

| 协议 | 端口 | 需要改的字段 |
|------|------|-------------|
| VLESS+REALITY | 33741 | `uuid`, `private_key`, `short_id` |
| VMess+WS+TLS | 2096 | `uuid`, `transport.path` |
| Hysteria2 | 65083 | `password` |
| TUIC | 53900 | `uuid` + `password` |
| AnyTLS | 29624 | `password` |

### 操作流程

```bash
# 1. 生成新凭据
python3 << 'PYEOF'
import json, uuid, subprocess
result = {
    "uuid": str(uuid.uuid4()),
    "password": uuid.uuid4().hex[:20]
}
r = subprocess.run(["/etc/s-box/sing-box", "generate", "reality-keypair"],
    capture_output=True, text=True, timeout=10)
for line in r.stdout.strip().split("\n"):
    if "PrivateKey" in line: result["private_key"] = line.split(": ")[1]
    if "PublicKey" in line: result["public_key"] = line.split(": ")[1]
r2 = subprocess.run(["/etc/s-box/sing-box", "generate", "rand", "4", "--hex"],
    capture_output=True, text=True, timeout=10)
result["short_id"] = r2.stdout.strip()[:8]
print(json.dumps(result))
PYEOF

# 2. 写回 /etc/s-box/sb.json（用 JSON 替换所有旧值）
# 用 execute_code 或 Python 脚本修改后写回

# 3. 重启
systemctl restart sing-box
```

### 验证旧连接已清除

```bash
# 检查代理端口连接数
ss -tnp | grep -E "33741|2096|65083|53900|29624" | wc -l
# 应该为 0
```

### 监控流量变化

```bash
# 轮换前后对比出站流量
cat /proc/net/dev | grep ens4 | awk '{print "出站: " $10/1024/1024/1024 " GB"}'
```

## 每日流量自动报告

`scripts/traffic-report.py` 生成简洁的中文日报，输出到 stdout，适合 cron 定时推送。

### 部署（Hermes cron，免 LLM 费用）

```bash
cronjob action=create \
  schedule="0 23 * * *" \
  name="代理流量日报" \
  script="traffic-report.py" \
  no_agent=true \
  deliver=origin
```

- `no_agent=true`: 只跑脚本 + 送 stdout，无 LLM 调用成本
- `deliver=origin`: 自动发到当前聊天

### 日报内容

```
📊 代理流量日报 — 2026-07-23 23:49:08
━━━━━━━━━━━━━━━━━━━━
📡 本月累计流量：
   入站: 1107.31 GB
   出站: 513.67 GB
🔌 代理端口连接数: 2
🟢 网关运行时间: 1-07:26:25
📱 Telegram今日断连: 1 次
💾 内存: 469Mi / 955Mi
━━━━━━━━━━━━━━━━━━━━
```

## 参考

- `references/yonggekkk-sing-box-yg.md` — Full repo reference, file structure, video tutorials
- `references/tuic-version-field.md` — Tuic version compatibility error transcript (sing-box 1.13.x)
- `references/socks5-inbound-telegram.md` — Running sing-box as a SOCKS5 proxy for direct Telegram/app use, without external clients. **Includes WARP routing pattern for improving GCP→Telegram network stability.**

## GCP Ephemeral IP Change Handling

GCP VMs with ephemeral public IPs (the default) can change IP on stop/start. This breaks all proxy protocols that use the IP directly (vless-reality) and any DDNS or subscription config URLs.

### What Breaks When IP Changes

| Config file | What to update | Impact |
|-------------|---------------|--------|
| `/etc/s-box/clmi.yaml` | vless-reality `server:` field | Client can't connect via vless |
| GitHub subscription config (e.g., `custom.yaml`) | vless `server:` field + proxy-group name | Client subscription refresh picks up stale IP |
| DDNS domain record | A record | All domain-based nodes go down |
| vault/服务器配置.md | IP field | Agent loses accurate server info |

### Automated Pipeline (Recommended)

If the subscription is served to Clash/Stash clients via a local HTTP service, use the **[gcp-subscription-auto-ip-update](../devops/gcp-subscription-auto-ip-update/)** skill for fully automated IP change handling:

1. **gcp-ip-check.sh** runs every 30min (cron) and detects IP changes
2. Automatically updates `/etc/s-box/clmi.yaml`, `jhsub.txt`, and `jhdy.txt` with the new IP
3. Generates a Clash-override-format YAML and **pushes it to GitHub** (private repo OK) + **saves locally** at `/etc/s-box/custom-sub.yaml`
4. A systemd-managed HTTP server on port 8888 serves `custom-sub.yaml` for clients
5. Clients use `http://<your-domain>:8888/custom.yaml` — repos can be private

See the skill for full setup, script contents, and troubleshooting.

### Manual Fallback

If automation isn't set up yet:

**1. clmi.yaml (local Clash subscription):**
```bash
sed -i 's/server: OLD_IP/server: NEW_IP/' /etc/s-box/clmi.yaml
```

**2. GitHub subscription config** — See the **[Pushing Subscriptions to GitHub](#pushing-subscriptions-to-github)** and **[Authentication Troubleshooting](#authentication-troubleshooting)** sections.

**3. Vault info:**
```bash
sed -i 's/IP：OLD_IP/IP：NEW_IP/' /root/.hermes/vault/🖥️\ 服务器配置.md
```

### DDNS Update

For DDNS domains (e.g., `*.dpdns.org`), update the A record through the provider's management console. After updating DDNS, the domain-based nodes (vmess-ws, hysteria2, tuic5, anytls) will work again without touching clmi.yaml.

## Pitfalls

- **Must run as root** — the script checks EUID and exits if not root
- **Not for OpenVZ/LXC** — some virtualization types unsupported
- **Serv00 scripts risk account ban** — free accounts may be terminated
- **Firewall** — ensure ports are open (script handles most defaults)
- **Systemd requirement** — the service registers as a systemd unit
- **GCP cloud firewall ≠ VM firewall** — On GCP, even if `ufw` allows all ports and sing-box is listening, traffic won't reach the VM unless GCP cloud firewall rules also allow the ports. Add rules via `gcloud compute firewall-rules create ... --target-tags http-server`. See the `gcp-operations` skill for details.
- **Tuic version field removed in sing-box 1.13+** — see troubleshooting section above
- **Restart loop** — sing-box auto-restarting 50+ times will burn CPU; stop service before fixing config
- **Config backup exists** — `/etc/s-box/sb.json.bak` may contain a working config without the version field if tuic was the only problem
- **Service respawning** — `systemctl stop + disable` is not always enough for services like `google-cloud-ops-agent`. Use `systemctl mask <service> --now`. See [linux-server-audit](../linux-server-audit/) for the full pattern.
- **dpkg interruptions** — After bulk package removal, `dpkg --configure -a` may fail with `'ldconfig' not found in PATH'`. Fix: `export PATH=$PATH:/usr/sbin:/sbin` before running dpkg/apt commands. See [linux-server-audit](../linux-server-audit/) for the dpkg recovery workflow.
- **Low-memory (≤1GB) kernel tuning** — After stripping bloat, also apply sysctl tweaks. See the **Kernel Optimization** section in [linux-server-audit](../linux-server-audit/).
