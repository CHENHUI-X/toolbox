# WeChat (weixin/iLink) Send Reliability — CLI vs Direct API

Session 2026-07-15/20-21 learnings. Symptom: dad says "让妈妈睡吧", agent runs
`hermes send --to weixin "..."`, and the command **times out (exit 124)** or fails
with "iLink sendmessage rate limited; cooldown active for 30.0s". User's fix
instruction: "不是给微信发消息，而是直接通过微信那个端口说话" — use the weixin
platform port directly, not the CLI.

## Sending methods, from worst to best

### 1. `hermes send -q --to weixin "..."` — UNRELIABLE
- `-q` mode **times out silently** (exit 124) on weixin in several sessions, even
  when the message eventually gets delivered. The short timeout (30s default) is
  not enough for iLink's confirmation round-trip.
- When it does fail visibly, it's "rate limited; cooldown active for 30.0s".

### 2. `hermes send --to weixin "..."` (NO -q, timeout=120) — RELIABLE
- The pattern that succeeded this session: run **without** `-q` and give the
  terminal a **120s timeout**. Output: `Sent to weixin home channel (chat_id:
  o9cq809Yzw5aOtcoHCmdVFtQLpfA@im.wechat)`.
- If it returns "rate limited; cooldown active for 30.0s" (exit 1), **wait 45-90s
  before retrying** — each failed retry RESETS the 30s cooldown timer. Hammering
  makes it worse (see circuit-breaker notes below).

### 3. Direct platform API (`send_weixin_direct`) — BEST DIAGNOSTICS
User explicitly asked for this ("直接通过微信那个端口说话"). It bypasses the
CLI/approval layer and returns structured errors, making the actual failure mode
visible instead of a silent timeout:

```bash
cd /usr/local/lib/hermes-agent && python3 -c "
import asyncio, os, sys
sys.path.insert(0, '/usr/local/lib/hermes-agent')
from dotenv import load_dotenv
load_dotenv('/root/.hermes/.env')
from gateway.platforms.weixin import send_weixin_direct

async def main():
    result = await send_weixin_direct(
        extra={'account_id': os.environ.get('WEIXIN_ACCOUNT_ID', '')},
        token=os.environ.get('WEIXIN_TOKEN', ''),
        chat_id='o9cq809Yzw5aOtcoHCmdVFtQLpfA@im.wechat',
        message='【爸爸传话】老婆不早了快睡吧😘'
    )
    print(result)  # {'success': True, ...} or {'error': '...'}

asyncio.run(main())
"
```
- Works even when the CLI times out (different code path — no delivery-confirm wait).
- Mom's chat_id: `o9cq809Yzw5aOtcoHCmdVFtQLpfA@im.wechat`.

## Error codes seen (iLink sendmessage)

| ret | Meaning | Action |
|-----|---------|--------|
| -2 / "rate limited; cooldown active for 30.0s" | iLink server cooldown | WAIT 45-90s. Do NOT retry fast — every attempt resets the 30s breaker (`_rate_limit_circuit_until` extends). Bundle multiple items into ONE send. |
| -3 "invalid arguments" | stale/expired context_token or malformed params | The session context token is stale. Code auto-retries without context_token only for -14; for -3 you may need to wait for a fresh inbound message from mom to refresh the token, then retry. |
| -14 / session expired | iLink session expired | Auto-handled in code (retries without context_token). |

## Circuit-breaker mechanics (why waiting matters)

`weixin.py` has a rate-limit circuit breaker: threshold=1 hit within 30s window
opens the breaker for 30s; each subsequent failure EXTENDS `_rate_limit_circuit_until`
by 30s. So a burst of 5 rapid retries = 150s+ of cooldown. **Retry at most once
after a 60-90s pause.** The breaker state lives on the live adapter in the gateway
process — a fresh python process can't see/reset it; only time heals it.

## Root cause of recurring limits: dual-gateway shared bot

GCP (QQ+WeChat) and WSL (Telegram+WeChat) gateways share the SAME iLink bot token.
Both poll inbound AND send outbound, so iLink's per-account rate limit trips
often. Logs showed daily hits (~01:00, ~19:36). Fixes: decouple tokens, disable
WeChat on WSL, or accept + batch sends. See `gcp-wsl-dual-gateway.md`.

## Rules of thumb

1. Default to `hermes send --to weixin` (no `-q`) with **timeout=120**.
2. On rate-limit error: tell the sender, wait 60-90s, retry ONCE.
3. If CLI times out again, switch to `send_weixin_direct` for real diagnostics.
4. Never fire a burst of separate weixin sends — batch into one message.
