---
name: webhook-subscriptions
description: "Webhook subscriptions: event-driven agent runs."
version: 1.1.0
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [webhook, events, automation, integrations, notifications, push]
---

# Webhook Subscriptions

Create dynamic webhook subscriptions so external services (GitHub, GitLab, Stripe, CI/CD, IoT sensors, monitoring tools) can trigger Hermes agent runs by POSTing events to a URL.

## Setup (Required First)

The webhook platform must be enabled before subscriptions can be created. Check with:
```bash
hermes webhook list
```

If it says "Webhook platform is not enabled", set it up:

### Option 1: Setup wizard
```bash
hermes gateway setup
```
Follow the prompts to enable webhooks, set the port, and set a global HMAC secret.

### Option 2: Manual config
Add to `~/.hermes/config.yaml`:
```yaml
platforms:
  webhook:
    enabled: true
    extra:
      host: "0.0.0.0"
      port: 8644
      secret: "generate-a-strong-secret-here"
```

### Option 3: Environment variables
Add to `~/.hermes/.env`:
```bash
WEBHOOK_ENABLED=true
WEBHOOK_PORT=8644
WEBHOOK_SECRET=generate-a-strong-secret-here
```

After configuration, start (or restart) the gateway:
```bash
hermes gateway run
# Or if using systemd:
systemctl --user restart hermes-gateway
```

Verify it's running:
```bash
curl http://localhost:8644/health
```

## Commands

All management is via the `hermes webhook` CLI command:

### Create a subscription
```bash
hermes webhook subscribe <name> \
  --prompt "Prompt template with {payload.fields}" \
  --events "event1,event2" \
  --description "What this does" \
  --skills "skill1,skill2" \
  --deliver telegram \
  --deliver-chat-id "12345" \
  --secret "optional-custom-secret"
```

Returns the webhook URL and HMAC secret. The user configures their service to POST to that URL.

### List subscriptions
```bash
hermes webhook list
```

### Remove a subscription
```bash
hermes webhook remove <name>
```

### Test a subscription
```bash
hermes webhook test <name>
hermes webhook test <name> --payload '{"key": "value"}'
```

## Prompt Templates

Prompts support `{dot.notation}` for accessing nested payload fields:

- `{issue.title}` — GitHub issue title
- `{pull_request.user.login}` — PR author
- `{data.object.amount}` — Stripe payment amount
- `{sensor.temperature}` — IoT sensor reading

If no prompt is specified, the full JSON payload is dumped into the agent prompt.

## Common Patterns

### GitHub: new issues
```bash
hermes webhook subscribe github-issues \
  --events "issues" \
  --prompt "New GitHub issue #{issue.number}: {issue.title}\n\nAction: {action}\nAuthor: {issue.user.login}\nBody:\n{issue.body}\n\nPlease triage this issue." \
  --deliver telegram \
  --deliver-chat-id "-100123456789"
```

Then in GitHub repo Settings → Webhooks → Add webhook:
- Payload URL: the returned webhook_url
- Content type: application/json
- Secret: the returned secret
- Events: "Issues"

### GitHub: PR reviews
```bash
hermes webhook subscribe github-prs \
  --events "pull_request" \
  --prompt "PR #{pull_request.number} {action}: {pull_request.title}\nBy: {pull_request.user.login}\nBranch: {pull_request.head.ref}\n\n{pull_request.body}" \
  --skills "github-code-review" \
  --deliver github_comment
```

### Stripe: payment events
```bash
hermes webhook subscribe stripe-payments \
  --events "payment_intent.succeeded,payment_intent.payment_failed" \
  --prompt "Payment {data.object.status}: {data.object.amount} cents from {data.object.receipt_email}" \
  --deliver telegram \
  --deliver-chat-id "-100123456789"
```

### CI/CD: build notifications
```bash
hermes webhook subscribe ci-builds \
  --events "pipeline" \
  --prompt "Build {object_attributes.status} on {project.name} branch {object_attributes.ref}\nCommit: {commit.message}" \
  --deliver discord \
  --deliver-chat-id "1234567890"
```

### Generic monitoring alert
```bash
hermes webhook subscribe alerts \
  --prompt "Alert: {alert.name}\nSeverity: {alert.severity}\nMessage: {alert.message}\n\nPlease investigate and suggest remediation." \
  --deliver origin
```

### Direct delivery (no agent, zero LLM cost)

For use cases where you just want to push a notification through to a user's chat — no reasoning, no agent loop — add `--deliver-only`. The rendered `--prompt` template becomes the literal message body and is dispatched directly to the target adapter.

Use this for:
- External service push notifications (Supabase/Firebase webhooks → Telegram)
- Monitoring alerts that should forward verbatim
- Inter-agent pings where one agent is telling another agent's user something
- Any webhook where an LLM round trip would be wasted effort

```bash
hermes webhook subscribe antenna-matches \
  --deliver telegram \
  --deliver-chat-id "123456789" \
  --deliver-only \
  --prompt "🎉 New match: {match.user_name} matched with you!" \
  --description "Antenna match notifications"
```

The POST returns `200 OK` on successful delivery, `502` on target failure — so upstream services can retry intelligently. HMAC auth, rate limits, and idempotency still apply.

Requires `--deliver` to be a real target (telegram, discord, slack, github_comment, etc.) — `--deliver log` is rejected because log-only direct delivery is pointless.

## Signature Formats

The webhook adapter supports **three** signature header formats. Which one you use depends on the external service:

### 1. GitHub format (default for `hermes webhook test`)
```
Header: X-Hub-Signature-256
Value:  sha256=<HMAC-SHA256 hex of request body>
```
Used by GitHub webhooks. Also the format used by `hermes webhook test <name>`.

### 2. GitLab format (plain token match)
```
Header: X-Gitlab-Token
Value:  <plaintext secret>
```
Used by GitLab webhooks. Simple string comparison.

### 3. Generic format (for custom clients)
```
Header: X-Webhook-Signature
Value:  <HMAC-SHA256 hex of request body>
```
Use this for custom scripts, IoT devices, or any service that doesn't follow GitHub/GitLab conventions.

HMAC is always computed as:
```python
hmac.new(secret.encode(), body_bytes, hashlib.sha256).hexdigest()
```

### Shell example (generic HMAC)
```bash
BODY='{"event": "task", "data": {"message": "hello"}}'
SIG=$(echo -n "$BODY" | openssl dgst -sha256 -hmac "your-secret" | cut -d' ' -f2)

curl -X POST http://localhost:8644/webhooks/my-route \
  -H "Content-Type: application/json" \
  -H "X-Webhook-Signature: $SIG" \
  -d "$BODY"
```

### Global vs route-specific secret
If a route has its own `secret` in `webhook_subscriptions.json`, it takes **precedence** over the global `secret` from `config.yaml`. Route secrets are stored at `~/.hermes/webhook_subscriptions.json` with mode `0o600`.

## Security

- Each subscription gets an auto-generated HMAC-SHA256 secret (or provide your own with `--secret`)
- The webhook adapter validates signatures on every incoming POST
- Static routes from config.yaml cannot be overwritten by dynamic subscriptions
- Subscriptions persist to `~/.hermes/webhook_subscriptions.json`

## How It Works

1. `hermes webhook subscribe` writes to `~/.hermes/webhook_subscriptions.json`
2. The webhook adapter hot-reloads this file on each incoming request (mtime-gated, negligible overhead)
3. When a POST arrives matching a route, the adapter formats the prompt and triggers an agent run
4. The agent's response is delivered to the configured target (Telegram, Discord, GitHub comment, etc.)

## Troubleshooting

If webhooks aren't working:

1. **Is the gateway running?** Check with `systemctl --user status hermes-gateway` or `ps aux | grep gateway`
2. **Is the webhook server listening?** `curl http://localhost:8644/health` should return `{"status": "ok"}`. Check actual port with `ss -tlnp | grep <port>`.
3. **Check gateway logs:** `grep webhook ~/.hermes/logs/gateway.log | tail -20`
4. **Signature mismatch?** Verify the secret in your service matches the one from `hermes webhook list`. GitHub sends `X-Hub-Signature-256`, GitLab sends `X-Gitlab-Token`, custom clients use `X-Webhook-Signature`.
5. **Got `{"status": "ignored"}`?** The POST reached the server and authenticated, but the event type didn't match the route's `--events` filter. The test command sends `X-GitHub-Event: test` by default — if the route only accepts `task` events, it ignores the test. Use `hermes webhook test <name> --payload '{"event_type": "task", ...}'` to match the filter, or broaden the route's events.
6. **"Invalid signature" on localhost?** The HMAC is computed over the raw request body (bytes), not the pretty-printed JSON. Both sides must compute the signature over the exact same byte sequence (same whitespace, same key order). Python's `json.dumps` emits compact JSON by default; make sure your sender matches.
7. **External connectivity (dual firewall)?** The webhook binds to `0.0.0.0:<port>` by default, but may still be unreachable from outside due to **two** firewall layers:
   - **Local firewall** (ufw/iptables): Port must be allowed. Check `ufw status` or `iptables -L -n`.
   - **Cloud provider firewall** (GCP/AWS/Azure): Instance must have a firewall rule or network tag allowing the port.
   - **Workaround for local/dev**: Use ngrok / cloudflared to tunnel the port without opening firewalls: `cloudflared tunnel --url http://localhost:8644`
8. **Health check returns nothing?** The webhook adapter does NOT expose a `/health` endpoint — it only responds to `/webhooks/<name>` POST routes. Verify with `curl -X POST http://localhost:8644/webhooks/<name>` (will return auth error if misconfigured, which proves the server is alive).
