# `hermes peer dm` 分层诊断

适用于双机 Hermes API 可达、但 `hermes peer dm` 超时或无回复的情况。目标是区分 VM/SSH 隧道、API/模型、持久会话和 agent turn；超时本身不等于进程死亡。

## 先确认 `peer dm` 实际调用路径

当前 Hermes CLI 实现（`hermes_cli/subcommands/peer.py`）中，`peer dm`：

1. 对 `/api/sessions?limit=200&title=Bot+Chat&include_hidden=1` 查找远端规范 Bot Chat；找不到时会尝试创建。
2. 对 `/api/sessions/<session_id>/chat` 发送同步 agent turn。
3. CLI 的 `DM_TIMEOUT_S` 是 600 秒。若用外层 `timeout 15/45` 杀掉本地命令，只能说明本地等待被截断，远端是否已取消不能由此判断。不要连续重发，避免重复入队或叠加会话工作。

代码升级后若需确认路由，先只读检查 `hermes_cli/subcommands/peer.py` 中 `_ensure_bot_chat`、`DM_TIMEOUT_S` 和 `cmd_peer`，不要假设端点永远不变。

## 由轻到重的只读检查

1. **传输/隧道**：在隧道终点检查转发监听和已建立 SSH 连接：
   ```bash
   ss -lntp '( sport = :9902 )'
   ss -tnp state established
   ```
   `systemctl is-active a2a-tunnel.service` 不是唯一证据：unit 名称可能不存在/不同，但实际 SSHD 转发会话仍在。反过来，只有本地监听而没有有效转发也不能证明远端 API可用。最后以对目标 HTTP 端点的请求为准。

2. **基础 API**：分别请求 `/health` 和带 peer API key 的 `/v1/models`，记录状态码/耗时，不打印 key。二者成功说明基础 API 有响应，不代表 agent 会话可用。

3. **模型通路（可选，可能产生一次极小模型调用）**：可用一个 `max_tokens` 很小的 `/v1/chat/completions` 请求确认模型通路。它不加载 Bot Chat 历史，也不执行 Hermes 工具；成功只能排除“模型 API 完全不可用”，**不是 `peer dm` 的端到端验证**。

4. **会话 API**：用有鉴权的只读 `GET /api/sessions?limit=1` 或精确 Bot Chat 查询，设置 5–15 秒超时并记录耗时。若这一步卡住而 `/health`、`/v1/models` 正常，故障已收敛到 session/API 数据路径；若 GET 正常但 `peer dm` 卡住，重点查 agent turn、工具执行及远端网关日志。

5. **取证后再动手**：读取远端 `journalctl -u hermes-gateway`、gateway/error log、相关 session 错误；通过受授权 SSH 取证。不要因一次 `peer dm` 超时就重启 GCP gateway/VM，尤其当存在 Python venv 损坏的历史风险时。

## 结论口径

- `health/models/chat` 成功、`/api/sessions` 超时：报“基础 API/模型仍响应，持久会话路径超时；根因需远端日志确认”，不要报“GCP agent 已死”。
- `health` 超时但 SSH 隧道仍建立：报“远端 API 当前无响应，VM/agent 是否存活尚不能由此判定”。
- `peer dm` 收到明确 HTTP 500/错误正文时，以真实错误为准；不要把已知历史错误自动套到本次。
- 面向用户先给结论，再列一两条证据和明确未知项；不要复述整段排查过程。
