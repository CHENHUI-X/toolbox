# SOCKS5 10808 外部访问封禁

SOCKS5 端口（默认 10808）**无密码协议**，公网开放后任何人都能蹭用。即使 sing-box 配置只用于本地 Telegram WARP，外部扫描器仍能发现并滥用。

## 检测方法

```bash
# 查看 10808 上非本地的连接
ss -tnp | grep 10808 | grep -v "127.0.0.1"

# 从外部测试（应在另一台机器上执行）
curl -s --max-time 3 --proxy socks5://<公网IP>:10808 http://ifconfig.me
# 应返回"Connection refused"或超时

# 检查 iptables 规则
iptables -L INPUT -nv | grep 10808
```

## 封禁方案：iptables 优先级规则

核心逻辑：**先放行本地 127.0.0.1，再 DROP 所有其他来源**。两条规则的顺序至关重要：

```bash
# 第1条：放行本地（必须在前）
iptables -A INPUT -p tcp --dport 10808 -s 127.0.0.1 -j ACCEPT

# 第2条：拒绝其他所有（必须在后）
iptables -A INPUT -p tcp --dport 10808 -j DROP
```

**为什么不能只用 UFW？** UFW 的规则是 stateful — 它只阻止外部新建连接，但对已建立的连接没影响。而 iptables DROP 规则是无条件的，任何非本地来源的包都会被丢弃。

### 删除 UFW 放行规则（如存在）

```bash
ufw delete allow 10808/tcp 2>/dev/null
```

## 验证

```bash
# 查看规则（ACCEPT 127.0.0.1 在前，DROP 在后）
iptables -L INPUT -nv | grep 10808
#    0     0 ACCEPT     tcp  --  *      *       127.0.0.1            0.0.0.0/0            tcp dpt:10808
#  397 23820 DROP       tcp  --  *      *       0.0.0.0/0            0.0.0.0/0            tcp dpt:10808

# 从外部测试连接
curl -s --max-time 3 --proxy socks5://<公网IP>:10808 http://ifconfig.me
# ✅ 外部连接被拒绝（空输出或 curl: (7) Connection refused）

# 本地测试（Telegram WARP 不受影响）
curl -s --max-time 3 --proxy socks5://127.0.0.1:10808 http://ifconfig.me
# ✅ 返回本机公网IP，本地正常
```

## 效果对比

| 项目 | 封禁前 | 封禁后 |
|------|--------|--------|
| 外部连接测试 | 返回公网IP（被蹭） | 连接被拒绝 |
| 本地（Telegram WARP 127.0.0.1） | 正常 | 正常 |
| sing-box 日志 | 持续看到外部 IP 连 10808 | 仍有扫描尝试记录但被 iptables 丢弃 |
| 出站流量影响 | 外部扫描器产生无意义流量 | 归零 |

## 注意事项

- iptables 规则在**重启后消失**（除非用 `iptables-save` 持久化）。如果需要持久化，安装 `iptables-persistent` 或写进启动脚本。
- iptables 规则不会影响 sing-box 自身对 10808 的监听。sing-box 仍然接受连接请求，但 iptables 在数据包进入前就丢弃了——所以连接根本到不了 sing-box。
- 只封 TCP（SOCKS5 不需要 UDP），`--dport 10808` 默认即 TCP。
