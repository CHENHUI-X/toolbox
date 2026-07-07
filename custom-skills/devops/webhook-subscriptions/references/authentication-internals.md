# Webhook Authentication Internals

> Source: `gateway/platforms/webhook.py` in Hermes Agent.

## Signature Validation Flow

`_validate_signature(request, body_bytes, secret)` checks headers in this order:

### 1. Svix / AgentMail
```
svix-id: msg_<id>
svix-timestamp: <unix seconds>
svix-signature: v1,<base64-hmac> [v1,<base64-hmac> ...]
```
Signed content: `"{msg_id}.{timestamp}.{raw_body}"`.  
Svix secrets usually start with `whsec_`; the remainder is base64-decoded to get the HMAC key.

Trigger: any of `svix-id`, `svix-timestamp`, or `svix-signature` headers present.

### 2. GitHub
```
Header: X-Hub-Signature-256
Value:  sha256=<hex>
```
HMAC = `hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()`.

Trigger: `X-Hub-Signature-256` header present.

### 3. GitLab
```
Header: X-Gitlab-Token
Value:  <plaintext secret>
```
Simple string comparison via `hmac.compare_digest(token, secret)`.

Trigger: `X-Gitlab-Token` header present.

### 4. Generic
```
Header: X-Webhook-Signature
Value:  <hex HMAC-SHA256>
```
HMAC computed identically to GitHub format, but without the `sha256=` prefix.

Trigger: `X-Webhook-Signature` header present.

### 5. No recognized header → 401

If a secret is configured but none of the above headers are found, the request is rejected with `401 Invalid signature`.

## `hermes webhook test` Behaviour

The CLI test (`hermes_cli/webhook.py`) uses **GitHub format**:

```python
sig = "sha256=" + hmac.new(
    secret.encode(), payload.encode(), hashlib.sha256
).hexdigest()
headers = {
    "Content-Type": "application/json",
    "X-Hub-Signature-256": sig,
    "X-GitHub-Event": "test",         # ← event type for filtering
}
```

The event type `test` is hardcoded. If the route only accepts specific events (e.g. `task`), the response is `{"status": "ignored", "event": "test"}` even though authentication succeeded.

## Secret Resolution Order

```python
secret = route_config.get("secret", self._global_secret)
```

1. Route-specific `secret` from `~/.hermes/webhook_subscriptions.json` (per-subscription)
2. Global `secret` from `~/.hermes/config.yaml` → `platforms.webhook.extra.secret`
3. If neither has a secret → `403 Webhook route is missing an HMAC secret`
4. Set secret to `"INSECURE_NO_AUTH"` to skip validation entirely (testing only)

## No `/health` Endpoint

The webhook adapter only serves POST routes at `/webhooks/<name>`. There is no `/health` or `/` endpoint. To test if the server is alive, send any POST to a known route — you'll get either:
- `401` if auth is wrong (server is up, auth failed)
- `200 {"status": "ignored"}` if event type doesn't match (server is up, auth OK)
- `200 {"status": "ok"}` if everything matches

## Rate Limiting

Per-route fixed window: `rate_count[route_name]` entries within the last 60 seconds. Breach returns `429 Rate limit exceeded`.

## Idempotency

If a route's prompt is empty and the body contains an `idempotency_key` field, the adapter checks a cache to prevent duplicate agent runs on webhook retries.
