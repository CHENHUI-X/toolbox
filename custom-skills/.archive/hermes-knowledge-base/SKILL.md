---
name: hermes-knowledge-base
description: "Manage a categorized personal knowledge base at /home/projects/hermes-knowledge/ for storing user credentials, environment configs, habits/rules, and memory archives. Four folders, git-backed."
version: 1.0.0
author: Hermes Agent
tags: [knowledge-base, memory-archive, credentials, config-backup, user-preferences]
---

# Hermes Knowledge Base — 知识库管理

用户的知识库在 `/home/projects/hermes-knowledge/`，用于分类存储长久信息。

## 目录结构

```
📁 账号密码/      → 账户、API Key、Token 等敏感信息
📁 环境配置/      → 服务器 IP、端口、网络拓扑、软件版本
📁 习惯规则/      → 用户的个人习惯、偏好、沟通规则
📁 记忆归档/      → 从 Hermes memory 归档的旧记忆（非删除）
```

## 使用场景

### 场景 1：用户发来账号/密码/Token

用户说"这是我的 xxx 的 API Key" → 写入 `账号密码/` 下的 `.md` 文件。

```bash
# 写入格式示例
cat >> /home/projects/hermes-knowledge/账号密码/cloud-provider-keys.md << 'EOF'
## xx云 API
- Key: sk-xxx
- 注册邮箱: xxx@example.com
- 备注: 2026-05 注册
EOF
```

标注时间和备注，方便日后查找。

### 场景 2：用户告诉我服务器配置

IP 变更、端口映射、服务路径 → 写入 `环境配置/`。

### 场景 3：用户纠正我的行为

"不要这样做"、"以后要那样" → 写入 `习惯规则/`。每条规则用一个条目，标注日期。

```markdown
## 2026-05-27
- 通知格式：只发 release note，不要 git log --oneline
- 服务器状态：问的时候才发，不要定时推送
```

### 场景 4：Memory 快满 → 归档到知识库

当 memory 使用接近 2200 chars 上限时：

1. 选择「已经不太需要每轮看到」的旧记忆
2. 写入 `/home/projects/hermes-knowledge/记忆归档/` 下的 `.md` 文件
3. 每条归档标注标签和日期
4. 用 `memory(action='remove')` 删除对应的 memory 条目，释放空间

```bash
# 归档格式示例
cat > /home/projects/hermes-knowledge/记忆归档/2026-05-27_hermes_memory_archive.md << 'EOF'
# 记忆归档 — 2026-05-27

## 两地架构隧道细节 [标签: network, tunnel, gcp-wsl]
归档理由：已稳定运行，无需每轮加载
内容：WSL↔GCP 双向隧道，webhook secret，端口映射...

## 旧日志信息 [标签: debug, old]
归档理由：问题已解决
内容：...
EOF
```

### 场景 5：用户问"我的 xxx 是什么？"

直接去对应分类文件夹下 `grep` 或 `search_files` 查找，不要问用户"你之前说过的xxx是什么"。

## 用户偏好

- ✅ 所有信息分类存储，不乱放
- ✅ 记忆不直接删除，先归档再清理
- ✅ 敏感信息标时间戳和备注
- ❌ 不要用 memory 存大量具体数据（密码、配置细节）
- ❌ 不要问用户"这个东西放哪里" — 根据内容自己判断分类

## Pitfalls

- 知识库不是 Hermes memory 的替代品，而是 overflow 存储。活跃信息放 memory，冷数据归档到知识库
- 写文件时注意不要覆盖已有内容 — 用 `>>` 追加或 patch 现有文件
- 账号密码类的文件不要 commit 到公开的 Git 仓库 — 本知识库目前没有 Git 管理，保持纯文件即可
- 归档记忆后记得用 `memory(action='remove')` 清理 memory 中的对应条目
