---
name: knowledge-base-management
description: "Set up and maintain a categorized knowledge base for a user — archive old memory, store credentials/configs/habits, and enforce lookup-first rules"
version: 1.0.0
author: Hermes Agent
tags: [knowledge-base, memory-archive, knowledge-management, user-preferences, file-organization]
---

# Knowledge Base Management

Use this skill when the user asks to:
- Create a knowledge base / 知识库 / 归档系统
- Archive old memory entries instead of deleting them
- Store credentials, configs, habits, or rules persistently
- Set rules about knowledge lookup behavior

## Core Pattern

The knowledge base is a **directory tree of markdown files under `/home/projects/`**, organized by category, backed by git. Each file captures a topic that would otherwise live in the agent's limited-context memory.

### Directory structure

```
/home/projects/hermes-knowledge/
├── 📁 账号密码/          # 账户、Token、密钥等敏感信息
├── 📁 环境配置/          # 服务器配置、网络拓扑、软件信息
├── 📁 习惯规则/          # 用户的个人偏好、习惯、行为规则
├── 📁 记忆归档/          # 从 Hermes memory 归档的旧记忆（按日期）
│   └── 2026-05-27-首次归档.md
└── README.md
```

### Initialization

```bash
mkdir -p /home/projects/hermes-knowledge/{账号密码,环境配置,习惯规则,记忆归档}
cat > /home/projects/hermes-knowledge/README.md << 'EOF'
# Hermes 知识库
...
EOF
```

## The Two Iron Rules（两条铁律 — 不得删除）

These must be recorded in the agent's **memory** as permanent entries (not just a skill note), so they're injected every turn:

| # | Rule | key-phrase |
|---|------|------------|
| 1 | **Memory full → Archive, never delete** — When the agent's memory system approaches capacity (~2200 chars), move useful old entries to `/home/projects/hermes-knowledge/记忆归档/` as .md files with date tags. Never `memory(action='remove')` without first archiving the content. | `【铁律1-不能删除】` |
| 2 | **Knowledge base first** — When the user asks a question and the agent has no relevant information in memory, search the knowledge base (all subdirectories) before asking the user to repeat themselves. The original files stay in place after reading. | `【铁律2-不能删除】` |

### Memory entry format

```
【铁律1-不能删除】memory 快满时，把有用的旧记忆归档到知识库
  /home/projects/hermes-knowledge/记忆归档/，标注标签和日期，绝不能直接删除。

【铁律2-不能删除】当用户问的问题我的 memory 里没有相关信息时，
  必须优先去知识库 /home/projects/hermes-knowledge/ 的各分类文件夹中查找，
  拿到的信息用完后仍需保留在原处。
```

## Memory Archiving Procedure

### When to archive

- Memory usage hits **≥80%** (~1760 chars out of 2200)
- The agent notices old entries that are stale, superseded, or rarely relevant
- The user explicitly asks to "compress" or "归档" memory

### Archive format

Create a file at `/home/projects/hermes-knowledge/记忆归档/YYYY-MM-DD-描述.md`:

```markdown
# 记忆归档 — YYYY-MM-DD

> 以下记忆从 Hermes Agent 的 active memory 中归档至此，
> 信息完整保留，需要时可查阅。

## 归档条目

| 原内容概要 | 归档至 | 日期 |
|-----------|--------|------|
| Gateway systemd 部署详情、超时设置 | `环境配置/hermes-gateway-部署.md` | 2026-05-27 |
| 两地实例架构、隧道方向限制 | `环境配置/两地Hermes架构.md` | 2026-05-27 |
```

### Compression steps

1. Identify which memory entries to **keep** (active rules, unresolved issues, core preferences) vs **archive** (detailed configs, resolved issues, old IPs)
2. Write archive files to the appropriate knowledge base subdirectory
3. Write an index entry to `📁 记忆归档/`
4. Remove the old entries from memory via `memory(action='remove')`
5. Add concise replacement entries if needed (~1 line summaries)
6. Write updated rules (铁律1, 铁律2) as fresh entries

## Knowledge Base Lookup

When the user asks something and memory doesn't help:

1. Search all files under `/home/projects/hermes-knowledge/` using `search_files(pattern=..., path='/home/projects/hermes-knowledge/')`
2. Read relevant files with `read_file`
3. Synthesize the answer
4. Do NOT delete or move files after reading

## Categorization Rules

When the user shares new information, classify it:

| Info type → | Store in |
|-------------|----------|
| Account credentials, API keys, tokens, passwords | `📁 账号密码/` |
| Server setup, network topology, software configs | `📁 环境配置/` |
| User habits, preferences, "don't do X", style notes | `📁 习惯规则/` |
| Old memory that was compressed out of active memory | `📁 记忆归档/` |

### File naming convention

- Use Chinese: `描述性名称.md` (descriptive, not cryptic)
- For credentials: include the service/platform name, e.g., `webhook配置.md`
- For configs: include what it configures, e.g., `hermes-gateway-部署.md`
- For archives: `YYYY-MM-DD-描述.md`

## Concrete Implementation Example

This user's knowledge base lives at **`/home/projects/hermes-knowledge/`** with the exact structure above. It is **not** git-backed (plain files only — do not commit credential files to git).

### Usage Scenarios

**Scenario 1: User shares credentials (API key, token, password)**
→ Write to `📁 账号密码/` with timestamp and context:

```bash
cat >> /home/projects/hermes-knowledge/账号密码/cloud-provider-keys.md << 'EOF'
## xx云 API
- Key: sk-xxx
- 注册邮箱: xxx@example.com
- 备注: 2026-05 注册
EOF
```

**Scenario 2: User shares server configuration (IP, ports, topology)**
→ Write to `📁 环境配置/`.

**Scenario 3: User corrects your behavior ("don't do that", "next time do X")**
→ Write to `📁 习惯规则/` with each rule as a dated markdown entry:

```markdown
## 2026-05-27
- 通知格式：只发 release note，不要 git log --oneline
- 服务器状态：问的时候才发，不要定时推送
```

**Scenario 4: Memory approaching limit (~1760/2200 chars)**
→ Archive old entries to `📁 记忆归档/YYYY-MM-DD_描述.md` before removing from memory:

```bash
cat > /home/projects/hermes-knowledge/记忆归档/2026-05-27_hermes_memory_archive.md << 'EOF'
# 记忆归档 — 2026-05-27
## 两地架构隧道细节 [标签: network, tunnel, gcp-wsl]
归档理由：已稳定运行，无需每轮加载
内容：WSL↔GCP 双向隧道，webhook secret，端口映射...
EOF
```

Then `memory(action='remove')` the archived entries.

**Scenario 5: User asks "what's my X?" and memory has no relevant info**
→ Search all subdirectories of the knowledge base via `search_files` before asking the user to repeat themselves. Do NOT ask "where should I put this" — classify and file it yourself.

### User Preferences (this specific user)

- ✅ All info categorized, not scattered
- ✅ Memory entries archived before removal (never delete first)
- ✅ Sensitive info gets timestamps and context notes
- ❌ Do not store large amounts of specific data (passwords, config details) in memory — use the knowledge base
- ❌ Do not ask "where does this go" — classify based on content
- ✅ Response language: Chinese when the user communicates in Chinese
- ✅ Format: concise, practical, no unnecessary explanations

### Localization Note

This implementation uses Chinese directory names (`账号密码/`, `环境配置/`, `习惯规则/`, `记忆归档/`), mirroring the user's language. When setting up for a different user, use appropriate localized names.

## Pitfalls

- **Don't archive rules that are still active** — `【铁律】` entries and unresolved issues stay in memory
- **Don't delete old memory without archiving first** — always write the .md before removing the memory entry
- **Don't store plaintext passwords in memory** — memory is injected every turn, use the knowledge base file instead, and mention it's stored there
- **Don't use `rsync --delete`** for backup scripts near the knowledge base — it deletes non-script files like README.md
- **Don't over-archive** — leave enough context that you can answer common questions without file I/O every turn
- **Don't overwrite existing files** — use `>>` append or `patch` existing files, never `>` redirect that replaces content
