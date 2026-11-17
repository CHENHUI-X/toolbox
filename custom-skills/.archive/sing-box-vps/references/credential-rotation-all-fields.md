# 凭据轮换：只换 UUID 不够 — 所有凭据字段一次全换（2026-08-29 实战暴怒教训）

**用户原话（暴怒）：** "我他妈真服了，你全面排查把所有的秘密链接所有的ID全给我换成新的全部用密码加全"
**用户要求（先前的教训）：** "以后记住，一次性给我修改好"

## 核心教训：只换 UUID 后"旧订阅还能用"

实测场景：轮换时只替换了 `uuid` 字段，用户反馈**旧订阅依然能连**。原因是 sing-box 各协议有**多种独立凭据**，只换 UUID 会漏掉其余。

## 必须一起轮换的凭据（不止 UUID）

| 凭据类型 | 协议/位置 | 为什么必须换 |
|---------|----------|-------------|
| `uuid` | vless (33741) / vmess (2096) / tuic (53900) 的 `users[].uuid` | 主凭据 |
| `password` | **hy2 (65083) / anytls (29624) / tuic** 的 `users[].password` | ⚠️ 独立于 UUID！yonggekkk 脚本生成的是 20 位 hex 密码，**不是** UUID 格式。漏换 → 旧订阅 hy2/anytls/tuic 节点照样连 |
| `private_key` + `short_id` | sb.json vless 的 `tls.reality` | Reality 密钥对，必须配套换 |
| `public-key` + `short-id` | custom-sub.yaml 的 vless 段 | ⚠️ 与 sb.json 的 private_key **配套**。漏换 → 订阅里 vless 节点连不上（公钥不匹配）或旧公钥仍在 |
| `transport.path` | sb.json vmess | ⚠️ 路径嵌着 UUID（`/<uuid>-vm` 格式），**JSON 遍历 users 会漏**，必须字符串级替换 |

## 替换技巧（防漏）

```python
# sb.json 用字符串级替换（覆盖 transport.path 等嵌套字段）：
raw = json.dumps(cfg, ensure_ascii=False)
raw = raw.replace(old_uuid, new_uuid).replace(old_pw, new_pw)
cfg = json.loads(raw)

# 其他文本文件逐个 replace（先备份 .bak-YYYYMMDD）
```

## 轮换后的验证（必须做）

```bash
# 1. 全盘扫描旧凭据 0 残留（UUID + 密码 + 公钥 + short-id 全查）
grep -rlE "旧UUID|旧密码|旧公钥|旧short-id" /etc/s-box/ --exclude=*.bak*

# 2. 重启 sing-box + 订阅服务
systemctl restart sing-box
systemctl restart subscription-server.service

# 3. 验证订阅输出全部为新凭据
curl -s "http://127.0.0.1:443/nx4hspzb?key=订阅密码" | grep -c "新UUID"   # 应为 4+
curl -s "http://127.0.0.1:443/nx4hspzb?key=订阅密码" | grep -c "新密码"   # 应为 3

# 4. UDP 端口检查（hy2/tuic 是 UDP）
ss -ulnp | grep -E "65083|53900"
```

## 订阅服务密码鉴权（防再次泄露，2026-08-29 新增）

订阅链接如果外泄，换凭据只是临时措施——旧用户重新拉订阅就能拿到新凭据。**彻底方案：给订阅服务加密码鉴权**（`?key=` 参数）。

```python
# /root/.hermes/scripts/subscription-server.py
import json, os
from urllib.parse import urlparse, parse_qs

KEY_FILE = '/etc/s-box/sub-key'   # 密码存独立文件，不硬编码

class SubHandler(http.server.BaseHTTPRequestHandler):
    def _check_key(self):
        with open(KEY_FILE) as f:
            valid_key = f.read().strip()
        qs = parse_qs(urlparse(self.path).query)
        provided = (qs.get('key') or qs.get('token') or [''])[0]
        return provided == valid_key

    def do_GET(self):
        if not self._check_key():
            self.send_response(401)
            self.end_headers()
            self.wfile.write(b'401 Unauthorized')
            return
        # ... 正常返回订阅内容
```

```bash
# 密码写入独立文件（600 权限）
echo -n "你的密码" > /etc/s-box/sub-key
chmod 600 /etc/s-box/sub-key
systemctl restart subscription-server.service

# 验证：无密码 401 / 错误密码 401 / 正确密码 200
curl -s -o /dev/null -w "%{http_code}" "http://域名:443/nx4hspzb"                 # 401
curl -s -o /dev/null -w "%{http_code}" "http://域名:443/nx4hspzb?key=wrong"       # 401
curl -s -o /dev/null -w "%{http_code}" "http://域名:443/nx4hspzb?key=正确密码"     # 200
```

用户订阅链接格式（带密码）：
```
http://google.cloud.eosphor.dpdns.org:443/nx4hspzb?key=<密码>
```

## 交付规则

- 用户要订阅链接时**只发链接本身**，不要附解释/对比/询问（Parker 偏好："直接发我链接，其他啥也不要打"）
