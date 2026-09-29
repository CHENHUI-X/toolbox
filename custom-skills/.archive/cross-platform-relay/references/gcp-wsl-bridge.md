# GCP ↔ WSL Hermes 双向通信桥梁

## GCP 侧（已配置）

| 项目 | 值 |
|:--|:--|
| 公网 IP | `34.3.100.22` |
| Webhook 端口 | `8645` |
| 平台密钥 | `gcp-wsl-bridge-secret-2026` |
| 订阅名称 | `wsl-to-gcp` |
| 订阅密钥 | `huEaDGl1dCMLPFMcWcS4PK32qTZRZZzkyUi3yy8CJYo` |

## WSL → GCP

WSL Hermes 向 GCP webhook 发送 POST：

```bash
POST http://34.3.100.22:8645/webhooks/wsl-to-gcp
Content-Type: application/json
X-Hub-Signature-256: sha256=<HMAC-SHA256(secret, body)>
```

Body: `{"message": "要发送的内容"}`

验证 webhook 是否活着：
```bash
curl http://34.3.100.22:8645/health
# → {"status": "ok", "platform": "webhook"}
```

## GCP → WSL

需要 WSL 侧开 SSH 反向隧道才能从 GCP 主动连 WSL：

```bash
# 在 WSL 上执行：
ssh -R 8646:localhost:8645 root@34.3.100.22
```

之后 GCP 可以向 `localhost:8646` POST，隧道会转发到 WSL 的 webhook。

## GCP 公网 IP 变更处理流程

GCP VM 的临时公网 IP 会在实例停止/启动时变化（ephemeral IP）。IP 变更后需要以下操作：

### 1. 检测
已有 cron job `/etc/cron.d/gcp-ip-check` 每30分钟检测一次，IP 变了会自动通过 Telegram 通知。

### 2. 更新清单

| # | 操作 | 示例文件 |
|---|------|---------|
| 1 | 更新本参考文件的 IP | `references/gcp-wsl-bridge.md` |
| 2 | 更新 clmi.yaml 中 vless-reality 的 server 字段 | `/etc/s-box/clmi.yaml` |
| 3 | 更新 DDNS 域名解析（如 dpdns.org 后台） | `google.cloud.eosphor.dpdns.org` |
| 4 | 更新 vault 服务器配置 | `~/.hermes/vault/🖥️ 服务器配置.md` |
| 5 | 更新 memory 中的 IP 记录 | `memory` tool |
| 6 | 通知用户更新 Clash 客户端配置（如用订阅链接则自动） | Telegram 通知 |

### 3. clmi.yaml 更新命令

```bash
# 替换 vless-reality 节点的 IP
sed -i 's/server: OLD_IP/server: NEW_IP/' /etc/s-box/clmi.yaml

# 验证更新结果
grep "server:" /etc/s-box/clmi.yaml | head -5
```

### 4. DDNS 域名更新

如果用了像 `google.cloud.eosphor.dpdns.org` 这样的 DDNS 域名，需要去域名提供商后台更新 A 记录指向新 IP。其他节点（vmess-ws, hysteria2, tuic5, anytls）都依赖这个域名解析。

## 现有 GCP 配置

```yaml
# config.yaml
platforms:
  webhook:
    enabled: true
    extra:
      host: 0.0.0.0
      port: 8645
      secret: gcp-wsl-bridge-secret-2026
```
