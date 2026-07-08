# DeepSeek 400 Fix: anthropic_messages → chat

## Root Cause

DeepSeek API requires `reasoning_content` to be passed back on every assistant message after the model first outputs thinking tokens. When `api_mode: anthropic_messages` is set, Hermes wraps requests in Anthropic message format, but the DeepSeek thinking field is not correctly translated → reasoning_content gets lost → HTTP 400 on the next request.

## The Fix

Two levels of config need the fix — changing only the top-level `model.api_mode` is NOT enough:

| Level | Before | After |
|-------|--------|-------|
| `model.api_mode` (top-level) | `anthropic_messages` | `chat` |
| **Custom provider `gcp_dpsk.api_mode`** (🔥 the one that actually matters) | `anthropic_messages` | `chat` |

The `base_url` should already have `/v1` suffix (e.g., `https://www.packyapi.com/v1`) — this is the standard Chat API path.

**Live config example** (GCP Parker setup):
```yaml
custom_providers:
  - name: gcp_dpsk
    base_url: https://www.packyapi.com/v1
    api_key: sk-nxA...85UM
    api_mode: chat         # ← was anthropic_messages
    model: deepseek-v4-flash
    models:
      deepseek-v4-flash:
        context_length: 1000000
```

## Verification

```bash
grep -E "api_mode|base_url" ~/.hermes/config.yaml
```

Expected:
```yaml
api_mode: chat          # on both model. and custom provider
base_url: https://.../v1  # must end with /v1
reasoning_effort: high  # can stay high, no conflict
```

After changing config: `/reset` to start a new session. The 400 error should not reappear.

## Why This Works

- `api_mode: chat` → standard OpenAI-compatible /v1/chat/completions format
- DeepSeek's `reasoning_content` (thinking tokens) round-trips correctly in OpenAI format
- `reasoning_effort: high` can stay enabled
- No conflict between thinking mode and message format
