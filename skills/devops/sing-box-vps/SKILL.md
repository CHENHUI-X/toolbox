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

## References

- `references/yonggekkk-sing-box-yg.md` — Full repo reference, file structure, video tutorials
- `references/tuic-version-field.md` — Tuic version compatibility error transcript (sing-box 1.13.x)

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
