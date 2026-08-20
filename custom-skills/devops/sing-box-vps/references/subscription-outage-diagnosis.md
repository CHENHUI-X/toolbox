# 订阅节点全挂排查（2026-08-19 事故续）

事故复盘续篇：`references/subscription-edit-pitfalls.md` 记录了 push-sub-to-github.py 污染 UUID 的教训。本文件补充当天进一步排查出的两个根因与修复。

## 根因1：REALITY 公钥/short-id 不匹配（不只是 UUID）

**症状**：客户端全部节点超时；sing-box 日志：
```
ERROR inbound/vless[vless-sb]: TLS handshake: REALITY: processed invalid connection
```

**原因**：订阅文件被旧脚本污染时，REALITY 的 `public-key` 和 `short-id` 一起变旧（与 sb.json 的 `private_key`/`short_id` 不匹配）。**UUID 只是用户标识，REALITY 握手靠公钥对 + short-id** —— 只改 UUID 不够。

**验证订阅文件是否与服务器一致（全面对比）**：
```bash
# 订阅输出 vs sb.json 的 UUID
curl -s http://127.0.0.1:443/ | grep -oE '[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}' | sort -u
grep -oE '[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}' /etc/s-box/sb.json | sort -u
# REALITY 公钥/short-id
grep -A3 reality-opts /etc/s-box/custom-sub.yaml
python3 -c "import json; d=json.load(open('/etc/s-box/sb.json')); print(d['inbounds'][0]['tls']['reality'])"
```

**从 sb.json 私钥推导正确公钥**（不猜、不用旧文件里的值）：
```python
import base64
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey
priv_b64 = "<reality.private_key>"   # base64url 无填充
padded = priv_b64.replace("-", "+").replace("_", "/") + "=" * ((4 - len(priv_b64) % 4) % 4)
priv = X25519PrivateKey.from_private_bytes(base64.b64decode(padded))
pub = base64.b64encode(priv.public_key().public_bytes_raw()).decode().rstrip("=").replace("+", "-").replace("/", "_")
print(pub)   # 应填入订阅文件 public-key
```

**修复陷阱**：`sed` 全局替换会把所有旧 UUID 换成新 UUID —— 但旧配置里 **hy2/tuic/anytls 的 password/token 恰好就是旧 UUID 字符串**，会被一起误改（正确密码是独立字符串如 `51ed628...`）。修复必须按协议块定位：
```python
content = content.replace(
    "  password: <new_uuid>\n  sni: google.cloud.eosphor.dpdns.org",
    "  password: <real_password>\n  sni: google.cloud.eosphor.dpdns.org")
```
用 `password: X\n  sni:` / `token: X` 等上下文锚点逐块替换，改完 curl 验证输出。

## 根因2：订阅服务单线程假死

**症状**：`curl -s http://127.0.0.1:443/` 返回**空**（0 bytes），但进程活着、端口 LISTEN。`ss -tlnp` 显示 Recv-Q 排队（如 `LISTEN 6 5`）。

**原因**：`http.server.HTTPServer` 是单线程，一个慢连接/未关闭连接卡住 handler，后续所有请求排队等死。

**永久修复**（已应用到 `/root/.hermes/scripts/subscription-server.py`）：
```python
server = http.server.ThreadingHTTPServer(('0.0.0.0', PORT), SubHandler)
server.daemon_threads = True
```
改完 `systemctl restart subscription-server.service`。临时救急 = 直接 restart。

**验证**：
```bash
curl -s -m 5 http://127.0.0.1:443/ | head -3     # 应返回订阅
curl -s -m 8 -o /dev/null -w "%{http_code}" http://google.cloud.eosphor.dpdns.org:443/   # 公网 200
```

## 检查清单（节点全挂时按序排查）

1. `systemctl is-active sing-box` — 进程活着吗
2. `ss -tlnp | grep -E "33741|2096|65083|53900|29624"` — TCP 端口监听（hy2/tuic 是 UDP：`ss -ulnp`）
3. `journalctl -u sing-box -n 20 | grep ERROR` — 有无 REALITY 握手错误
4. `curl -s http://127.0.0.1:443/ | head` — 订阅服务活着吗（空 = 单线程假死 → restart）
5. 订阅输出 UUID/公钥/short-id vs sb.json — 凭据一致吗
6. `curl -s https://api.ipify.org` — IP 变了吗（变了 → DDNS/订阅里 server 字段）
7. `ufw status` — 端口放行了吗
