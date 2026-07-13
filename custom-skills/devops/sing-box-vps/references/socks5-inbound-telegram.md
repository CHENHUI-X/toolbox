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
