#!/bin/bash
# GCP 公网 IP 变化检测 — 系统 crontab 版
# IP 没变时静默，变了则通过 Telegram 通知
# 
# Setup:
#   chmod +x gcp-ip-check.sh
#   bash gcp-ip-check.sh  # first run records current IP
#   echo '*/30 * * * * root /path/to/gcp-ip-check.sh' > /etc/cron.d/gcp-ip-check

export PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
IP_STORE="/root/.hermes/scripts/.last_public_ip"

# 读取 Telegram 配置
ENV_FILE="/root/.hermes/.env"
BOT_TOKEN=""
CHAT_ID=""
if [ -f "$ENV_FILE" ]; then
    BOT_TOKEN=$(grep -a "^TELEGRAM_BOT_TOKEN=" "$ENV_FILE" | head -1 | cut -d= -f2-)
    CHAT_ID=$(grep -a "^TELEGRAM_HOME_CHANNEL=" "$ENV_FILE" | head -1 | cut -d= -f2-)
fi

# Telegram 通知函数
tg_notify() {
    local msg="$1"
    if [ -n "$BOT_TOKEN" ] && [ -n "$CHAT_ID" ]; then
        curl -s -X POST "https://api.telegram.org/bot${BOT_TOKEN}/sendMessage" \
            -d "chat_id=${CHAT_ID}" \
            -d "text=${msg}" \
            -d "parse_mode=HTML" > /dev/null 2>&1
    fi
}

# 获取当前公网 IP（从 GCP metadata）
CURRENT_IP=$(curl -s -H "Metadata-Flavor: Google" \
    "http://metadata.google.internal/computeMetadata/v1/instance/network-interfaces/0/access-configs/0/external-ip" 2>/dev/null)

if [ -z "$CURRENT_IP" ]; then
    # metadata 拿不到，用 ipify 兜底
    CURRENT_IP=$(curl -s --connect-timeout 5 https://api.ipify.org 2>/dev/null)
fi

if [ -z "$CURRENT_IP" ]; then
    echo "$(date): ❌ 无法获取公网 IP" >> /tmp/gcp-ip-check.log
    exit 1
fi

# 读取上次记录的 IP
LAST_IP=""
if [ -f "$IP_STORE" ]; then
    LAST_IP=$(cat "$IP_STORE")
fi

# 如果没记录过，直接写入退出
if [ -z "$LAST_IP" ]; then
    echo "$CURRENT_IP" > "$IP_STORE"
    echo "$(date): ✅ 首次记录 IP: $CURRENT_IP" >> /tmp/gcp-ip-check.log
    exit 0
fi

# 比较 IP
if [ "$CURRENT_IP" != "$LAST_IP" ]; then
    MSG="⚠️ GCP 公网 IP 已变更！
旧 IP: $LAST_IP
新 IP: $CURRENT_IP
时间: $(date '+%Y-%m-%d %H:%M:%S UTC')

请更新你的 Clash 节点配置中的 IP 地址。"
    echo "$CURRENT_IP" > "$IP_STORE"
    echo "$(date): 🔄 IP 变更: $LAST_IP → $CURRENT_IP" >> /tmp/gcp-ip-check.log
    tg_notify "$MSG"
else
    # IP 没变，静默
    exit 0
fi
