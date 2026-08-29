# UUID 凭据轮换 — 全文件清单（2026-08-29 实战）

**用户硬性要求："以后记住，一次性给我修改好"** — 轮换 UUID 时绝不分批，一次改完全部含旧凭据的文件，改完全局扫描确认 0 残留。

## 完整文件清单（按轮换优先级）

| 文件 | 角色 | 改动点 |
|------|------|--------|
| `/etc/s-box/sb.json` | sing-box 真实配置（权威） | vless/vmess/tuic 的 `uuid` + **vmess 的 `transport.path`**（路径嵌着旧 UUID，如 `/b1c9210e-...-vm`，最容易漏） |
| `/etc/s-box/custom-sub.yaml` | Clash/Stash 订阅文件 | 4 处 `uuid`（vless/vmess/tuic + 其他） |
| `/etc/s-box/clmi.yaml` | yonggekkk 生成 Clash 订阅 | uuid（可能用**更早一代** UUID，如 `2f319249-...`） |
| `/etc/s-box/jhsub.txt` | 合并订阅文本 | uuid |
| `/etc/s-box/jhdy.txt` | 订阅文本 | uuid |
| `/etc/s-box/tuic5.txt` | TUIC 分享链接 | uuid + password |
| `/etc/s-box/an.txt` | AnyTLS 分享链接 | password |
| `/etc/s-box/vl_reality.txt` | VLESS 分享链接 | uuid |
| `/etc/s-box/hy2.txt` | Hysteria2 分享链接 | password |
| `/etc/s-box/sbox.json` / `sb10.json` / `sb11.json` | 历史配置快照（无人引用） | 残留旧 UUID，一并替换保持干净 |
| 知识库 `/home/projects/hermes-knowledge/环境配置/代理订阅配置.md` | 运维文档 | UUID 记录 |
| toolbox 仓库技能文档（如 `custom-skills/devops/sing-box-vps/references/*.md`） | 文档 | UUID 记录 |

## 高效做法（实测）

1. **先找出所有含旧 UUID 的文件**（替代逐个猜）：
   ```bash
   grep -rlE "旧UUID1|旧UUID2" /etc/s-box/ /root/.hermes/scripts/ /home/projects/ 2>/dev/null | grep -v ".bak-"
   ```
2. **sb.json 用 Python 全量替换**（含 transport.path）：
   ```python
   import json
   raw = json.dumps(cfg, ensure_ascii=False)
   raw = raw.replace(old_uuid, new_uuid)   # 字符串级替换，覆盖 path 等嵌套字段
   cfg = json.loads(raw)
   ```
3. **其他文本文件逐个 replace**（先备份 `.bak-YYYYMMDD`）
4. **全局残留扫描**：
   ```bash
   grep -rlE "旧UUID1|旧UUID2" /etc/s-box/ --exclude=*.bak*
   # 应输出空
   ```

## 轮换后验证 + 交付

```bash
# 1. 重启 sing-box + 订阅服务
systemctl restart sing-box
systemctl restart subscription-server.service

# 2. 验证订阅输出
curl -s http://127.0.0.1:443/nx4hspzb | grep -c "新UUID"      # 应为 4+
curl -s http://127.0.0.1:443/nx4hspzb | grep -c "旧UUID"      # 应为 0

# 3. 验证 UDP 端口（hy2/tuic 是 UDP，用 ss -ulnp 不是 -tlnp）
ss -ulnp | grep -E "65083|53900"
```

**交付订阅链接给用户**（Stash 可直接用，三种都给）：
```
http://google.cloud.eosphor.dpdns.org:443           # 域名（推荐）
http://<公网IP>:443                                  # IP 直连
http://google.cloud.eosphor.dpdns.org:443/nx4hspzb  # 带路径
```

提示用户：客户端刷新订阅；手动配置过旧节点的删掉重加。

## 背景

- 蹭流复发（7 月被蹭 1100GB，8/29 又来 5.76GB/天，凌晨 13 个 IP 白嫖）→ 轮换 UUID 是唯一彻底手段
- 轮换后如果订阅链接本身已外泄（无密码+不检查路径），旧用户**重新拉订阅就能拿到新 UUID**——彻底封杀需换端口或加路径鉴权，见 SKILL.md「订阅服务器安全加固」
- 用户对改 UUID 敏感（此前"悠悠ID别动"），但**明确授权轮换后**就要一次做完，不要中途停下来问
