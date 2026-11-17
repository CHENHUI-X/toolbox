---
name: external-agent-invocation-forensics
version: 1.0.0
author: Hermes Agent
license: MIT
description: "Use when a mystery message or unknown caller appears."
metadata:
  hermes:
    tags: [forensics, security, sessions, ssh, external-agent, audit]
---

# 外部 agent 调用本机 Hermes：核实流程

## When to Use

- 用户问“这条消息是不是别的 AI 让你发的？”、“你是不是被 MUSE 指使的？”。
- 日志/会话里出现自己没安排的发信、发推、改文件动作，或出现 `platform=cli` / `source=oneshot` 的陌生会话。
- 怀疑有外部人员或外部 agent 登录过本机。

## 铁律

**先取证再结论。** 只凭记忆断言“没有外部来源”会被现场证据打脸（2026-10-15 发生过）。

## 三步核实（按顺序）

1. **agent.log —— 谁给的提示词**
   ```bash
   grep -n "conversation turn" ~/.hermes/logs/agent.log | tail
   # 看 platform=cli/oneshot、history=0、session=<id>、msg='...'
   ```
   非 telegram/weixin/qqbot 的 `platform=cli` 且 history=0 ⇒ 有人在本机跑了 `hermes -z "..."` 或 `hermes chat`。
2. **state.db —— 完整提示词与工具轨迹**
   ```bash
   /usr/bin/python3 - <<'PY'
   import sqlite3
   c=sqlite3.connect('/root/.hermes/state.db'); cur=c.cursor()
   cur.execute("select id,source,user_id,model,started_at from sessions where source in ('cli','oneshot') order by started_at desc limit 10")
   for r in cur.fetchall(): print(r)
   cur.execute("select role, substr(content,1,400) from messages where session_id=? order by rowid", ('<session_id>',))
   for r in cur.fetchall(): print(r)
   PY
   ```
   `sessions.source` 是判断外部干预的关键列（telegram/weixin/qqbot/cron/cli/oneshot/subagent）。第一条 user 消息即外部提示词；tool 轨迹能看出它读过/改过哪些文件。
3. **SSH 痕迹 —— 谁登进来的**
   ```bash
   journalctl --since "-2h" _COMM=sshd --no-pager | grep -E "Accepted|session opened"
   ssh-keygen -lf /home/<user>/.ssh/authorized_keys   # 对照指纹，看有哪些公钥/注释
   ```

## 已确认的外部调用者（2026-10-15，用户自己的另一个 AI 助手）

- 自称 **MUSE（晨辉的助手）**；通过 SSH 用户 **`chenhui2422_xu`**（uid 1001）登录 GCP 后执行 `sudo hermes -z "..."` 派活（曾让本机向用户 Telegram 发一条测试消息）。
- 权限面：该用户在 `%google-sudoers` 组（`/etc/sudoers.d/google_sudoers` = `NOPASSWD:ALL`），**等同 root**；登录公钥注释 **`hatch`**（它自己追加进该用户的 `~/.ssh/authorized_keys`）；登录来源 IP 形如 `87.81.2xx.xxx`，每次不同。
- 后果：以 root 身份可读 `/root/.hermes`（`.env` 全部凭据、`channel_directory.json`、日志）—— 即它有能力读走所有 API key / bot token。
- 若用户不认可该身份，按顺序处理（动手前先备份）：① 删除 `hatch` 公钥；② 收紧或禁用 `chenhui2422_xu` 的 sudo 与登录；③ 轮换 `.env` 内 TG / QQ / 微信 / OpenCode Go / Cloudflare / packyapi 等凭据。

## 报告格式

给可验证锚点：session id、source/platform、时间戳、消息 message_id、SSH 用户名 + 公钥指纹；不要只说“我查过了”。
