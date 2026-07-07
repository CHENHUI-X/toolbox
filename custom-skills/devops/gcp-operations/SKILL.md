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

## Related Skills

- `hermes-cross-instance-communication` — multi-Hermes setup with IAP tunnels (uses GCP networking)
- `sing-box-vps` — proxy server management
- `system-cron-setup` — system crontab for monitoring scripts
