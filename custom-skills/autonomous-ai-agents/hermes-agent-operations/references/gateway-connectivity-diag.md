# Gateway Connectivity Diagnostics

Step-by-step process for diagnosing why a messaging gateway (Telegram, WeChat) is failing to connect or has gone silent.

## Quick Diagnostic Flow

```
hermes status                       # 1. Check platform config
hermes gateway status               # 2. Check systemd service state
journalctl -u hermes-gateway -n 50  # 3. Check live logs
  --since "10 minutes ago"          #    narrower window
  --no-pager -o cat                 #    machine-readable
```

Then per platform below.

## Telegram: httpx.ReadError / Reconnect Loop

**Symptom:** Gateway logs show repeating:
```
[Telegram] Telegram network error, scheduling reconnect: httpx.ReadError:
[Telegram] Telegram network error (attempt 1/10), reconnecting in 5s. Error: httpx.ReadError:
```

**Key diagnostic:** The python-telegram-bot library uses **long-polling** (`getUpdates` via httpx with long timeouts). This can fail even when a simple `curl` to the same endpoint succeeds, because:
- Long-poll connections have different firewall/DPI treatment than short GETs
- GCP (and some clouds) may terminate idle TCP connections after ~30-60s
- DNS-over-HTTPS discovery (used as fallback) may find a slower IP
- The library's DNS resolution path differs from the system resolver

### Step-by-Step Diagnosis

**Step 1 — Basic network reachability:**
```bash
curl -s -o /dev/null -w "%{http_code} %{time_total}s\n" --connect-timeout 10 https://api.telegram.org
# Expected: 302 0.4-1.5s
```

**Step 2 — Direct Bot API test (bypasses the library entirely):**
```bash
# WARNING: Token will show in process list; use with care or via python3 -c
TOKEN="..."  # from ~/.hermes/.env
curl -s "https://api.telegram.org/bot${TOKEN}/getUpdates" | python3 -m json.tool | head -30
# Expected: {"ok": true, "result": [...]}
# Fails: {"ok": false, "error_code": 401, ...} means bad token
#        Connection refused/timed out means network blocked
```

**Step 3 — Check DNS resolution (the library may use its own resolver):**
```bash
# System resolution
host api.telegram.org
dig +short api.telegram.org

# Check if library's DNS-over-HTTPS fallback is relevant
journalctl -u hermes-gateway --no-pager | grep "Discovering Telegram API fallback IPs"
# If you see this, the library's primary DNS path failed first
```

**Step 4 — Check if it's a token issue specifically:**
```bash
# Extract token (Python to avoid terminal redaction)
python3 -c "
import os
with open('/root/.hermes/.env') as f:
    for line in f:
        if line.startswith('TELEGRAM_BOT_TOKEN='):
            token = line.strip().split('=', 1)[1]
            # Test token validity via Bot API
            import urllib.request, json
            req = urllib.request.Request(f'https://api.telegram.org/bot{token}/getMe')
            resp = urllib.request.urlopen(req, timeout=10)
            data = json.loads(resp.read())
            print(f'Bot username: {data[\"result\"][\"username\"]}')
            print('Token is valid' if data.get('ok') else 'Token rejected')
"
```

**Step 5 — Compare libcurl vs httpx behavior (the real divergence):**
```bash
# Simulate long-poll with curl
curl -s --max-time 60 \
  "https://api.telegram.org/bot${TOKEN}/getUpdates?timeout=30&offset=-1" \
  -o /dev/null -w "HTTP %{http_code}, time: %{time_total}s, conn: %{time_connect}s\n"
# If this works (200 after 30s wait), the network supports long-poll fine
# If it fails, GCP or your VPC is killing idle connections
```

### Known Causes

| Cause | Evidence | Fix |
|-------|----------|-----|
| GCP terminates idle TCP | Long-poll curl also fails after ~30s | Reduce poll timeout, or use webhook mode instead of polling |
| DNS resolution mismatch | Library uses DNS-over-HTTPS fallback but gets slower IPs | Add `api.telegram.org` to `/etc/hosts` with known-good IP |
| IP blocked / SNI filtering | Short curl works, long-poll curl fails | Use a proxy/relay for Telegram traffic |
| Token corrupted | `getMe` returns 401 | Recreate token via @BotFather and re-write `.env` |
| Transient network issue | Restarting the gateway fixes it | `sudo systemctl restart hermes-gateway`; if persistent, see above |

### Recovery

```bash
# Always use reset-failed + restart for clean recovery
sudo systemctl reset-failed hermes-gateway
sudo systemctl restart hermes-gateway
sleep 10
journalctl -u hermes-gateway --no-pager -n 10 | grep -i "telegram"
# Look for "Connected to Telegram" or "polling"
```

---

## WeChat/Weixin: Silent After Restart

**Symptom:** No WeChat-related log entries at all after a gateway restart. Last WeChat log is days old.

**Diagnosis:**

```bash
# Check if WeChat plugin loaded at all
journalctl -u hermes-gateway --no-pager | grep -i "weixin\|wechat" | tail -20
```

**Interpretation:**
- **No log entries at all** → The plugin may have started silently without logging a connection message. This is normal for iLink if the credentials are valid — the connection is established during plugin init and doesn't log a separate "connected" message.
- **Rate-limit entries** (`iLink sendmessage rate limited`) → The plugin is alive but hitting iLink's aggressive per-user rate limits. Messages flow again once cooldown (~30s) expires.
- **"Unauthorized user"** entries → The pairing code was never delivered (rate limited) or the user needs manual approval.

**Definitive test — send a message through WeChat:**
```bash
hermes send -q --to weixin "测试消息：网关是否正常运行？"
# -q (quiet mode) returns in ~3s instead of hanging for delivery confirmation
# If this succeeds, the gateway is alive
```

**If `hermes send` succeeds but logs show nothing:**
The WeChat plugin may simply not log "connected" on startup. Check for outbound messages in the logs:
```bash
journalctl -u hermes-gateway --no-pager | grep -i "weixin" | tail -5
```

**If `hermes send` fails or times out:**
- Check `.env` for valid `WEIXIN_*` variables
- Re-run `hermes gateway setup` to generate a new QR login if credentials expired
- iLink bot tokens may expire; a fresh QR login is the fix

---

## General Connectivity Checks

### Check all gateway logs at once
```bash
journalctl -u hermes-gateway --no-pager -o cat | grep -iv "registry\|tool_executor\|kanban" | tail -30
# Strips noisy tool-registry warnings, keeps platform + systemd messages
```

### Test network to each platform endpoint
```bash
# Telegram
curl -s -o /dev/null -w "Telegram: %{http_code} %{time_total}s\n" --connect-timeout 10 https://api.telegram.org
# WeChat iLink
curl -s -o /dev/null -w "Weixin: %{http_code} %{time_total}s\n" --connect-timeout 10 https://ilinkai.weixin.qq.com
```
