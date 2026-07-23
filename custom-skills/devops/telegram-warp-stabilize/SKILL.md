---
name: telegram-warp-stabilize
description: "通过 sing-box WARP 出口稳定 Telegram 连接 — 解决 GCP 连 Telegram API 网络不稳定的问题"
version: 1.0
author: Hermes Agent
---

# Telegram WARP 稳定连接

## 问题

GCP 服务器连 Telegram API 经常断连，每天断十几次，导致 Telegram 一直显示"正在输入"、消息延迟甚至收不到。

## 解决方案

让 Telegram 流量通过 sing-box 的 WARP（Cloudflare WireGuard）出口，不走 GCP 原生网络。

## 前置条件

- sing-box 已安装并运行
- sing-box 配置中已有 `endpoints` 配置了 `warp-out`（WireGuard / Cloudflare WARP）
- sing-box 已配置 `socks-in` 入站（端口 10808）

## 步骤

### 1. 修改 sing-box 配置，添加 Telegram 路由规则

在 sing-box 配置的 `route.rules` 中，找到 `warp-out` 的出站规则，在其后添加 Telegram 的域名和 IP 段规则：

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

### 2. 设置 Telegram 代理

在 `/root/.hermes/.env` 中添加或修改：

```
TELEGRAM_PROXY=socks5://127.0.0.1:10808
```

⚠️ 注意：走 `127.0.0.1` 本地 sing-box，不要走外部 IP（否则回环回 GCP 自身，等于没走代理）。

### 3. 重启服务

```bash
systemctl restart sing-box
systemctl restart hermes-gateway
```

### 4. 验证

```bash
# 检查网关日志是否识别到代理
grep "Proxy detected" ~/.hermes/logs/gateway.log | tail -3

# 观察断连次数是否下降
grep "polling restarted after network error" ~/.hermes/logs/gateway.log | wc -l
```

## 效果

改之前：每天断连 15~30 次
改之后：连续运行 29+ 小时无断连

## 注意事项

- Cloudflare WARP 免费且流量不限量
- 流量路径：Gateway → SOCKS5(127.0.0.1:10808) → sing-box 路由 → warp-out(Cloudflare WARP) → Telegram API
- 如果 sing-box 配置中没有 warp-out，需要先配置 WARP WireGuard 端点
