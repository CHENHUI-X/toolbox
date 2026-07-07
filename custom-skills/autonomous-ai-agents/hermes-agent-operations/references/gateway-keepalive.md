# Gateway Keepalive — Full Implementation Example

This reference documents the keepalive script created for Hermes gateway on this server.

## System Crontab Entry

File: `/etc/cron.d/hermes-gateway-check`
```
* * * * * root /root/.hermes/scripts/hermes-gateway-check.sh
```
Changed from `*/5` to `* * * * *` (every 1 minute) per user request. Cron can't do sub-minute intervals — 1 minute is the finest granularity. 30s is architecturally unnecessary because `Restart=always` in systemd handles unexpected crashes in ~5s; the keepalive is only needed for client-requested stops which `Restart=always` ignores.

## Keepalive Script

File: `/root/.hermes/scripts/hermes-gateway-check.sh`

```bash
#!/bin/bash
export PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
SERVICE="hermes-gateway.service"
RESTART_LOG="/tmp/hermes-gateway-restart.log"

# Read Telegram config from .env at runtime (survives gateway crash)
ENV_FILE="/root/.hermes/.env"
BOT_TOKEN=*** CHAT_ID=""
if [ -f "$ENV_FILE" ]; then
    BOT_TOKEN=*** -a "^TELEGRAM_BOT_TOKEN=*** "$ENV_FILE" | head -1 | cut -d= -f2-)
    CHAT_ID=$(grep -a "^TELEGRAM_HOME_CHANNEL=" "$ENV_FILE" | head -1 | cut -d= -f2-)
fi

tg_notify() {
    local msg="$1"
    if [ -n "$BOT_TOKEN" ] && [ -n "$CHAT_ID" ]; then
        curl -s -X POST "https://api.telegram.org/bot${BOT_TOKEN}/sendMessage" \
            -d "chat_id=${CHAT_ID}" -d "text=${msg}" -d "parse_mode=HTML" > /dev/null 2>&1
    fi
}

# Check service state
SERVICE_STATE=$(systemctl is-active "$SERVICE" 2>/dev/null)
if [ "$SERVICE_STATE" = "active" ]; then
    exit 0  # silent — nothing to report
fi

# Failed — reset and restart
systemctl reset-failed "$SERVICE" 2>/dev/null
systemctl restart "$SERVICE" 2>&1
sleep 4

NEW_STATE=$(systemctl is-active "$SERVICE" 2>/dev/null)
if [ "$NEW_STATE" = "active" ]; then
    NEW_PID=$(systemctl show -p MainPID "$SERVICE" 2>/dev/null | cut -d= -f2)
    MSG="✅ Hermes Gateway 已自动重启
时间: $(date '+%Y-%m-%d %H:%M:%S UTC')
状态: active | PID: ${NEW_PID:-unknown}"
    echo "$MSG"
    echo "$(date): 重启成功 → PID $NEW_PID" >> "$RESTART_LOG"
    tg_notify "$MSG"
else
    MSG="❌ Hermes Gateway 重启失败！
时间: $(date '+%Y-%m-%d %H:%M:%S UTC')
服务状态: ${NEW_STATE:-unknown}
$(journalctl -u "$SERVICE" --no-pager -n 15 2>/dev/null | tail -10)"
    echo "$MSG"
    tg_notify "$MSG"
    exit 1
fi
```

## Key Design Decisions

1. **No Hermes dependency** — runs from system crontab (`/etc/cron.d/`), not Hermes internal cron. Survives gateway crash. This is essential: Hermes cron runs inside the gateway process, so a keepalive inside Hermes cron is chicken-and-egg.
2. **`systemctl reset-failed` before restart** — needed because SIGKILL puts systemd unit in "failed" state. `systemctl restart` alone doesn't work on a failed unit.
3. **Direct Telegram API** — uses curl to call Bot API directly when gateway is dead. Token extracted from `.env` at runtime so there's no hardcoded credential.
4. **Silent on healthy** — exits 0 with no output when everything is normal. Alerts only when action is taken.

## Timeline of the Bug It Fixed

- Gateway was killed by SIGKILL at 12:26:00 (tool loop during shutdown)
- Hermes internal cron scheduler died with it — chicken-and-egg deadlock
- Systemd `Restart=always` does NOT trigger on `systemctl stop/kill` (only unexpected crashes)
- Gateway was dead for ~20 minutes until manual restart
- System crontab version (now every 1 min) catches it at next tick

## Also Migrated from Hermes Cron

| Task | File | System crontab |
|------|------|----------------|
| Sing-box health check | `/root/.hermes/scripts/sing-box-check.sh` | `/etc/cron.d/sing-box-check` `0 8 * * *` |
| Hermes auto-update | `/root/.hermes/scripts/hermes-update.sh` | `/etc/cron.d/hermes-update` `0 9 * * *` |

Both scripts also use direct Telegram Bot API notifications via the same pattern.

### Hermes Update Script — Final Design (v3)

The hermes-update script went through 3 iterations based on user feedback:

| Version | Approach | User reaction |
|---------|----------|---------------|
| v1 | Dump raw `git log --oneline` | ❌ "直接拿gate日志" |
| v2 | Categorize commits (feat/fix/chore/refactor…) in grouped summary | ❌ "格式有点乱" |
| v3 | Only send annotated tag release notes for new version tags | ✅ |

Key design decisions in v3:
- Uses `git tag` diff detection (`comm -13`) — not commit hash comparison
- Only notifies when a NEW annotated tag appears (i.e. a new version release)
- Extracts the tag's annotation message as the release note
- Strips SSH/PGP signature blocks from the output
- No notification for non-tagged commits (daily development noise)
- Code is still pulled automatically — just silenced if no new tag