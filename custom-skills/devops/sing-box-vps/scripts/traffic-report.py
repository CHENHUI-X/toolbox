#!/usr/bin/env python3
"""每日代理流量报告 — 输出到 stdout，适合 cron no_agent=true"""
import subprocess
from datetime import datetime

# 1. 网卡流量
with open("/proc/net/dev") as f:
    for line in f:
        if "ens4" in line:
            parts = line.strip().split()
            rx = int(parts[1])
            tx = int(parts[9])
            break

rx_gb = rx / 1024 / 1024 / 1024
tx_gb = tx / 1024 / 1024 / 1024

# 2. 代理端口连接数
result = subprocess.run(["ss", "-tn"], capture_output=True, text=True, timeout=5)
ports = ["33741", "2096", "65083", "53900", "29624"]
conn_count = sum(1 for line in result.stdout.split("\n") if any(p in line for p in ports))

# 3. 网关运行时间
try:
    pid = subprocess.run(
        ["pgrep", "-f", "hermes_cli.main gateway run"],
        capture_output=True, text=True, timeout=5
    ).stdout.strip().split("\n")[0]
    uptime = subprocess.run(
        ["ps", "-o", "etime=", "-p", pid],
        capture_output=True, text=True, timeout=5
    ).stdout.strip()
except Exception:
    uptime = "N/A"

# 4. 内存
mem = subprocess.run(["free", "-h"], capture_output=True, text=True, timeout=5).stdout
mem_line = [l for l in mem.split("\n") if "Mem" in l][0]
mem_parts = mem_line.split()
mem_used, mem_total = mem_parts[2], mem_parts[1]

# 5. Telegram 今日断连
today = datetime.now().strftime("%Y-%m-%d")
grep_result = subprocess.run(
    ["grep", today, "/root/.hermes/logs/gateway.log"],
    capture_output=True, text=True, timeout=5
)
if grep_result.stdout:
    disconnects = str(sum(1 for line in grep_result.stdout.split("\n")
                          if "polling restarted after network error" in line))
else:
    disconnects = "0"

print(f"📊 代理流量日报 — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("━━━━━━━━━━━━━━━━━━━━")
print(f"📡 本月累计流量：")
print(f"   入站: {rx_gb:.2f} GB")
print(f"   出站: {tx_gb:.2f} GB")
print()
print(f"🔌 代理端口连接数: {conn_count}")
print(f"🟢 网关运行时间: {uptime}")
print(f"📱 Telegram今日断连: {disconnects} 次")
print(f"💾 内存: {mem_used} / {mem_total}")
print("━━━━━━━━━━━━━━━━━━━━")
