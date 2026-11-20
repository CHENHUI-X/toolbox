# Peer DM 模型/provider 路由取证

适用于 `hermes peer dm` 收到模型/provider HTTP 错误、但通道本身在线的场景。目标是准确回答失败方向、原命令、错误正文、接收端目标会话和当前状态；先取证，不凭错误字符串猜测。

## 证据链

1. **定位失败方向与原命令**
   - 分清发起端（执行 `hermes peer dm <peer> ...` 的主机）和接收端（peer API 所在主机）。例：GCP 的 `gcp2` 指向 QQG，因此 GCP 上 `hermes peer dm gcp2 ...` 是 GCP→QQG。
   - 在发起端 Hermes `state.db` 对应 agent session 的 `messages.tool_calls` 找完整终端命令，并紧跟着读取对应 `tool` 消息的输出/退出码。API 接收端通常没有调用者 shell argv；只有接收端日志时，不要编造原命令，应标明未记录。
   - 将调用方命令时间与接收端日志时间（注意时区）对齐；同一条消息内容和精确时间可用于关联。

2. **读取接收端目标会话**
   - 从接收端 `state.db` 只读查询 `sessions`：`id`, `title`, `source`, `model`, `model_config`, `billing_provider`, `billing_base_url`。
   - 同时查 `session_model_usage` 和 `messages` 时间戳；按目标 session ID 查 `errors.log` / `agent.log`，提取该请求当时实际的 `provider`, `base_url`, `model`, 原始 HTTP 状态/正文。
   - 错误正文中的 model/provider 是该次请求的运行时证据；不要用会话创建时的值或当前全局配置覆盖它。

3. **区分锁字段、历史汇总和实时路由**
   - 会话 `model_config` 中的锁（如 `browser_model_lock.provider/model/route_source`）表示当前锁定路由；缺字段/null 表示当前快照没有该信息。
   - 顶层 `sessions.billing_provider` 与 `session_model_usage` 是会话累计/历史归因，可能落后于后来会话级 model lock。它们不可单独证明本次请求的有效 provider。
   - 对当前有效路由，优先用同一请求时间的 `agent.turn_context`、`API call #... model=... provider=...` 日志；再与当前锁比较。没有失败时刻的 model_config 快照时，route_source 必须报“失败时未记录”，不能把当前 `raw_request` 倒推为历史值。

4. **判断“现在还失败吗”**
   - 把最后一次错误、会话锁更新时间、锁后第一条成功的实时调用按时间排序。明确将历史失败和当前失败分开。
   - 一条锁后成功的模型调用证明该次模型生成成功；若要断言 peer DM 整体闭环成功，还应看到发起端对应命令退出/收到回复。`/health` 200 或另一方向成功不能代替该证据。
   - 若本轮只读要求，不要重发 `peer dm`（会新增远端 agent turn），不要修改 session lock/全局 config，也不要重启。

## 汇报格式

先给结论（当前哪一方向仍失败；若未复现则直说），然后列：发起方向、发起端原命令及实际工具输出、接收端原始 HTTP 错误、接收端 session ID/title/source、失败时 model/provider/route_source（未知就标未知）、当前锁与锁后实时调用证据。简洁区分“从日志确认”“对端报告”和“推断”，不把推断写成准确命令。

## 常见根因模式

如果对端 session 保留了旧 model，但实际请求由另一个 provider 执行，会出现 session model/provider 不兼容的 400。修复若已获授权，应只修目标会话路由；不要因此切换两端全局 provider，也不要让一个 provider 执行不支持的模型。修复后验证目标会话的实时 `turn_context` 和实际 API-call model/provider，并确认发送端 peer 命令拿到回复。

## 对端回复已到达，但助手未纳入判断（2026-10-02）

本次 QQG↔GCP 排障中，GCP Agent 的说明已到达当前对话，且助手曾复述其关键值（Bot Chat: `glm-5.3-flash`、provider `custom`、base URL `cf.api.fan`）；之后助手仍错误地说“需要先和 GCP 协调”并重复旧状态。由此可确认本次不是 A2A 消息投递失败，而是助手的状态/上下文管理失败：已收到并确认的信息没有覆盖旧的“待协调”状态。是否由上下文压缩或摘要陈旧触发，证据不足，不能当成确定的内部根因。

防复发：
1. GCP 回复到达后立即将“协调状态”标为已完成，保存回复提供的事实、出处和时间；独立记录“根因已知/未知”及“修复已验证/未验证”。
2. 在回答“好了没”或再次要求协调前，先检查当前轮及紧邻历史的 GCP 回复和助手既有确认；已收到时不得让用户重新转达，不得再说“需要先协调”。
3. 上下文压缩后若摘要与较新对话冲突，按时间核对会话历史，采用较新的原始回复；不能只复读摘要中的旧待办状态。
4. 沟通成功不等于修复成功：准确说“GCP 已回复，配置事实为……；修复是否完成/端到端验证……”，不得混成一个结论。
