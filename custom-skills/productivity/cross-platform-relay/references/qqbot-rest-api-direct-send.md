# QQ Bot REST API Direct Send

Since `hermes send --to qqbot` silently times out (QQ Bot can reply within a session but cannot push standalone sends), use this Python pattern to send messages to QQ users directly via the Tencent QQ Bot REST API.

## Required Credentials

- `QQ_APP_ID` — from `.env`
- `QQ_CLIENT_SECRET` — from `.env`

## Python Direct Send Pattern

```python
import httpx, asyncio

async def send_qq_message(chat_id: str, message: str) -> bool:
    # Read credentials from .env
    with open('.hermes/.env') as f:
        env = {}
        for line in f:
            if '=' in line and not line.startswith('#'):
                k, v = line.strip().split('=', 1)
                env[k] = v
    
    appid = env['QQ_APP_ID']
    secret = env['QQ_CLIENT_SECRET']
    
    async with httpx.AsyncClient(timeout=15) as client:
        # Step 1: Get access token
        token_resp = await client.post(
            'https://bots.qq.com/app/getAppAccessToken',
            json={'appId': appid, 'clientSecret': secret},
        )
        if token_resp.status_code != 200:
            return False
        
        access_token = token_resp.json().get('access_token')
        headers = {
            'Authorization': f'QQBot {access_token}',
            'Content-Type': 'application/json',
        }
        payload = {'content': message[:4000], 'msg_type': 0}
        
        # Step 2: Try C2C (direct message) endpoint first
        url = f'https://api.sgroup.qq.com/v2/users/{chat_id}/messages'
        resp = await client.post(url, json=payload, headers=headers)
        if resp.status_code in {200, 201}:
            return True
        
        # Fallback: try group endpoint
        url2 = f'https://api.sgroup.qq.com/v2/groups/{chat_id}/messages'
        resp2 = await client.post(url2, json=payload, headers=headers)
        return resp2.status_code in {200, 201}

# Usage
# asyncio.run(send_qq_message('C8E2C7968148EB6B56F0FAEC285A96C8', '你好'))
```

## Finding the QQ Chat ID

The recipient's QQ open ID is stored in `~/.hermes/channel_directory.json`:

```json
{
  "qqbot": [
    {
      "id": "C8E2C7968148EB6B56F0FAEC285A96C8",
      "name": "C8E2C7968148EB6B56F0FAEC285A96C8",
      "type": "dm",
      "thread_id": null
    }
  ]
}
```

Use the `id` field as `chat_id` — it's the user's QQ Bot open ID (C2C DM channel).

## Why This Works When `hermes send` Doesn't

`hermes send --to qqbot` goes through the Hermes gateway → WebSocket → QQ Bot adapter, which requires an active session. The REST API direct call bypasses this by authenticating with `appId + clientSecret` to get an OAuth token, then posting directly to the `api.sgroup.qq.com` endpoint. This works even when there's no active WebSocket session with the target user.

## Rate Limiting

The QQ Bot REST API has its own rate limits. Keep messages under 4000 characters per call. If sending fails with a 429, back off and retry.
