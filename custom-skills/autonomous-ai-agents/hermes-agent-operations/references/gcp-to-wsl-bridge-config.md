# GCP → WSL 双向通信桥接配置（SSH Reverse Tunnel）

## 架构

```
WSL Hermes  ──SSH reverse tunnel──►  GCP Hermes
(WeChat)    :8644 ←reverse tunnel   :8644 (GCP localhost → WSL)
            :8645 (listener)         :8645 (GCP public listener → WSL)
```

GCP 通过本地 8644 端口（SSH 反向隧道）直接访问 WSL 的 Hermes Webhook，无需 WSL 暴露公网 IP。

## GCP 侧确认隧道状态

```bash
# 隧道存活检查
ss -tlnp | grep 8644
# ✅ LISTEN 127.0.0.1:8644 → 隧道正常
# ❌ 无输出 → 隧道断开

# 连接测试
curl -s http://localhost:8644/health
# → {"status": "ok", "platform": "webhook"}
```

## GCP → WSL 发送消息

### 配置文件

保存在 `/root/wsl-bridge-config.json`:

```json
{
  "direction": "GCP → WSL",
  "method": "POST http://localhost:8644/webhooks/gcp-to-wsl",
  "secret": "XXX",
  "signing": "HMAC-SHA256, header: X-Webhook-Signature",
  "payload_example": {
    "event_type": "task",
    "message": "GCP 发来的消息"
  }
}
```

### 发送测试命令 (Python)

```python
import json, hmac, hashlib, urllib.request
s = b'<secret>'
p = json.dumps({'event_type': 'task', 'message': '测试消息'}).encode()
sig = hmac.new(s, p, hashlib.sha256).hexdigest()
req = urllib.request.Request('http://localhost:8644/webhooks/gcp-to-wsl',
    data=p, headers={'Content-Type': 'application/json', 'X-Webhook-Signature': sig})
resp = urllib.request.urlopen(req, timeout=15)
print(resp.status, resp.read().decode())
# → 202 {"status": "accepted", "route": "gcp-to-wsl", ...}
```

### Payload 格式要点

- WSL 端对 **flat 格式** payload 响应更好：`{"event_type": "task", "message": "..."}` → 202 accepted
- 嵌套格式 `{"event": "task", "data": {"task": "..."}}` 可能被忽略（返回 200 `ignored` / `unknown event`）
- 签名 header 是 `X-Webhook-Signature`（纯 hex 小写），不是 `X-Hub-Signature-256`
- 不同 Hermes 实例/不同安装版本接受的 HMAC header 名称可能不同

### 注意事项

- 隧道依赖 WSL 侧主动建立的 SSH 连接，WSL 断开或休眠后隧道自动断开
- 隧道断开后 GCP 侧 `curl localhost:8644` 返回 `Connection refused`
- 恢复方式：WSL 重新执行 `ssh -R 8644:localhost:8644 root@<GCP_IP>`
- 建议在 WSL 侧设置 cron 或 systemd 自动保活隧道
- Webhook secret 在订阅重建后变更，GCP 侧需同步更新
