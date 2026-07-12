---
name: gcp-operations
description: "Manage a GCP Compute Engine VM from within — network, firewall, monitoring, IP handling, and operational conventions for running Hermes on GCP."
version: 1.0.0
author: Agent
tags: [gcp, compute-engine, firewall, networking, ephemeral-ip, monitoring]
---

# GCP Operations

Operations knowledge for running Hermes Agent on a GCP Compute Engine VM. Covers networking, firewall, IP management, and operational style.

## User Preference: "You're on GCP — Just Execute"

When running on GCP as root, **try to execute commands directly** rather than explaining why you can't do something. Don't describe barriers — try a workaround first. Examples:

- Need to install a tool → install it (gcloud, nmap, etc.)
- Need to check something → check it via API, metadata, or install what's needed
- Service account permissions insufficient → try other approaches before explaining the limitation

The bottom line: this VM has internet access, root access, and Google metadata. There's almost always a way.

## GCP Networking Architecture

### Two Firewall Layers

Traffic from the internet must pass **both** layers:

```
Internet → [GCP Cloud Firewall] → [VM ufw/iptables] → Application (Sing-box, webhook, etc.)
```

- **GCP Cloud Firewall** = network-level rules managed via `gcloud compute firewall-rules` or GCP Console
- **VM Firewall (ufw)** = host-level rules on the instance itself

These are **independent** — allowing in one does NOT mean it passes the other. Ports open in ufw are invisible from the internet if GCP firewall blocks them.

### Checking Network Tags (GCP Firewall)

The instance has network tags that match GCP firewall rules:

```bash
curl -s -H "Metadata-Flavor: Google" \
  http://metadata.google.internal/computeMetadata/v1/instance/tags
# Typical: ["http-server","https-server"] → only TCP 80,443 allowed
```

### Adding GCP Firewall Rules

If a port is listening on the VM but unreachable from the internet:

```bash
gcloud compute firewall-rules create <rule-name> \
  --allow <protocol:port,...> \
  --source-ranges 0.0.0.0/0 \
  --target-tags <tag>
```

### Ephemeral IP Address

GCP instances use **ephemeral (temporary) public IPs by default**. These can change on:
- Instance restart / stop-start
- Prolonged disuse

**Always check current IP:**

```bash
# Via GCP metadata (fastest, reliable)
curl -s -H "Metadata-Flavor: Google" \
  http://metadata.google.internal/computeMetadata/v1/instance/network-interfaces/0/access-configs/0/external-ip

# Via external service (fallback)
curl -s https://api.ipify.org
```

### IP Change Detection

For setups where IP stability matters (proxy nodes, webhook endpoints), set up a cron-based IP monitor:

1. Store last known IP: `echo "$IP" > /path/to/.last_public_ip`
2. Every 30 min: fetch current IP, compare, notify on change
3. Use system crontab (`/etc/cron.d/`) — NOT Hermes internal cron

A ready-to-use script is at `scripts/gcp-ip-check.sh` in this skill directory — copy or symlink it to `/root/.hermes/scripts/` and add a crontab entry.

The script template pattern:

```bash
#!/bin/bash
CURRENT_IP=$(curl -s -H "Metadata-Flavor: Google" \
  "http://metadata.google.internal/computeMetadata/v1/instance/...")
LAST_IP=$(cat /path/to/.last_public_ip 2>/dev/null)
if [ "$CURRENT_IP" != "$LAST_IP" ]; then
    # Notify via Telegram
    echo "$CURRENT_IP" > /path/to/.last_public_ip
fi
```

### Static IP (Recommended)

To prevent IP changes permanently, promote to a static IP via GCP Console or:
```bash
gcloud compute addresses create <name> --region <region>
gcloud compute instances delete-access-config <instance> --access-config-name="external-nat"
gcloud compute instances add-access-config <instance> --access-config-name="external-nat" --address <STATIC_IP>
```

## Service Accounts

### Checking Scopes

```bash
curl -s -H "Metadata-Flavor: Google" \
  http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/scopes
```

### Getting an Access Token

```bash
curl -s -H "Metadata-Flavor: Google" \
  http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token
```

### Typical Default Scopes

Default compute service account (`...-compute@developer.gserviceaccount.com`) has:
- `devstorage.read_only` — read GCS buckets
- `logging.write` — write logs
- `monitoring.write` — write metrics
- No `compute` scope → cannot manage firewall rules, instances, etc.

If you need compute API access, the instance must be created with appropriate scopes, OR you must use gcloud from a machine that has proper credentials (WSL, local machine with gcloud auth).

## Useful GCP Metadata Endpoints

All require header `Metadata-Flavor: Google`:

| Info | URL |
|------|-----|
| External IP | `/instance/network-interfaces/0/access-configs/0/external-ip` |
| Internal IP | `/instance/network-interfaces/0/ip` |
| Instance name | `/instance/name` |
| Zone | `/instance/zone` (includes full URL) |
| Network | `/instance/network-interfaces/0/network` |
| Tags | `/instance/tags` |
| Service account scopes | `/instance/service-accounts/default/scopes` |
| Service account token | `/instance/service-accounts/default/token` |
| Service account email | `/instance/service-accounts/default/email` |
| Project ID | `/project/project-id` |

## External Port Testing

From inside GCP, connecting to the VM's own external IP does NOT work (hairpinning is not supported by default). To test if ports are actually open from the internet:

1. **Use an external port checker** (PortChecker, YouGetSignal, etc.)
2. **Install nmap** on the VM and run from a different source
3. **Use a free API** — write a script that tests via https://api.ipify.org or similar

## Memory & OOM Prevention

On small instances (~1GB RAM), Hermes gateway and sing-box can push memory close to limit. Standard hardening:

### Swap Setup

```bash
# Create 4GB swap (was 2GB, increased after OOM killed Hermes gateway)
swapoff /swapfile 2>/dev/null
dd if=/dev/zero of=/swapfile bs=1M count=4096
chmod 600 /swapfile
mkswap /swapfile
swapon /swapfile

# Persist across reboots
echo "/swapfile none swap sw 0 0" >> /etc/fstab
```

**Check swap is actually on:**
```bash
swapon --show
# NAME      TYPE SIZE  USED PRIO
# /swapfile file   4G   0B   -2
```

### Swappiness

Reduce swappiness so the kernel only swaps when truly necessary:

```bash
echo "vm.swappiness=30" > /etc/sysctl.d/99-oom-protect.conf
sysctl -p /etc/sysctl.d/99-oom-protect.conf
```

Value `30` = starts swapping at ~70% RAM usage (default `60` = starts at 40%). Lower = keeps processes in RAM longer, reduces swap churn. `10` is too aggressive for 1GB machines.

### Systemd Memory Limits for Hermes Gateway

Prevent Hermes from consuming all available RAM:

```ini
# /etc/systemd/system/hermes-gateway.service.d/99-memory.conf
[Service]
MemoryMax=400M
MemoryHigh=350M
OOMPolicy=continue
```

- `MemoryMax=400M` — hard cap, at 400MB the kernel OOM-kills the gateway
- `MemoryHigh=350M` — soft throttle, at 350MB the kernel starts slowing it
- `OOMPolicy=continue` — if OOM-killed, systemd restarts it (not `stop` or `kill`)

Apply:
```bash
systemctl daemon-reload
systemctl restart hermes-gateway   # must run OUTSIDE the gateway session
```

### OOM Score

To protect critical services from being killed first:
```bash
echo -1000 > /proc/1/oom_score_adj   # init never killed
echo -500  > /proc/$(pgrep -f "subscription-server")/oom_score_adj  # subscription server
# Hermes gateway stays at 0 (default) — acceptable to kill if absolutely necessary
```

## IP Change Detection & Auto-Update

GCP ephemeral IPs can change on instance stop/start. The following infrastructure auto-detects changes on reboot and updates everything downstream.

### User Preference: Boot-Only Detection

This user only wants IP detection on **server reboot** (systemd oneshot), not periodic cron. The 30-min cron was removed because GCP ephemeral IPs only change on stop/start, not during runtime.

### Architecture

```
Server Reboot
  → gcp-ip-check-boot.service (systemd oneshot, after network-online.target)
  → gcp-ip-check.sh
      ├── curl metadata.google.internal (timeout 10s, fallback ipify)
      ├── compare against .last_public_ip
      ├── if changed:
      │   ├── cf-update-dns.py "$CURRENT_IP"   ← must pass IP arg!
      │   ├── push-sub-to-github.py             ← rebuilds custom-sub.yaml + push
      │   └── systemctl restart subscription-server.service
      └── if unchanged: silent exit
```

### ⚠️ Common Pitfalls (fixed this session)

1. **`cf-update-dns.py` requires IP argument** — calling it without `"$CURRENT_IP"` makes it fail silently. Always use: `/root/.hermes/scripts/cf-update-dns.py "$CURRENT_IP"`

2. **`cf-update-dns.py` must be executable** — it was `-rw-------` (no +x), causing silent failure. Fix: `chmod +x /root/.hermes/scripts/cf-update-dns.py`

3. **`subscription-server` needs systemd service** — was a bare process killed by `pkill` with no auto-restart. Fix: created `/etc/systemd/system/subscription-server.service` with `Restart=always`.

4. **Curl timeout on boot** — no timeout set, could hang if network not ready. Fix: `--connect-timeout 5 --max-time 10` on all curl calls.

5. **Check script dependencies exist before calling** — added `[ -x ]` checks before calling cf-update-dns.py and push-sub-to-github.py, with fallback logging.

### Setup

**1. IP check script** (`/root/.hermes/scripts/gcp-ip-check.sh`):

Full working script at `scripts/gcp-ip-check.sh` in this skill directory. Covers:
- Fetches current IP from GCP metadata (falls back to ipify, with connection timeouts)
- Compares against stored IP
- On change: updates DDNS, pushes subscription to GitHub, restarts subscription server
- Logs to `/tmp/gcp-ip-check.log`
- Sends Telegram notification on IP change or first run

**2. Boot service (systemd oneshot) — no cron:**

```ini
# /etc/systemd/system/gcp-ip-check-boot.service
[Unit]
Description=GCP IP Check on Boot
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
ExecStart=/bin/bash /root/.hermes/scripts/gcp-ip-check.sh
RemainAfterExit=yes
User=root

[Install]
WantedBy=multi-user.target
```

Enable:
```bash
systemctl daemon-reload && systemctl enable gcp-ip-check-boot.service
```

### Files Managed on IP Change

| File | Purpose | Update Method |
|------|---------|--------------|
| `/root/.hermes/scripts/.last_public_ip` | Tracks known IP | `echo "$IP" >` |
| `/etc/s-box/clmi.yaml` | Clash config (VLESS node IP) | `sed -i "s/旧IP/新IP/g"` |
| `/etc/s-box/jhsub.txt` | V2Ray share links | `sed -i "s/@旧IP:/@新IP:/g"` |
| `/etc/s-box/jhdy.txt` | Share links backup | same as jhsub.txt |
| `/etc/s-box/custom-sub.yaml` | Stash override file | regenerated by push-sub-to-github.py |
| Cloudflare DNS A record | DDNS | cf-update-dns.py "新IP" |
| GitHub CHENHUI-X/sub/custom.yaml | Remote backup | push-sub-to-github.py |

### Verification

```bash
# Check current IP
curl -s -H "Metadata-Flavor: Google" http://metadata.google.internal/computeMetadata/v1/instance/network-interfaces/0/access-configs/0/external-ip

# Check DDNS resolution
nslookup google.cloud.eosphor.dpdns.org | grep Address

# Check local subscription is served
curl -s http://localhost:8888/custom.yaml | head -5

# Check last IP detection run
tail -5 /tmp/gcp-ip-check.log
```

## Related Skills

- `gcp-subscription-auto-ip-update` — narrow skill for subscription IP auto-update (candidate for consolidation into this skill)
- `sing-box-vps` — proxy server management
- `system-cron-setup` — system crontab for monitoring scripts
- `cross-platform-relay` — WeChat/QQ/Telegram relay (uses GCP as the relay host)
- `hermes-cross-instance-communication` — multi-Hermes setup with IAP tunnels
