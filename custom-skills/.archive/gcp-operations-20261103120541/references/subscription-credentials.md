# 订阅凭据对照表 & 修复流程（2026-08 血的教训）

> 背景：2026-08 跑了一次 push-sub-to-github.py，把 /etc/s-box/custom-sub.yaml 覆盖成旧配置（旧 UUID + 旧 REALITY 公钥 + talktone 规则），导致所有客户端节点超时，用户暴怒。

## 权威文件

| 文件 | 角色 |
|------|------|
| `/etc/s-box/sb.json` | **唯一权威** — sing-box 实际运行的配置 |
| `/etc/s-box/custom-sub.yaml` | Clash 订阅（给客户端），**必须与 sb.json 凭据一致** |
| `/root/.hermes/scripts/push-sub-to-github.py` | ⛔ 已损坏（硬编码旧配置），**禁止运行** |

## 凭据一致性检查（5 项全对齐才算好）

```bash
# 订阅输出 vs sb.json 对比
SUB=$(curl -s -m 5 http://127.0.0.1:443/)
echo "$SUB" | grep -oE '[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}' | sort -u   # UUID
grep -oE '[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}' /etc/s-box/sb.json | sort -u  # 服务器 UUID
# 两者必须相等
```

| 参数 | 位置（订阅文件） | 位置（sb.json） | 说明 |
|------|-----------------|-----------------|------|
| VLESS UUID | `proxies[0].uuid` | inbounds vless users[].uuid | 直接抄 |
| VMESS UUID | `proxies[1].uuid` | inbounds vmess users[].uuid | 直接抄 |
| TUIC UUID | tuic 块 `uuid` | inbounds tuic users[].uuid | 直接抄 |
| REALITY public-key | `reality-opts.public-key` | **无直接字段** — 从 tls.reality.private_key 用 x25519 推导 | 见下方代码 |
| REALITY short-id | `reality-opts.short-id` | tls.reality.short_id[0] | 直接抄 |
| hy2 密码 | hysteria2 块 `password` | inbounds hy2 users[].password | 直接抄 |
| TUIC token | tuic 块 `token` | inbounds tuic users[].password | 直接抄 |
| anytls 密码 | anytls 块 `password` | inbounds anytls users[].password | 直接抄 |

## REALITY 公钥推导（private_key → public-key）

sb.json 里只有 private_key，订阅文件需要 public-key。用 x25519 推导：

```python
import base64

priv_b64 = "..."  # sb.json tls.reality.private_key
padded = priv_b64.replace("-", "+").replace("_", "/")
padded += "=" * ((4 - len(padded) % 4) % 4)
raw = base64.b64decode(padded)

from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey
priv = X25519PrivateKey.from_private_bytes(raw)
pub = priv.public_key().public_bytes_raw()
pub_b64url = base64.b64encode(pub).decode().rstrip("=").replace("+", "-").replace("/", "_")
print(pub_b64url)
```

注意 REALITY 密钥对是 base64url 无填充格式，直接 b64decode 会因 41 字符报错，必须先转标准 base64。

## 修复污染文件的流程（本次实战验证）

1. `cp /etc/s-box/custom-sub.yaml /etc/s-box/custom-sub.yaml.bak-$(date +%s)` 备份
2. 从 sb.json 提取真实 UUID / 密码 / short_id（`grep` 或 python json）
3. 推导 REALITY public-key（见上）
4. 用 python 按协议块精确替换（**别用全局 sed 替换 UUID** — 旧配置里 hy2/tuic/anytls 的密码恰好也是旧 UUID，全局替换会把密码也改错；要按块定位）
5. `systemctl restart subscription-server.service`（无路径检查，无需动端口）
6. 验证：`curl -s http://127.0.0.1:443/ | grep -E "uuid:|password:|token:|public-key:|short-id:"` 与 sb.json 逐项对比

## 关键教训

- 服务器跑的是 sb.json 里的密钥；订阅文件只是给客户端的"说明书"——两者不一致 = 全部节点超时
- VLESS 超时先查 REALITY（公钥/short-id），不是 UUID！REALITY 握手靠公钥，UUID 只是用户标识
- **改任何配置前先搜知识库**（/home/projects/hermes-knowledge/环境配置/代理订阅配置.md 有同步记录）
- 用户铁律：**UUID/ID 一律不动**，只做被要求的最小改动
