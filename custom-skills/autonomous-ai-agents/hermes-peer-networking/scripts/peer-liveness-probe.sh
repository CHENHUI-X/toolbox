#!/bin/bash
# 两机存活确认探针：本机服务 → a2a 隧道 → Syncthing 连接 → 对端端口/指纹
# 用法: bash peer-liveness-probe.sh <对端IP> [对端api_server端口, 默认9901]
set -u
PEER_IP="${1:?用法: $0 <对端IP> [api端口]}"
API_PORT="${2:-9901}"

probe_port() { # $1=ip $2=port
  timeout 6 bash -c "echo > /dev/tcp/$1/$2" 2>/dev/null
}

say() { printf '  %s\n' "$*"; }

say "=== 本机 ==="
say "host=$(hostname) ip=$(hostname -I 2>/dev/null | awk '{print $1}') up=$(uptime -p 2>/dev/null) now=$(date '+%F %T %Z')"
for s in hermes-gateway syncthing nginx sing-box; do
  st=$(systemctl is-active "$s" 2>/dev/null)
  [ -n "$st" ] && say "$s: $st"
done
say "listening: $(ss -tln 2>/dev/null | awk 'NR>1{print $4}' | grep -oE ':(9900|9901|9902|8384)$' | sort -u | tr '\n' ' ')"

say "=== a2a 隧道 ==="
tun=$(systemctl is-active a2a-tunnel 2>/dev/null); say "a2a-tunnel: ${tun:-absent}"
if [ "${tun:-absent}" != "active" ]; then
  first=$(journalctl -u a2a-tunnel --since '-14d' -o short-iso --no-pager 2>/dev/null \
          | grep -m1 -E 'host key check failure|Permission denied|Connection refused|Connection timed out')
  say "最早失败: ${first:-未取到（可能从未成功过）}"
  say "近24h失败条数: $(journalctl -u a2a-tunnel --since '-24h' --no-pager 2>/dev/null \
          | grep -cE 'host key check failure|Permission denied')"
fi

say "=== Syncthing 连接 ==="
CFG=/root/.local/state/syncthing/config.xml
if [ -r "$CFG" ]; then
  KEY=$(grep -oE '<apikey>[^<]+' "$CFG" | cut -d'>' -f2)
  curl -s -m 8 -H "X-API-Key: $KEY" http://127.0.0.1:8384/rest/system/connections \
    | python3 -c 'import sys,json
d=json.load(sys.stdin)
for k,v in d.get("connections",{}).items():
    print("  %s connected=%s addr=%s" % (k[:7], v.get("connected"), v.get("address") or "-"))' 2>/dev/null \
    || say "API 无响应（syncthing 未运行？）"
else
  say "读不到 $CFG"
fi

say "=== 对端 $PEER_IP ==="
for p in 22 "$API_PORT" 80 443; do
  if probe_port "$PEER_IP" "$p"; then say "tcp/$p 可连"; else say "tcp/$p 不可连"; fi
done
code=$(curl -sSk -m 8 -o /dev/null -w '%{http_code}' "http://$PEER_IP:$API_PORT/health" 2>/dev/null)
say "api/health -> ${code:-000}  (000=不通; 200/401/404 属可达)"

say "=== 主机指纹（只读，不落盘） ==="
cur=$(timeout 10 ssh-keyscan -T 5 -t ed25519,rsa "$PEER_IP" 2>/dev/null | ssh-keygen -lf - 2>/dev/null)
say "当前: ${cur:-取不到（22 不通或 sshd 未应答）}"
known=$(ssh-keygen -F "$PEER_IP" 2>/dev/null | ssh-keygen -lf - 2>/dev/null)
say "已存: ${known:-known_hosts 无记录}"
if [ -n "$cur" ] && [ -n "$known" ] && [ "$(echo "$cur" | awk '{print $2}' | sort -u | tr '\n' ' ')" != "$(echo "$known" | awk '{print $2}' | sort -u | tr '\n' ' ')" ]; then
  say "⚠️ 指纹不一致 = 对端 sshd 被重装/重配或 IP 易主；报告用户并等确认，别自动写 known_hosts。"
fi
