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
- **Share links** for copying to client apps: `vl_reality.txt`, `vm_ws_tls.txt`, `hy2.txt`, `tuic5.txt`, `an.txt`
- **Clash subscription**: `clmi.yaml`
- **Combined subscription text**: `jhsub.txt`

**⚠️ Script-generated memo/share-link files go STALE on credential rotation** — they are one-time snapshots, not live config. After any rotation they still carry the OLD uuid/pbk/sid/passwords (and sometimes old IPs); importing one = mysteriously "timing out" nodes. **Truth = derive from `/etc/s-box/sb.json`** (REALITY public key via X25519 from `private_key` — never copy from old files; multiple generations of stale keys can coexist in old files). On the 2026-09-06 sweep, `jhsub.txt` / `jhdy.txt` / `vl_reality.txt` / `an.txt` / `hy2.txt` / `tuic5.txt` / `sb10.json` / `sb11.json` were archived to `/root/net-tune/legacy-backup/` on both machines. Only the distribution files served by subscription-server (`custom-sub.yaml` / `merged-sub.yaml` / `sub-links-plain.txt` / `sub-links-b64.txt` / `sub-singbox.json` / `sub-surfboard.ini`) are maintained.

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

### Vless REALITY "invalid connection" — two very different causes

| Signal | Stale client keys (old pbk/sid) | Handshake target blocked (2026-09-06 case) |
|---|---|---|
| Error latency after client connects | instant reject | **~5m30s** (server stuck dialing the disguise site) |
| Server → disguise site :443 | fine | TCP OK but **TLS handshake hangs forever** (openssl & python ssl both time out) |
| Other TLS sites from the same box | fine | fine — only the disguise site is broken |

Fix for the blocked-target case — two variants (details + diagnostic chain + rollback-A/B exoneration + CN-path UDP probe: `references/reality-handshake-target-blocked.md`):
- **Symmetric** (needs client re-pull): point `tls.server_name` + `reality.handshake.server` at a site verified working from THAT box (itunes.apple.com worked when apple.com was dropped by a DDoS-protection transit), update sni in ALL distributed subscription files, restart sing-box.
- **Asymmetric (preferred — zero client action)**: REALITY validates the client's SNI against `tls.server_name` but fetches the disguise cert from `reality.handshake.server` — these can DIFFER. Keep `server_name` on the old value (stale clients with old sni keep validating) and point only `handshake.server` at the working site. Users who won't re-pull their subscription connect immediately. Do NOT touch the subscription sni — it must always mirror `tls.server_name` (syncing it to `handshake.server` broke every re-pulled client — 2026-09-06 second incident, user furious; see references/reality-asymmetric-sni-rule.md). Verified 204/33ms + 100MB/s through the old-sni path.
- **User says 'still timeout' → read server logs before asking them anything**: `journalctl -u sing-box | grep <user-IP>`. Arrivals + instant `invalid connection` + no proxy completions + empty subscription-server access log = client never re-pulled (their sni no longer matches) → switch to asymmetric fix server-side instead of waiting on the user.
- **2026-09-19/20 QQG case — invalid despite server ≡ subscription params = CLIENT-side stale node**: when `sb.json` truth verbatim-matches the distributed subscription (pbk/sid/sni/uuid all identical) and the user STILL gets instant `REALITY: processed invalid` on every attempt (130+ rejects, 0 completions) across multiple rotating home exit IPs, the client is running a stale node (old deleted subscription entry like /nx4hspzb, a manually-added old node, or cached params). Verify server health first with the 5-protocol end-to-end loopback test (`references/protocol-benchmark-same-host.md`) — if all 204, touch NOTHING server-side; the fix is client-side: delete ALL old Stash subscriptions, keep only the live URL, force update + airplane-mode toggle. User self-check: node detail page public-key/short-id vs server truth (2-second confirmation). Rule out rotation theories via key mtimes (`ls -la /etc/s-box/*.key`). Details: `references/reality-client-stale-params.md`
- **User broadband exit IP rotates every few days** (218.12.29.95→218.12.27.55→123.124.194.215→124.126.141.113→61.148.244.244 in ~5 days, all same home broadband) — never grep logs for ONE remembered user IP: got a false "user hasn't connected for hours" that way. Enumerate all sources: `journalctl -u sing-box --no-pager | grep 'connection from' | grep -oE 'from [0-9.]+' | sort | uniq -c | sort -rn`. Per-user success counting also has a trap: `grep <ip> | grep 'connection to'` reads 0 even while traffic flows, because proxy-completion (`to`) lines carry NO client IP — correlate via the `[reqid]` bracket token instead.

## Server Prep & Cleanup

When setting up sing-box on a VPS that also runs Hermes Agent, strip unnecessary services to keep memory under 1GB. Common cloud VPS bloat includes BT Panel, Docker, Snapd, and Google Cloud Ops Agent.

**Use the [linux-server-audit](../linux-server-audit/) skill** for the complete server audit, cleanup checklist, cache cleanup, service masking, dpkg recovery, and kernel optimization. The notes below cover only sing-box-specific concerns.

## Direct optimization workflow (when user rejects more experiments)

- Stop parameter sweeps and speculative A/B loops. Choose the final configuration from existing verified evidence and known-supported settings; a post-change syntax/service/subscription check is verification, not another tuning experiment.
- Be exact about evidence: identify which host/path was measured, and never claim all nodes or both servers are optimized from one client-path result.
- For dual-VPS work, inspect and back up each host independently; apply only to hosts whose management path is actually available, and verify each separately. A reverse-forward on port 9902 is the A2A HTTP API, not SSH; use the configured peer workflow for remote agent work. If remote administration is unavailable, distinguish that from proxy availability and report the unmodified scope plainly.
- If that access network has verified UDP QoS, make the default auto-selection prefer reliable TCP transports while keeping HY2/TUIC available in the manual group. Do not remove nodes or other user-visible entries without explicit deletion permission.
- Make the smallest text-targeted YAML edit; avoid PyYAML round-trips on distribution files with mirrored provider URLs. Back up first, parse-validate, then fetch the live subscription and confirm the expected groups/nodes/providers and HTTP status.
- Preserve a one-step rollback backup and report changed scope, what was verified, and any inaccessible host. Do not call the whole deployment "optimized" while a named host remains untouched or unverified.

## Kernel Optimization for Low-Memory (≤1GB) VPS

After stripping unnecessary services, apply sysctl tweaks to reduce memory pressure. See the **Kernel Optimization** section in [linux-server-audit](../linux-server-audit/) for the exact sysctl settings and tuning rationale.

Example before/after metrics from a real deployment:
| Metric | Before | After |
|--------|--------|-------|
| Available memory | ~286MB | ~440MB |
| Disk usage (29GB) | 8.5G | 5.3G |
| Service restarts (sing-box) | 59× loop | stable |

吞吐/延迟类 TCP 优化（bbr+fq、32MB 缓冲——区别于本节的省内存调优）见 `references/tcp-boost-four-pack.md`。**内核调优必须先获用户点头再动**（2026-09-06 全撤前科）。

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

### SOCKS5 封禁外部访问

SOCKS5 端口（10808）无密码认证，公网开放后易被扫描器滥用。封禁方案：
- iptables 规则：先放行 127.0.0.1，再 DROP 所有其他来源
- 不能用 UFW 代替（UFW 是 stateful 的，已建立连接不受影响）

详见 `references/socks5-block-external.md`。

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

#### Subscription link delivery / Parker 用户偏好

**Parker 的交付规则（适用于一切链接/推荐场景）：** 给订阅链接、商品链接、项目链接、优惠链接等**任何链接**时，**只发链接本身**，不要附带推荐理由、对比分析、询问"要不要试试"之类的废话。直接给出 URL 即可。如果用户问"有没有X"，直接回答"有/没有"并给链接，不要展开对比表或优势说明。用户要了解自然会追问。

**代写转发文案同理**：让写工单/邮件/话术让他转发时，用户说"只回复内容，其他啥也别加"就是字面意思——正文直接输出，不加主题行、不加"好的/以下是"前后语、不加说明（主题行只有单独要时才给）。

```
http://域名:443
# 或
https://域名/nx4hspzb  # 如果保留了路径保护
```

**给 Parker 的命令必须单行** — 多行/反斜杠续行会被他的终端自动执行（用户原话"一行给我 不要换行 不然自动执行了 以后记住"）。所有发给用户的 shell/PowerShell 命令写成一行。

**双机语境先确认主语** — 用户问"这个 IP 在哪/为啥超时"时先分清说的是 QQG 还是 GCP（报过错一次：用户问 QQG 的 IP，整篇答了 GCP 归属，被骂）。报 IP 归属时明确标注机器名。

**订阅 URL 以 subscription-server.py 的 PATH_MAP 为准，交付前必须 curl 实测 200** — 勿凭记忆报路径（9-19 报了不存在的 /vycqe8gr 实际 404；QQG 现役入口 `/merged9k2m` → merged-sub.yaml 十节点 GCP5+QQG5；custom-sub.yaml 已删、/nx4hspzb 路由 404）。

**"啥问题/怎么了"类问句先对齐所指** — 语境指刚发生的事故时直接答结论（一两句），不要开启新一轮排查（9-19 被打断纠正："我说之前啥问题"）。

**⚠️ Telegram 会打码 IP 字符串** — 发含 `0.0.0.0/0` 的命令，Telegram 自动替换成 `[IP]/0`，用户复制过去就是错的。规避：gcloud 命令省略 `--source-ranges`（默认就是 0.0.0.0/0），或让用户用 Cloud Shell/网页控制台。

**PowerShell 逗号是数组分隔符** — `--allow "udp:65083,udp:53900"` 必须加引号，否则 gcloud 报 `received [udp:65083 udp:53900]`。

### 用户喊停/回滚：最小交付节奏

用户中途打断（如转圈等太久）或连说"算了"时，通常不是要新方案，而是要**回到改动前的状态**：
- 立即停下当前方向，把已动的用户可见状态（订阅内容、下架节点）恢复原样，服务端内部配置的必要修复可保留但须逐条说明保留理由
- 先恢复，再简短汇报"恢复到 X 状态"，等用户新指令——不要乘势推销替代方案
- 订阅节点增删类变更须先问再做；服务端内部参数不属于用户可见面，可直接修

在第二台 VPS 上部署 sing-box 并与已有主机统一密钥体系 / 双向 agent 通信的完整流程（脚本非交互安装、密钥同步字段表、SSH 反向隧道绕开云防火墙、peer 互备、检查钩子移植、实测清单）：见 `references/multi-server-deployment.md`。

## 凭据轮换（清理蹭流用户）

sing-box 配置对外开放了代理端口后，订阅链接外泄会导致其他人蹭流量、GCP 出站费用飙升。实测月出站 ~500GB，入站 ~1TB，GCP 出站按 $0.12/GB 计会产生 ~$60+/月的费用。

### Pitfalls

- **订阅服务器会挂起** — sb.json 轮换后，`subscription-server.py`（端口 8888）可能因旧连接卡住而停止响应。Clash 端刷新订阅会拿到旧配置或空响应。**必须重启订阅服务：** `pkill -f subscription-server.py && sleep 1 && python3 /root/.hermes/scripts/subscription-server.py 8888 &`
- **轮换后蹭流客户端疯狂重试 → 30s 超时 ERROR 风暴 → journal 爆盘 → Telegram 网关断联** — 换凭据后旧客户端仍自动重连，每次 30 秒超时刷 ERROR，journal 可涨到 2.9GB，资源挤压导致 Telegram WARP 通道周期性断联（每 6-7 分钟）。**必须封禁来源 IP + journal 限容**，完整流程见 `references/leecher-retry-storm-blocking.md`
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

## 每日安全+流量自动报告

`scripts/traffic-report.py` 生成中文安全+流量报告（含日/周/月统计 + 端口扫描 + 异常检测），输出到 stdout，适合 cron `no_agent=true` 定时推送。

### 报告内容

```
🛡️ 每日安全+流量报告 — 2026-07-24 19:57
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📡 【流量统计】
  📅 本日 (0.02 GB ↓ / 0.01 GB ↑)
  📆 本周 (0.05 GB ↓ / 0.03 GB ↑)
  📊 本月 (0.05 GB ↓ / 0.03 GB ↑)
  💾 累计 (1107.93 GB ↓ / 513.94 GB ↑)

🔌 【端口状态】
  ✅ 无异常端口
  ✅ UFW规则干净

🔗 【连接安全】
  代理端口连接: 0 个
  ✅ SOCKS5外部: 无异常连接

🟢 【系统状态】
  网关运行: 2-03:35:07
  Telegram断连: 0 次/日
  内存: 421Mi / 955Mi
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### 功能模块

| 模块 | 检测内容 |
|------|---------|
| 📡 流量统计 | 本日/本周/本月/累计 入站+出站（GB），跨日自动跟踪 |
| 🔌 端口状态 | TCP/UDP 分列检测，白名单每轮从 sb.json 现读，报告异常监听 |
| 🔗 连接安全 | 代理端口连接数 + SOCKS5 外部连接检测 |
| 🟢 系统状态 | 网关运行时间、Telegram 断连次数、内存占用 |

### 状态持久化

脚本用 `~/.hermes/data/traffic-state.json` 保存网卡流量快照，跨日/跨周/跨月自动对齐：
- **日流量** = 上次运行到本次运行的增量
- **周流量** = 周一重置起点
- **月流量** = 每月1号重置起点

### 端口检测逻辑（现行实现）

端口检测不用硬编码白名单——代理端口会迁移，硬编码列表必然过时后把新真端口全报成"异常"。现行规则（`/root/.hermes/scripts/traffic-report.py` 为权威实现，skill 存档副本已落后于该逻辑）：

- **白名单每轮从 `/etc/s-box/sb.json` inbounds 现读**：hysteria2/tuic 归 UDP 入口，vless/vmess/anytls 归 TCP 入口（shadowsocks 双归）；SSH/订阅/Hermes 等基础端口保留小常量表
- **判定监听只看 `ss -H -lntup` 的本地地址列**：解析绑定地址判回环/通配（含 v4-mapped IPv6），对端列的 `0.0.0.0:*` 与暴露与否无关
- **UDP 用 `/proc/net/nf_conntrack` 统计真实流量**：只计 ASSURED 双向流，[UNREPLIED] 不算
- **代理进程持有的临时 UDP socket（`ip_local_port_range` 内）不是入站监听**，豁免告警
- 解析陷阱与 conntrack 细节见 `system-cron-setup` 技能 "Parsing network state in monitoring scripts" 一节

### 部署（Hermes cron，免 LLM 费用）

```bash
cronjob action=create \
  schedule="30 10 * * *" \
  name="代理安全+流量日报" \
  script="traffic-report.py" \
  no_agent=true \
  deliver=origin
```

- `no_agent=true`: 只跑脚本 + 送 stdout，无 LLM 调用成本
- `deliver=origin`: 自动发到当前聊天
- `schedule="30 10 * * *"`: 每天北京时间 10:30（系统已是 Asia/Shanghai）

### 文件位置

当前运行的脚本在 `/root/.hermes/scripts/traffic-report.py`（该文件比 skill 目录下的副本更新，是权威版本）。Skill 目录下的 `scripts/traffic-report.py` 是发布时存档，内容可能落后于运行版。

## 参考

- `references/subscription-node-offline-restore.md` — 订阅节点下架/恢复四格式同步、从现成链接克隆新节点、proxy-groups 引用陷阱、用户喊停时的恢复节奏
- `references/yonggekkk-sing-box-yg.md` — Full repo reference, file structure, video tutorials
- `references/tuic-version-field.md` — Tuic version compatibility error transcript (sing-box 1.13.x)
- `references/socks5-inbound-telegram.md` — Running sing-box as a SOCKS5 proxy for direct Telegram/app use, without external clients. **Includes WARP routing pattern for improving GCP→Telegram network stability.**
- `references/ip-geolocation-correction.md` — IP 广播导致 GEO 库国家记录错误的自助纠错流程（MaxMind 程序化提交、实测物理位置、工单文案要素）
- `references/reality-asymmetric-sni-rule.md` — 不对称 REALITY 配置的 sni 一致性铁律：订阅 sni ≡ tls.server_name，混搭 = 重拉用户全挂（二次事故复盘）
- `references/reality-handshake-target-blocked.md` — REALITY 握手挂起形态（~5m30s 超时 vs 即拒）：诊断链 + 对称/不对称修复 + 回滚 A/B 豁免
- `references/reality-client-stale-params.md` — REALITY invalid 第三形态：服务端≡订阅参数仍全拒 = 客户端旧节点残留（旧订阅条目/手加节点/缓存），5协议端到端豁免法+用户2秒自检法；含出口IP轮换枚举与 reqid 关联计数两个日志陷阱
- `references/china-line-quality-diagnosis.md` — 延迟低但速度慢：中国方向线路诊断（**多源测速铁律，单 CDN 限速会伪造"线路天花板"**、优化前后交替 A/B 对比法、出口 IP 中途变更陷阱、UDP 随用户网络自愈、协议速度排名口径）；9/15 补充：华为云镜像是最可靠基准源（腾讯 CDN 单源曾伪造"3MB 天花板"）
- `references/subscription-outage-diagnosis-915.md` — 全超时补遗：REALITY 握手挂起第三形态、多机对机验证纪律、单源测速反面教训、用户沟通纪律
- `references/protocol-benchmark-same-host.md` — 同机 5 协议对比实测方法论：hy2/anytls 出站字段是 password 不是 uuid、tuic 需 alpn h3、2082 的 vmess-ws 服务器端无 TLS、回环 reality 假失败、回环带宽测速无区分度；结论口径：日常 VLESS、丢包线路切 HY2/TUIC
- `references/tcp-boost-four-pack.md` — TCP 吞吐四件套（bbr+fq/32MB 缓冲/防慢启动重置/防 MTU 黑洞）两机落地与回退脚本、tcp_no_metrics_save A/B 无差异实录、LimitNOFILE 陷阱
- `references/qos-evasion-port-migration.md` — 国际链路 QoS 规避·全协议端口迁移实录（2026-09-21 QQG：vless→443、vmess→2053、hy2→8443/udp、tuic→8843/udp、anytls→8443/tcp；订阅服务 443→80 让位，QQG 订阅现役 80 口；tcp/udp 共端口规则、blanket sed 串端口陷阱、僵尸进程占口；含"套 CF/WARP 不提速"判定口径与迁移即强制重拉的代价）
- `references/hy2-brutal-and-speed-tuning.md` — 服务端提速榨干实录（2026-09-24）：hy2 brutal 模式（up_mbps/down_mbps 服务端 + 订阅 "100 Mbps" 带单位格式，回环 6 倍）、tcp_fastopen 1→3、CF/WARP 不提速判定、双机同步时 peer 自报 vs 独立实拉验证、各机订阅 key 相互独立
- `references/plain-node-subscription-conversion.md` — 纯节点订阅生成（用户拿去做订阅转换）：备份完整版→砍 groups/rules→mihomo wiki 字段对齐（"100 Mbps"/reduce-rtt/client-fingerprint）→「只有 vmess」= 老转换后端静默丢节点，换 clashmeta 目标并数节点数验收
- `references/acl4ssr-self-conversion.md` — 不依赖第三方转换站的自建转换：解析 ACL4SSR 官方 MultiMode.ini（转换网站后端真身）→生成订阅、组精简归边映射（按官方组默认值，非全归代理）、FINAL→MATCH（Stash 不认 FINAL）、空地区组补 DIRECT 兜底、禁 per-app 专项规则（用户否决）、UDP 协议 Stash 测速超时=家宽 UDP QoS 的诊断口径

## 检查钩子补充坑（详见 sing-box-node-check 技能 + multi-server-deployment.md 第七节）

- **scp 覆盖会冲掉远端已适配的检查脚本**——先在本地改好适配项再传，或传完重新 sed 并跑一遍确认
- **用户区分"订阅"与"复写规则"**：第二台机器交付精简纯订阅（proxies+groups+rules），server 字段全域名零裸 IP，订阅服务 80/443 双端口（用户复制链接常不带 :443，只开 443 会误报超时）
- **CF API Token 在 ~/.cloudflare_token.txt**（Edit zone DNS，作用域 eosphor.dpdns.org）：给新机器加子域名 A 记录用 API 搞定，不用麻烦用户

## 分流规则方案（2026-09-02 实战定稿）

**现役结构（2026-09-25 起，用户点名精简）**：QQG merged-sub.yaml = 4 组（🚀节点选择/♻️自动选择/🚀手动切换/🎯全球直连）+ 35 条规则 + 32 个 jsdelivr 规则源。规则本体 = 官方 `ACL4SSR_Online_Full_MultiMode.ini`（订阅转换网站后端真身）原序原库，各 ruleset 组按**官方组默认值**归边到「代理/直连」两侧（哔哩哔哩/网易音乐/微软/苹果/谷歌FCM/游戏平台/国内媒体→直连侧；电报/AI/油管/奈飞/巴哈姆特/GFWlist→代理侧），末条 `MATCH,🚀 节点选择`（Stash 不认 FINAL）。31 组完整版备份 `merged-sub.yaml.bak-full-rules`。**禁 per-app 专项规则**（用户否决微信专项：官方库+GEOIP,CN 已覆盖，新 App 自动兜住）。细节与坑见 `references/acl4ssr-self-conversion.md`

用户点名要 ACL4SSR 风格的规则（订阅转换站同款），方案演进与坑：

- **首选：rule-providers 引用 ACL4SSR 碎片**（订阅小、客户端自动更新、Stash 规则页可点开看明细）：
  - ⚠️ **碎片源必须用中国直连可达镜像**（2026-09-15 实锤）：`https://testingcf.jsdelivr.net/gh/ACL4SSR/ACL4SSR@master/Clash/{name}.list`。`raw.githubusercontent.com` 中国客户端直连拉不到 → 规则集全空 → 全部流量（含微信）落 MATCH 兜底走代理，且客户端每次更新都重试失败（用户观感"怎么每次都在拉规则"）。rule-provider 本有 `interval: 86400`+`path` 本地缓存（首次拉成功后 24h 内不碰网络），源不可达 = 永远没缓存。改完逐条 curl 验证 200。⚠️ 9-19 复发补课：镜像化必须 `grep -rn raw.githubusercontent /etc/s-box/` 枚举**所有**分发文件逐个替换——9-15 只改了 aws-sub.yaml，漏了 QQG merged-sub.yaml（用户 Stash 实际拉的文件）导致问题复发；且不限于 ACL4SSR，blackmatrix7 ChinaMax 等任何 raw 源都要换（`testingcf.jsdelivr.net/gh/<owner>/<repo>@master/<path>`）。当前状态：两台机全部分发文件已 jsdelivr 化、raw 残留 0
  - behavior 用 `classical`
  - **组默认值/顺序/结构与官方模板逐字一致，禁"顺手优化"**（2026-09-15 用户暴怒："你别乱改，人家漏网之鱼是啥你就是啥，你用人家的"）——曾把漏网之鱼默认改成 DIRECT 被打回。只改必须改的（碎片源镜像），其余照抄官方 `ACL4SSR_Online_Full.ini`（漏网之鱼默认=🚀节点选择、国内媒体/微软/苹果=DIRECT、广告/净化=REJECT），改完逐组核对默认项
  - 微信走代理的排查顺序：先查规则集拉没拉成（客户端规则页空=源不可达），再查规则本身——机制链 weixin.qq.com→ChinaDomain(DOMAIN-SUFFIX,qq.com)→🎯全球直连（组默认 DIRECT）
  - 标准顺序：LocalAreaNetwork→DIRECT、BanAD/BanProgramAD→REJECT、ChinaDomain/ChinaCompanyIp/ChinaIp/GoogleCN→DIRECT、国外碎片（ProxyGFWlist/ProxyLite/Telegram/Netflix）→节点组、MATCH 兜底→节点组
  - 分组加一个 `♻️ 自动选择`（url-test）挂在 select 组首位
- **内联大规则集（Loyalsoldier 15 万条）已废弃**：订阅 5MB+，且从 payload YAML 手转规则行极易出格式错误（`payload:,` 残留、引号拼接坏行），客户端直接解析失败
- **用户对规则明细的关注点**：他要在 Stash 分流页看到"具体哪个域名/IP 走哪"——RULE-SET 远程引用满足此需求（客户端下载后可见），不要因此误改回内联
- **RULE-SET 无裸 IP 例外**：节点 server 字段仍全用域名；订阅整体零裸 IP 是硬性要求
- 节点命名规范：`🇺🇸 洛杉矶 | VLESS`（国旗+真实城市+协议）。⚠️ 商家宣传的机房国家可能是 IP 广播假象——用 TCP 握手延迟实测物理位置（俄勒冈→目标 36ms=美西，≠波兰的 180ms+），以实测为准命名

## Stash 覆写（Override）— 跨订阅复用规则（2026-09-30）

用户说"给我一个规则，能让**其他订阅**也能使用（像之前那个台湾接点）"时 = 要 **Stash 覆写**：独立于订阅的 YAML 片段（含 `rules:`），套在任意订阅上都生效，覆写规则前置于订阅自带规则。**不要**为此去改 merged 订阅——覆写才是这个需求的正解形态。

- 覆写文件 = 普通 Clash YAML 片段，`rules:` 列表即可（REJECT/DIRECT/组名均可）；放订阅服务器新路径（PATH_MAP 加一行），**改完必须重启 subscription-server（旧进程持旧映射，不重启新路径 404）**
- 首个实例「微信加速」：屏蔽微信内置 httpDNS 治打开转圈（源 v2ex.com/t/1140060）→ `DOMAIN,dns.weixin.qq.com,REJECT` + `DOMAIN,dns.weixin.qq.com.cn,REJECT`；文件 `QQG /etc/s-box/sub-pages/wechat-dns-fix.stash`，路径 `/wechat-fix`
- 用户导入：Stash → 配置 → 覆写 → ➕ 贴 URL → **对每个订阅手动开启覆写开关**（覆写不自动套用）；后续加规则 = 更新同一覆写文件，用户刷新即全订阅生效，零订阅改动
- ⚠️ GCP 侧 subscription-server 是旧版：未知路径**兜底返回 merged 订阅（HTTP 200 假成功）**——验证新路径必须看内容不是状态码；GCP 修好前覆写 URL 只发 QQG 域名（aws.eosphor.dpdns.org 80 口实测 10ms）
- 与「禁 per-app 专项规则」的关系：禁的是往订阅里塞 App 专项分流；**独立覆写**是用户主动要的形态（跨订阅、他自己控制开关）——两者不冲突，覆写形态的通用规则按配方交付

部署命令与完整配方：`references/stash-override-recipe.md`

**PATH_MAP 新增路径的完整落地顺序（2026-09-30 实操）**：① `subscription-server.py` 的 `PATH_MAP` dict 加一行 `'/路径': '/etc/s-box/文件'`；② 重启 systemd 服务——⚠️ 若 80 口被旧裸进程占用（ps 查 `subscription-server.py`，systemd restart 会 bind 失败进 activating 循环，先 kill 裸进程再 restart，systemd 5 秒后自动接管）；③ 验证 = curl 看内容正确而非只看 200（GCP 旧版脚本未知路径兜底 200 返回 merged，假成功）。改 PATH_MAP 后不重启 = 新路径 404（旧进程持旧映射）。

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
- **订阅服务端口让位陷阱（2026-09-21）**：把 443 让给 VLESS、订阅服务挪 80 时，① 旧手动实例仍占 80 → Errno 98 → systemd activating 循环，先 `ss -tlnp | grep :80` 找僵尸 pid kill 再 restart；② QQG 现役订阅入口自此为 **80 口 `/merged9k2m`**，交付前仍须 curl 实测 200
- **rule-providers 批量改源/改端口必须 yaml 解析校验兜底**：sed 批量替换端口/URL 后必须 `yaml.safe_load` 逐节点打印 name+port 人工核对——本次 sed 把 VMESS/HY2 端口互串两处，全靠核对抓回（细节见 `references/qos-evasion-port-migration.md`）
- **PyYAML 重写分发 yaml 后必须 grep raw 残留=0**：PyYAML 重写 merged-sub.yaml 会把手工 jsdelivr 化的 rule-provider URL 回退成 raw（GCP 侧 9-24 事故，peer 自报「未回退」不可信，跨机独立实拉抓出）——每次 yaml.dump 落盘分发文件后立即 `grep -c raw.githubusercontent` 验证
