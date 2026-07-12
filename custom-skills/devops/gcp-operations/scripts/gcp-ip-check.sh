#!/bin/bash
# GCP 公网 IP 开机检测脚本
# 仅服务器重启时执行（systemd oneshot），IP变了就更新DDNS+订阅+通知
# IP没变就静默
#
# 安装:
#   1. chmod +x /root/.hermes/scripts/gcp-ip-check.sh
#   2. 确保 cf-update-dns.py + push-sub-to-github.py 可执行
#   3. 创建 systemd service 并 enable
# 详见 skill: devops/gcp-operations

export PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
IP_STORE="/root/.hermes/scripts/.last_public_ip"
LOG_FILE="/tmp/gcp-ip-check.log"

log() {
    echo "$(date +'%Y-%m-%d %H:%M:%S'): $*" >> "$LOG_FILE"
}

# 读取 Telegram 配置
ENV_FILE="/root/.hermes/.env"
BOT_TOKEN=""
CHAT_ID=""
if [ -f "$ENV_FILE" ]; then
    BOT_TOKEN=$(grep -a "^TELEGRAM_BOT_TOKEN=" "$ENV_FILE" | head -1 | cut -d= -f2-)
    CHAT_ID=$(grep -a "^TELEGRAM_HOME_CHANNEL=" "$ENV_FILE" | head -1 | cut -d= -f2-)
fi

tg_notify() {
    local msg="$1"
    if [ -n "$BOT_TOKEN" ] && [ -n "$CHAT_ID" ]; then
        curl -s -X POST "https://api.telegram.org/bot${BOT_TOKEN}/sendMessage" \
            -d "chat_id=${CHAT_ID}" \
            -d "text=${msg}" \
            -d "parse_mode=HTML" \
            -d "disable_web_page_preview=true" > /dev/null 2>&1
    fi
}

# 获取当前公网 IP（加超时防止开机网络慢时卡死）
CURRENT_IP=$(curl -s --connect-timeout 5 --max-time 10 \
    -H "Metadata-Flavor: Google" \
    "http://metadata.google.internal/computeMetadata/v1/instance/network-interfaces/0/access-configs/0/external-ip" 2>/dev/null)

if [ -z "$CURRENT_IP" ]; then
    CURRENT_IP=$(curl -s --connect-timeout 5 --max-time 10 https://api.ipify.org 2>/dev/null)
fi

if [ -z "$CURRENT_IP" ]; then
    log "❌ 无法获取公网 IP（metadata 和 ipify 都失败）"
    tg_notify "⚠️ GCP 开机检测：无法获取公网 IP"
    exit 1
fi

log "当前IP: $CURRENT_IP"

if [ ! -f "$IP_STORE" ]; then
    echo "$CURRENT_IP" > "$IP_STORE"
    log "首次运行，记录 IP: $CURRENT_IP"
    tg_notify "🟢 GCP 公网 IP: <code>${CURRENT_IP}</code>"
    exit 0
fi

LAST_IP=$(cat "$IP_STORE")

if [ "$CURRENT_IP" = "$LAST_IP" ]; then
    log "✓ IP 未变: $CURRENT_IP，跳过更新"
    exit 0
fi

# ========== IP 变了，开始更新 ==========
log "⚠️ IP 变更: $LAST_IP → $CURRENT_IP"
echo "$CURRENT_IP" > "$IP_STORE"

# 1. 更新 DDNS（必须传IP参数，否则静默失败！）
if [ -x /root/.hermes/scripts/cf-update-dns.py ]; then
    DDNS_RESULT=$(/root/.hermes/scripts/cf-update-dns.py "$CURRENT_IP" 2>&1)
    log "DDNS: $DDNS_RESULT"
else
    DDNS_RESULT="❌ cf-update-dns.py 不存在或不可执行"
    log "$DDNS_RESULT"
fi

# 2. 更新订阅 + 推送到 GitHub
if [ -x /root/.hermes/scripts/push-sub-to-github.py ]; then
    SUB_RESULT=$(/root/.hermes/scripts/push-sub-to-github.py 2>&1)
    log "订阅: $(echo "$SUB_RESULT" | tr '\n' ' ')"
else
    SUB_RESULT="❌ push-sub-to-github.py 不存在或不可执行"
    log "$SUB_RESULT"
fi

# 3. 重启本地订阅服务
if systemctl is-active subscription-server.service >/dev/null 2>&1; then
    systemctl restart subscription-server.service
    log "订阅服务: 已重启"
else
    log "订阅服务: 未运行（跳过）"
fi

tg_notify "🔄 GCP 公网 IP 已变更
旧IP: <code>${LAST_IP}</code>
新IP: <code>${CURRENT_IP}</code>"

log "✅ 全部完成"
exit 0
