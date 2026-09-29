# GCP × WSL Dual-Gateway Infrastructure

## Architecture

Two independent Hermes gateways run in parallel:

| Instance | Host | Platforms | Role |
|----------|------|-----------|------|
| **GCP Hermes** | Google Cloud VM | QQ Bot, WeChat (iLink), Webhook | Casual/family — mom & dad chat |
| **WSL Hermes** | WSL (local PC) | Telegram, WeChat (iLink), Webhook | Work — dad's professional channel |

## The Shared-Bot Problem

Both GCP and WSL use the **same WeChat iLink bot token**. This means:

1. Mom sends a message on WeChat
2. WeChat server delivers it to both GCP and WSL simultaneously (same bot token = same inbox)
3. **GCP** processes it → responds on WeChat (correct)
4. **WSL** also processes it → may forward to Telegram (wrong — family content in work channel)
5. Dad reacts angrily on QQ: "为啥又转发到telegram 了？！"

## Webhook Bridge

The two instances are connected via a webhook bridge:

- **Route name:** `wsl-to-gcp`
- **Direction:** WSL → GCP (WSL sends tasks to GCP)
- **Secret:** Configured in `~/.hermes/webhook_subscriptions.json`
- **Deliver mode:** `local` (does NOT auto-forward to other platforms)

The webhook bridge is **not the cause** of the Telegram leak — it only goes WSL→GCP, not GCP→WSL. The actual cause is the **shared WeChat bot token**.

## Verification

### Check if both gateways receive the same message

On GCP:
```bash
grep "inbound message: platform=weixin" ~/.hermes/logs/gateway.log | tail -3
```

On WSL (check local gateway logs):
```bash
# Access WSL logs or ask the user to check
```

If the same message timestamp/content appears in both logs, the token is shared.

### Confirm Telegram-forward source

When dad says "为啥又转发到telegram了", check:

1. **GCP logs** for any `hermes send --to telegram` calls — there shouldn't be any
2. **WSL logs** — the WSL gateway likely processed the same WeChat message and relayed it to Telegram

## Fix Options

### Option A: Decouple credentials (cleanest)
Provision a separate iLink bot token for each instance. GCP's bot handles family chat; WSL's bot handles work chat. No cross-contamination.

### Option B: Disable WeChat on WSL
If WSL is work-only (Telegram), there's no need for it to have WeChat access at all. Remove the weixin platform from WSL's `config.yaml`.

### Option C: Accept with mitigations
- On GCP, ensure mom's messages are NEVER forwarded to Telegram
- Accept that WSL may still process them and forward to Telegram
- Warn the user about this limitation

## Timeline

This was discovered and debugged on 2026-07-08 when the user (dad on QQ) repeatedly complained about mom's messages appearing on Telegram. The GCP gateway logs showed zero Telegram sends, confirming the leak was on the WSL side.
