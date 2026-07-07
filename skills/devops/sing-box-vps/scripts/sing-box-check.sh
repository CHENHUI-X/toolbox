#!/bin/bash
# Sing-box 健康检查脚本 — 一切正常时静默，出问题才通知
# 用于 cronjob no_agent=True 定时任务
# 配置: 每天 8:00

export PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
SERVICE="sing-box.service"
CONFIG="/etc/s-box/sb.json"
BINARY="/etc/s-box/sing-box"

# 1. 检查进程
PID=$(pgrep -f "sing-box run" 2>/dev/null | head -1)
[ -z "$PID" ] && PROCESS_OK=false || PROCESS_OK=true

# 2. 检查端口
PORTS=$(ss -tlnp 2>/dev/null | grep sing-box | awk '{print $4}' | awk -F: '{print $NF}')
[ -z "$PORTS" ] && PORTS_OK=false || PORTS_OK=true

# 3. 检查配置
CONFIG_OK=true
if [ -f "$CONFIG" ]; then
    $BINARY check -c "$CONFIG" >/dev/null 2>&1 || CONFIG_OK=false
else
    CONFIG_OK=false
fi

# 全部正常 → 静默退出（用户收不到消息）
[ "$PROCESS_OK" = true ] && [ "$PORTS_OK" = true ] && [ "$CONFIG_OK" = true ] && exit 0

# 有问题 → 输出日志并尝试重启
echo "⚠️ $(date): Sing-box 异常"
[ "$PROCESS_OK" = false ] && echo "   - 进程未运行"
[ "$PORTS_OK" = false ] && echo "   - 端口未监听"
[ "$CONFIG_OK" = false ] && echo "   - 配置文件错误"

$BINARY check -c "$CONFIG" >/dev/null 2>&1 || {
    echo "❌ 配置文件无法通过验证，跳过重启"
    exit 1
}

echo ""
echo "🔄 正在重启 Sing-box..."
systemctl restart "$SERVICE" 2>&1
sleep 2

NEW_PID=$(pgrep -f "sing-box run" 2>/dev/null | head -1)
if [ -n "$NEW_PID" ]; then
    echo "✅ Sing-box 已成功重启 (PID: $NEW_PID)"
else
    echo "❌ Sing-box 重启失败，请手动检查"
    journalctl -u "$SERVICE" --no-pager -n 15 2>/dev/null
fi
exit 1
