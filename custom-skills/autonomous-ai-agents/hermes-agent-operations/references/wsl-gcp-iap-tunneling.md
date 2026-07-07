# Parker's WSL ↔ GCP IAP Tunnel Setup (Reference)

## Instance Details
- **GCP Instance:** us-west1-b, Ubuntu 22.04, IP 35.212.240.179
- **WSL:** Windows Subsystem Linux (local machine)
- **IAP Zone:** us-east1-b (verify with `gcloud compute instances list`)

## Active Tunnels (WSL side)
Two persistent SSH tunnels via `gcloud compute ssh --tunnel-through-iap`:

### Forward Tunnel (WSL→GCP)
```bash
gcloud compute ssh <instance-name> --zone <zone> \
  --tunnel-through-iap -- -L 8645:localhost:8645 -N
```
Maps GCP's webhook port 8645 to WSL's localhost:8645.  
Used for: WSL Hermes POSTing tasks to GCP Hermes.

### Reverse Tunnel (GCP←WSL)
```bash
gcloud compute ssh <instance-name> --zone <zone> \
  --tunnel-through-iap -- -R 8644:localhost:8644 -N
```
Maps WSL's webhook port 8644 to GCP's localhost:8644.  
Used for: GCP Hermes POSTing tasks to WSL Hermes.

## Webhook Routes

### gcp-to-wsl (GCP→WSL on reverse tunnel)
- **URL:** `http://localhost:8644/webhooks/gcp-to-wsl`
- **Events:** task
- **Deliver:** weixin (WSL processes task → pushes result to WeChat)
- **Secret:** Stored in `~/.hermes/webhook_subscriptions.json` on WSL
- **Prompt:** `"{message}"` (flat JSON, no `payload.` prefix)
- **Note:** Secret changes every time the subscription is recreated (deleted + re-added)

### wsl-to-gcp (WSL→GCP on forward tunnel)
- **URL:** `http://localhost:8645/webhooks/wsl-to-gcp`
- **Events:** task
- **Deliver:** origin (response goes back to WSL)
- **Secret:** Stored in `~/.hermes/webhook_subscriptions.json` on GCP
- **Prompt:** `"任务从 WSL Hermes 发来：{payload.message}"`

## Platform Mapping
| Instance | Chat Platform | Home Channel |
|----------|--------------|--------------|
| GCP Hermes | Telegram | @CyberBullsBot |
| WSL Hermes | WeChat (微信) | Parker's WeChat |

## Cron Jobs (WSL Side)
- **wsl-gcp-tunnel-health** — monitors tunnel health; fails with 401 if Packy API token is invalid

## Key Commands (GCP Side)
Send a task to WSL:
```python
import json, hmac, hashlib, urllib.request
payload = {"event_type": "task", "message": "instruction"}
body = json.dumps(payload).encode()
sig = hmac.new(b"<current-secret>", body, hashlib.sha256).hexdigest()
req = urllib.request.Request("http://localhost:8644/webhooks/gcp-to-wsl",
    data=body, headers={"Content-Type": "application/json", "X-Webhook-Signature": sig})
resp = urllib.request.urlopen(req, timeout=15)
print(resp.status, resp.read().decode())  # → 202 {"status": "accepted", ...}
```

## Common Pitfalls
1. **Tunnel drops** — IAP tunnels can disconnect; need auto-reconnect or monitoring
2. **Secret mismatch** — subscription recreate = new secret; both sides must coordinate
3. **Template rendering** — use `{message}` for flat POST body, not `{payload.message}`
4. **Event filtering** — POST must include matching `event_type` or route filters it
