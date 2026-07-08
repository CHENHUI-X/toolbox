# Weixin iLink Session Expiry & Circuit Breaker Troubleshooting

Session-specific diagnosis from 2026-07-08: `hermes send --to weixin` repeatedly failed with "rate limited" despite >9 hours since last activity.

## Symptom: Persistent "rate limited" with no recent activity

```
hermes send: Weixin send failed: iLink sendmessage rate limited; cooldown active for 30.0s
```

Retrying after 60s, 90s, 180s all return the same error — the circuit breaker resets but the server still rejects.

## Diagnosis Flow

### 1. Check if the adapter has a live long-poll session

```bash
grep -E "Connected.*account|inbound from=|response ready.*weixin" ~/.hermes/logs/gateway.log | tail -10
```

If the most recent entry is >1 hour old, the iLink server has expired the session server-side (errcode=-14). The circuit breaker shows "rate limited" but the root cause is session expiry.

### 2. Check the circuit breaker state

The in-memory circuit breaker lives on the `WeixinAdapter` instance keyed by token in `_LIVE_ADAPTERS`:

```python
from gateway.platforms.weixin import _LIVE_ADAPTERS
import os, time

token = os.getenv("WEIXIN_TOKEN", "")
adapter = _LIVE_ADAPTERS.get(token)
if adapter:
    remaining = max(0.0, adapter._rate_limit_circuit_until - time.monotonic())
    print(f"Cooldown: {remaining:.1f}s, Events: {len(adapter._rate_limit_events)}")
    # Reset
    adapter._reset_rate_limit_circuit()
    adapter._rate_limit_events.clear()
```

This clears the **local** gate but does NOT fix the server-side session. Use it to eliminate "is this a stale circuit breaker or a real server reject" ambiguity.

### 3. Direct API probe (bypass adapter entirely)

Use the same headers and endpoints as the adapter:

```python
import aiohttp, json, os

async def probe():
    token = os.getenv("WEIXIN_TOKEN", "")
    base_url = "https://ilinkai.weixin.qq.com"
    
    # Same API call the adapter uses
    payload = {"get_updates_buf": ""}
    body = json.dumps({**payload, "base_info": {"channel_version": "2.2.0"}})
    
    async with aiohttp.ClientSession() as session:
        resp = await session.post(
            f"{base_url}/ilink/bot/getupdates",
            data=body,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token}",
                "AuthorizationType": "ilink_bot_token",
                "iLink-App-Id": "bot",
                "iLink-App-ClientVersion": str((2 << 16) | (2 << 8) | 0),
            },
            timeout=aiohttp.ClientTimeout(total=15)
        )
        text = await resp.text()
        print(f"Status: {resp.status}, Body: {text[:500]}")

asyncio.run(probe())
```

Expected responses:
- `{"ret": 0, "msgs": [...], "get_updates_buf": "..."}` — session healthy
- `{"ret": -14, "errcode": -14, "errmsg": "session timeout"}` — session expired server-side
- Empty or 404 — wrong base URL or endpoint

### 4. Session expiry recovery

When errcode=-14 comes back from the iLink server, the gateway's long-poll loop normally handles this: it sleeps 600s (10 minutes) and then reconnects automatically. But if the adapter was never issued a `connect()` call (e.g. a fresh `WeixinAdapter` created by `send_weixin_direct` rather than the gateway's poll loop), there is NO reconnection logic — the adapter tries to send and immediately gets errcode=-14 with no recovery path.

**Only the gateway's running long-poll loop can re-establish the session.** Restarting the gateway is the reliable fix.

## Root Cause: Two Separate Failure Modes

| Error | Circuit Breaker? | Server Session | Fix |
|-------|:-:|:--------------:|-----|
| `errcode=-2` + "rate limited" | Yes — adapter auto-retries with backoff | Valid | Wait 30s, retry, or reset circuit breaker |
| `errcode=-14` + "session timeout" | No direct — mapped to last_error | Expired | Gateway restart required from outside process tree |

The "rate limited" message from `hermes send` is **misleading** when the actual server response is errcode=-14. The adapter's error handling in `_send_text_chunk_locked` maps session expiry to a `RuntimeError("iLink sendmessage error: ret=None errcode=-14 errmsg=session timeout")`, but the circuit breaker layer converts repeated failures into the "rate limited" message it shows.

## Why Gateway Restart Is Needed

The iLink long-poll session is established during `WeixinAdapter.connect()`, which:
1. Creates a new `_send_session` and `_poll_session`
2. Spawns the `_poll_task` (long-poll getupdates loop)
3. Registers itself in `_LIVE_ADAPTERS`

A cron-created `WeixinAdapter` (via `send_weixin_direct`) uses the `_LIVE_ADAPTERS` entry if available, or creates a fresh adapter with its own session — but the fresh adapter never runs the poll loop, so it has no way to receive the server-side "reconnect" flow.

Only the gateway's owned adapter (the one that called `connect()`) runs the poll loop. If that adapter's poll loop has disconnected (process restart, thread timeout), the server-side session remains expired for any other adapter instance trying to use the same token.

## Cron Job Design Consideration

WeChat cron jobs that run `hermes send --to weixin` should:
1. Accept that the first attempt may fail if the gateway's iLink session is stale
2. Check gateway activity timestamp from logs before retrying
3. Report the clear error status (exit code 1, "rate limited") rather than looping infinitely
4. Flag to the user when a gateway restart is needed (since the cron agent inside the gateway process cannot do it)

**Do NOT:**
- Loop-sleep-retry more than 1-2 times — the server will not recover without a new poll session
- Bypass the circuit breaker by creating a fresh adapter — it still hits the same server-side session expiry
- Try to restart the gateway from inside the cron job — the SIGTERM propagation block prevents it
