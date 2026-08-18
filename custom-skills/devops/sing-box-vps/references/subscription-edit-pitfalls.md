# 订阅文件编辑陷阱 & 最小改动原则（2026-08-18 事故复盘）

## 事故经过

用户要求：删除订阅规则里的 talktone 两条规则（仅此而已）。

助手的错误链：
1. 用 `sed -i '/talktone/d'` 删除了规则 ✅（这一步没问题）
2. 顺手运行了 `/root/.hermes/scripts/push-sub-to-github.py` 想"同步推送" ❌
3. 该脚本的 YAML 内容**硬编码了旧 UUID（2f319249-...）和旧规则（含 talktone）**
4. 脚本第二步会**覆盖本地 `/etc/s-box/custom-sub.yaml`** → 订阅文件变成旧 UUID
5. 客户端（Stash）刷新订阅拉到旧 UUID 节点，服务器（sb.json 里的新 UUID b1c9210e-...）不认 → 全部连不上
6. 用户报"订阅更新失败了"，随后发怒："你别他妈乱改，你悠悠ID别动"、"就他妈删除两行规则就行了"

## 核心教训

1. **push-sub-to-github.py 是坏脚本** —— 内容硬编码旧凭据，运行即覆盖本地订阅文件。
   **除非用户明确说"推送到 GitHub"，永远不要运行它。**
2. **最小改动原则** —— 用户要删两行就只删两行，不要顺手做任何"附加操作"。
   用户明确说过："就他妈删除两行规则就行了"。
3. **UUID/密钥是敏感字段** —— 未经用户明确指示，一律不动。改订阅文件前先确认 sb.json 里的真实值。
4. **sb.json 是权威** —— 订阅文件（custom-sub.yaml）的 UUID/密码必须与 sb.json 一致，客户端才能连上。
5. **改配置前先查知识库** —— 用户要求改任何配置前先搜索本地知识库
   `/home/projects/hermes-knowledge/`（尤其 `环境配置/代理订阅配置.md`），不要凭 memory 里的模糊印象动手。

## 正确流程（最小改动）

```bash
# 0. 先读知识库确认事实
#    /home/projects/hermes-knowledge/环境配置/代理订阅配置.md

# 1. 只删目标行
sed -i '/talktone/d' /etc/s-box/custom-sub.yaml

# 2. 验证订阅输出（UUID 应与 sb.json 一致、规则正确）
curl -s http://127.0.0.1:443/ | grep -oE "[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}" | sort -u
curl -s http://127.0.0.1:443/ | grep -A5 "^rules:"

# 3. 确认 talktone 已消失
curl -s http://127.0.0.1:443/ | grep -c talktone   # 期望 0

# 4. 告诉用户刷新订阅
```

## 订阅服务路径行为（443 版本）

`subscription-server.py`（443 端口）**不检查请求路径**：
- `http://域名:443/` ✅ 返回订阅（用户一直这么用）
- `http://域名:443/nx4hspzb` ✅ 也返回订阅（路径只是摆设）
- 不要告诉用户"必须带后缀"，无后缀地址一直有效

## 相关文件

| 文件 | 角色 |
|------|------|
| `/etc/s-box/sb.json` | sing-box 真实配置（**权威**，UUID/密码以此为准） |
| `/etc/s-box/custom-sub.yaml` | Clash 订阅（给客户端，必须与 sb.json 一致） |
| `/root/.hermes/scripts/push-sub-to-github.py` | ⛔ 硬编码旧配置，运行会覆盖本地订阅文件 |
| `/root/.hermes/scripts/subscription-server.py` | 443 订阅 HTTP 服务（不检查路径） |
