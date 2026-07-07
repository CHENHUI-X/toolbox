#!/bin/bash
# Generic health check template — silent when healthy, Telegram notification on failure
# Copy this and customize SERVICE_NAME, CHECK_COMMAND, and RESTART_COMMAND
# Usage: place in /root/.hermes/scripts/ and add crontab entry

export PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"

# === CONFIGURABLES ===
SERVICE_NAME="your-service.service"
CHECK_COMMAND="systemctl is-active $SERVICE_NAME"
RESTART_COMMAND="systemctl restart $SERVICE_NAME"
# =====================

# Read Telegram config from .env at runtime
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

# Check if service is healthy
SERVICE_STATE=$(eval "$CHECK_COMMAND" 2>/dev/null)
if [ "$SERVICE_STATE" = "active" ]; then
    exit 0  # silent — all good
fi

# Service is down — attempt restart
echo "$(date): $SERVICE_NAME state=$SERVICE_STATE, attempting restart..."

systemctl reset-failed "$SERVICE_NAME" 2>/dev/null
eval "$RESTART_COMMAND" 2>&1
sleep 3

NEW_STATE=$(systemctl is-active "$SERVICE_NAME" 2>/dev/null)
if [ "$NEW_STATE" = "active" ]; then
    NEW_PID=$(systemctl show -p MainPID "$SERVICE_NAME" 2>/dev/null | cut -d= -f2)
    MSG="✅ $SERVICE_NAME 已自动重启
时间: $(date '+%Y-%m-%d %H:%M:%S UTC')
PID: ${NEW_PID:-unknown}"
    echo "$MSG"
    tg_notify "$MSG"
else
    MSG="❌ $SERVICE_NAME 重启失败！
时间: $(date '+%Y-%m-%d %H:%M:%S UTC')
服务状态: ${NEW_STATE:-unknown}
$(journalctl -u "$SERVICE_NAME" --no-pager -n 15 2>/dev/null | tail -10)"
    echo "$MSG"
    tg_notify "$MSG"
    exit 1
fi
