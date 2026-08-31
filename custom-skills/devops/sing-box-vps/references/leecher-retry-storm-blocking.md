# 凭据轮换后的蹭流重试风暴 → 封禁 IP（2026-08-31 实战）

> 背景：换 UUID/密码后，蹭流用户的客户端**不知道凭据失效，仍会疯狂自动重连**。每次重连 → sing-box 处理 30 秒超时 → ERROR 刷爆 journal → 资源挤压 → **Telegram 网关周期性断联**（每 6-7 分钟一次）。

## 症状识别（Telegram 断联 ≠ WARP 问题！）

**第一嫌疑不是 WARP，而是蹭流重试风暴：**

1. gateway.log 规律性断联：`polling degraded (heartbeat probe)` + `RemoteProtocolError: Server disconnected`
2. syslog 中 sing-box 大量 `ERROR ... 30.xx s] inbound/vless[vless-sb]: process connection from <IP>`（**30 秒超时是典型特征**）
3. `/var/log/journal` 体积暴涨（实测 2.9GB）
4. ERROR 来源 IP 与之前蹭流 IP 相同（144.0.57.254 / 221.215.191.182 / 39.88.112.226 / 58.56.65.139 …）

## 诊断命令

```bash
# 汇总超时来源 IP（按次数排序）
grep "ERROR" /var/log/syslog | grep "inbound/vless" \
  | grep -oE "process connection from ([0-9.]+)" | awk '{print $4}' \
  | sort | uniq -c | sort -rn | head -20

# journal 占用
journalctl --disk-usage
```

## 封禁流程（治本）

```bash
# 1. 提取 IP 列表到文件（排除自己公网 IP！本地测试会产生自己的记录）
grep "ERROR" /var/log/syslog | grep "inbound/vless" \
  | grep -oE "process connection from ([0-9.]+)" | awk '{print $4}' \
  | grep -vE "^(10\.|127\.|169\.254|34\.3\.100\.22)" | sort -u > /tmp/leech_ips.txt

# 2. iptables DROP（INPUT 链最前面，比 UFW 更早拦截、更省资源）
while read ip; do
    iptables -I INPUT -s "$ip" -j DROP && echo "封禁: $ip"
done < /tmp/leech_ips.txt

# 3. 持久化（重启不丢）
mkdir -p /etc/iptables
iptables-save > /etc/iptables/rules.v4
# 若装了 netfilter-persistent 则用 netfilter-persistent save
```

## journal 清理与限容（防再爆）

```bash
# 清理（保留 100M）—— 实测释放 2.7GB
journalctl --vacuum-size=100M

# 限制上限 200M（⚠️ 目录要先建！否则 cat > 报 No such file）
mkdir -p /etc/systemd/journald.conf.d
cat > /etc/systemd/journald.conf.d/99-size.conf << 'EOF'
[Journal]
SystemMaxUse=200M
EOF
systemctl restart systemd-journald
```

## 验证封禁生效

```bash
# ERROR 数量不再增长 = 生效（记数 → 等 20 秒 → 再记数，应相等）
grep -c "ERROR.*inbound/vless" /var/log/syslog

# iptables 命中计数
iptables -L INPUT -n -v | grep DROP
```

## 教训

- 换凭据后**必须**监控几小时的超时日志——蹭流客户端会自动重试，不会立即消失
- 封禁用 iptables 直接操作 INPUT 链（UFW 也是 iptables 封装，但直接操作最前面效率最高）
- 自己的公网 IP 要从封禁列表排除
- journal 限容是必须的：sing-box info 级日志量大，不限容迟早爆盘
- Telegram 断联先查蹭流重试风暴，再查 WARP——别一上来就动 WARP 配置
