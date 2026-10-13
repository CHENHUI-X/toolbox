---
name: opencode-go-provider
version: 1.0.0
author: Hermes Agent
license: MIT
description: "Use when wiring OpenCode Go/Zen subscription into Hermes."
metadata:
  hermes:
    tags: [opencode, provider, subscription, model-switch, hermes]
---

# OpenCode Go / Zen as a Hermes provider

Use when the user hands over an OpenCode key (`oc_sk_...`) or asks to run Hermes on the
OpenCode Go/Zen subscription instead of (or alongside) packyapi / cf.api.fan style relays.

## When to Use

- The user hands over an OpenCode key (`oc_sk_...`) or asks to "log in" / hook up the OpenCode
  Go or Zen subscription so Hermes runs on it.
- A model move between relays is planned (packyapi / cf.api.fan / cf.api.fan style) and the new
  endpoint is an OpenCode family relay.
- You need to switch `cron` and `delegation` model routes along with the main default.

## Key facts:

- built-in provider ids `opencode-go` (base `https://opencode.ai/zen/go/v1`) and `opencode-zen`
  (base `https://opencode.ai/zen/v1`); creds come from `OPENCODE_GO_API_KEY` / `OPENCODE_ZEN_API_KEY`
- always strip whitespace from a chat-pasted key, then validate free with
  `GET /zen/go/v1/models` (expect 200) before touching config
- switch `model.*`, **and** `cron.model` + `delegation.model`; keep old `providers:` entries
- activation needs an out-of-tree reload: `write_file` a one-shot script, run it with
  `at -f ... now + N minutes`
- verify with a real `hermes -z` call plus `session_model_usage.billing_provider`

Full procedure, per-family API surfaces, quota semantics and pitfalls: `references/opencode-go-provider.md`.
