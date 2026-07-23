# SOCKS5 Inbound for Direct Telegram Proxy

sing-box 除了作为代理服务器接受外部的 Vless/VMess/Hy2/TUIC 连接以外，还可以作为 **SOCKS5 入站代理** 直接给 Telegram 等 App 用。

## 适用场景

- **无需 Stash/Clash 等客户端** — Telegram 直接填服务器地址和端口
- **公共 WiFi / 朋友手机 / 临时设备** — 填个代理配置就能用
- **搭配现有节点** — SOCKS5 入站可以通过 sing-box 路由规则走 direct 出口，流量从服务器直出

## 配置方法

### 1. 添加 SOCKS5 入站

编辑 `/etc/s-box/sb.json`，在 `inbounds` 数组中添加：

```json
{
    "type": "socks",
    "tag": "socks-in",
    "listen": "::",
    "listen_port": 10808,
    "users": []
}
```

- `"listen": "::"` — 监听所有网卡（IPv4 + IPv6），公网可访问
- `"users": []` — 空数组 = 无认证模式（建议，方便临时设备连接）
- 如果要用用户名密码，填：

```json
"users": [
    {
        "username": "telegram",
        "password": "your-password"
    }
]
```

### 2. （可选）添加路由规则

如果希望 SOCKS5 入站的流量走特定的出口（比如直接出口，不走代理节点）：

```json
{
    "inbound": ["socks-in"],
    "outbound": "direct"
}
```

放在 `route.rules` 数组中。不加规则的话默认走第一个 outbound。

### 3. 校验并重启

```bash
/etc/s-box/sing-box check -c /etc/s-box/sb.json
systemctl restart sing-box
```

### 4. 开放防火墙

```bash
# VM 防火墙
iptables -A INPUT -p tcp --dport 10808 -j ACCEPT

# GCP 云防火墙（如需）
gcloud compute firewall-rules create allow-socks5 \
  --allow tcp:10808 \
  --source-ranges 0.0.0.0/0 \
  --target-tags http-server
```

## 关键陷阱：SOCKS5 → direct 出口不能解决 GCP 网络问题

**如果你在 GCP 上跑 sing-box，SOCKS5 入站走 `direct` 出口，流量路径是：**

```
Telegram App → 服务器公网IP:10808 → socks-in → direct → GCP 直连互联网
```

这意味着 Telegram API 的流量 **最终还是从 GCP 直连出去** 的。如果 GCP 到 Telegram API（`api.telegram.org`）的网络本身就不稳定（GCP 常见问题），这个代理配置**没有任何改善作用**。

**要真正改善 GCP → Telegram 的网络稳定性，必须让 Telegram API 流量走不同的出口通道。**

## 通过 WARP 出口改善 Telegram 稳定性

如果 sing-box 配置了 WARP（Cloudflare WireGuard）出站，可以把 Telegram API 的 DNS 域名路由到 WARP 出口，利用 Cloudflare 的网络路径绕开 GCP 直连的拥堵。

### 方案：域名规则分流

在 `route.rules` 中添加：

```json
{
    "domain_suffix": [
        "telegram.org",
        "api.telegram.org",
        "t.me",
        "telegra.ph"
    ],
    "outbound": "warp-out"
}
```

**注意事项：**
- `warp-out` 必须在 `endpoints` 中有对应的 WireGuard 配置（见 SKILL.md 的 WARP 配置）
- 规则放在 `direct` 兜底规则**之前**（sing-box 规则顺序匹配）
- 如果 `socks-in` 有专门的路由规则（`"inbound": ["socks-in"], "outbound": "direct"`），它和上面的域名规则是 AND 还是 OR 关系取决于规则动作。更好的做法是：
  - 不要给 `socks-in` 指定固定的 `direct` 出站
  - 让 sing-box 走正常的域名/SNI 嗅探路由，这样 Telegram API 流量自然走 WARP，其他流量走 direct

### 推荐的完整路由规则结构

```json
"route": {
    "rules": [
        // 嗅探优先
        { "action": "sniff" },
        // Telegram API → WARP 出口
        {
            "domain_suffix": [
                "telegram.org",
                "t.me",
                "telegra.ph"
            ],
            "outbound": "warp-out"
        },
        // socks-in 入站的其他流量走 direct
        {
            "inbound": ["socks-in"],
            "outbound": "direct"
        },
        // 兜底
        {
            "network": "udp,tcp",
            "outbound": "direct"
        }
    ]
}
```

## 验证 WARP 出口是否生效

```bash
# 检查 WARP 接口是否启动
wg show

# 查看 sing-box 日志确认路由
journalctl -u sing-box.service --no-pager -n 50 | grep -i "telegram\\|warp"

# 验证 Telegram 是否通过 WARP 出站
# SSH 到服务器，用 curl 显式走 socks5 测试
curl -s --socks5 127.0.0.1:10808 https://api.telegram.org/bot<TOKEN>/getMe
```

## Hermes Gateway 集成：通过 WARP 改善 GCP 网络稳定性

当 Hermes Gateway 运行在 GCP VM 上且 Telegram 频繁断连（`httpx.ReadError: Server disconnected without sending a response`），可通过 sing-box SOCKS5 入站 + WARP 出口解决。

### 问题诊断

GCP 直连 Telegram API 的网络不稳定，日志表现为：
```
[Telegram] Telegram network error (attempt 1/10), reconnecting in 5s. Error: httpx.ReadError:
[Telegram] Telegram polling restarted after network error (attempt 1)
```
curl 测试 api.telegram.org 正常（302 in 0.4s），但长轮询（getUpdates 30s timeout）频繁断连。

### 方案

让 Telegram 流量走本地 sing-box（SOCKS5 入站） → WARP 出站，利用 Cloudflare 网络出口。

**关键点：必须用 `127.0.0.1`（本地回环），不能用公网 IP。**

```bash
# 错误：公网 IP 产生回环，流量还是走 GCP 原网络
TELEGRAM_PROXY=socks5://<公网IP>:10808   # ❌

# 正确：本地 sing-box SOCKS5 入站
TELEGRAM_PROXY=socks5://127.0.0.1:10808   # ✅
```

### 配置步骤

**Step 1 — 确认 sing-box 有 SOCKS5 入站和 WARP 出站：**

```json
{
  "inbounds": [
    {
      "type": "socks",
      "tag": "socks-in",
      "listen": "::",
      "listen_port": 10808
    }
  ],
  "endpoints": [
    {
      "type": "wireguard",
      "tag": "warp-out",
      "address": ["172.16.0.2/32", "2606:4700:110:xxxx/128"],
      "private_key": "...",
      "peers": [{
        "address": "162.159.192.1", "port": 2408,
        "public_key": "bmXOC+F1FxEMF9dyiK2H5/1SUtzH0JuVo51h2wPfgyo=",
        "allowed_ips": ["0.0.0.0/0", "::/0"],
        "reserved": [63, 126, 139]
      }]
    }
  ]
}
```

**Step 2 — 添加路由规则**（Telegram API 域名 + 整段 Telegram IP 段走 WARP，插入在 warp-out 现有规则之后、direct 兜底之前）：

```json
{
  "domain": ["api.telegram.org"],
  "outbound": "warp-out"
},
{
  "ip_cidr": [
    "149.154.166.0/24",
    "149.154.160.0/20",
    "91.108.4.0/22",
    "91.108.56.0/22"
  ],
  "outbound": "warp-out"
}
```

**Step 3 — 配置 Hermes 使用本地代理：**

```bash
echo 'TELEGRAM_PROXY=socks5://127.0.0.1:10808' >> /root/.hermes/.env
```

**Step 4 — 重启服务并验证：**

```bash
systemctl restart sing-box
# 网关需从外部进程重启（system cron 或 execute_code fork）
# 验证代理生效：
grep "Proxy detected" ~/.hermes/logs/gateway.log | tail -1
# 期望: socks5://127.0.0.1:10808
```

### 效果验证

对比 WARP 前后断连次数：
```bash
# 改之前
grep "polling restarted after network error" ~/.hermes/logs/gateway.log | grep -c "2026-07-22"
# 改之后（从某条日志行号之后）：
grep "polling restarted after network error" ~/.hermes/logs/gateway.log | awk -F: '$1 > 25233' | wc -l
```

## 其他可选出口方案

| 出口 | 适用场景 | 配置注意 |
|------|---------|---------|
| **WARP (wireguard)** | Cloudflare 网络，免费，多数情况下稳定 | 需 WireGuard 配置，延迟略高于直连 |
| **socks-out** | 如果有第三方 SOCKS5 代理 | 指向 `127.0.0.1:40000` 或远程代理 |
| **自定义 outbound** | 任意自定义协议 | 需要对应出站配置 |

## Telegram 客户端配置

| 字段 | 值 |
|:--|:--|
| 类型 | **SOCKS5** |
| 地址 | `服务器IP` 或 `DDNS域名` |
| 端口 | **10808**（可自定义） |
| 用户名 | 留空（无认证模式）/ `telegram` |
| 密码 | 留空 / 你的密码 |

Settings → Data and Storage → Proxy → Add Proxy → SOCKS5

## 注意事项

- **无 SOCKS5 加密** — SOCKS5 协议本身没有传输层加密。如果担心流量被中间人窥探，建议走 TLS 隧道（如 Nginx 反向代理 + TLS），或者接受在服务器+客户端之间有信任的网络（如自建 VPS 直连）。
- **端口别冲突** — 10808 是常用 SOCKS5 端口，确认没有被其他服务占用。
- **GCP 双防火墙** — 即使 VM 内 iptables 开了，GCP 云防火墙层面也要放行。参见 `gcp-operations` skill 的防火墙章节。
- **用户密码建议去掉** — 临时设备用无密码更方便。如果担心被扫描，改一个非标准端口即可。
- **域名规则顺序** — `direct` 兜底规则必须是最后一条，否则域名分流规则不生效。
