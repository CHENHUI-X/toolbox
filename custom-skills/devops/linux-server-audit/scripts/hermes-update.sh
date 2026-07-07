#!/bin/bash
# Hermes 更新检测脚本 — 有更新才反馈，不碰 venv
# 用于 cronjob no_agent=True 定时任务
# 配置: 每天 9:00 + 10-18点每小时重试

export PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
HERMES_DIR="/usr/local/lib/hermes-agent"
STATE_FILE="/tmp/hermes-update-state"
GATEWAY_SERVICE="hermes-gateway.service"

TODAY=$(date +%Y-%m-%d)

# 今天已经成功 → 静默
if [ -f "$STATE_FILE" ]; then
    STATE_DATE=$(head -1 "$STATE_FILE")
    STATE_RESULT=$(tail -1 "$STATE_FILE")
    if [ "$STATE_DATE" = "$TODAY" ] && [ "$STATE_RESULT" = "success" ]; then
        exit 0
    fi
fi

cd "$HERMES_DIR" || {
    echo "❌ $(date): Hermes 更新失败，无法进入 $HERMES_DIR"
    echo "$TODAY" > "$STATE_FILE"; echo "failed" >> "$STATE_FILE"
    exit 1
}

OLD_HASH=$(git rev-parse HEAD 2>/dev/null)

git fetch origin main 2>&1
if [ $? -ne 0 ]; then
    echo "❌ $(date): Hermes 更新失败 — Git fetch 出错，请检查网络"
    echo "$TODAY" > "$STATE_FILE"; echo "failed" >> "$STATE_FILE"
    exit 1
fi

NEW_HASH=$(git rev-parse origin/main 2>/dev/null)

# 没更新 → 静默（标记成功即可）
if [ "$OLD_HASH" = "$NEW_HASH" ]; then
    echo "$TODAY" > "$STATE_FILE"; echo "success" >> "$STATE_FILE"
    exit 0
fi

# 有更新！拉代码
git pull origin main 2>&1
if [ $? -ne 0 ]; then
    echo "❌ $(date): Hermes 更新失败 — Git pull 出错"
    echo "$TODAY" > "$STATE_FILE"; echo "failed" >> "$STATE_FILE"
    exit 1
fi

NEW_HASH=$(git rev-parse HEAD)
NEW_TAG=$(git describe --tags --abbrev=0 2>/dev/null || echo "最新commit")

echo "🆕 Hermes 有新版本！"
echo ""
echo "📋 更新记录:"
git log "$OLD_HASH..$NEW_HASH" --oneline --no-decorate 2>/dev/null | head -20 | sed 's/^/  /'
TOTAL=$(git log "$OLD_HASH..$NEW_HASH" --oneline 2>/dev/null | wc -1)
if [ "$TOTAL" -gt 20 ]; then
    echo "  ... 共 $TOTAL 个提交"
fi
echo ""
echo "📌 代码已拉取，如需手动安装请运行:"
echo "   cd $HERMES_DIR && source venv/bin/activate && pip install -e . && systemctl restart $GATEWAY_SERVICE"

echo "$TODAY" > "$STATE_FILE"; echo "success" >> "$STATE_FILE"
exit 0
