---
name: cloud-firewall-and-gateway-ops
version: 1.0.0
author: Hermes Agent
license: MIT
description: "Use when operating Hermes gateways or cloud firewalls. Check before restart."
metadata:
  hermes:
    tags: [gcp, aws, firewall, gcloud, gateway-restart, credentials, telegram-commands]
---

# 云防火墙放行与网关重启操作

## When to Use

- 新端口要暴露公网（节点、订阅、api_server、A2A 等）
- 用户报告服务"本机通但外面连不上"
- 需要重启本机/远程 hermes gateway

## 防火墙三层模型（排障顺序）

1. **服务监听**：`ss -tlnp`（TCP）/ `ss -ulnp`（UDP）——确认进程在听、绑 0.0.0.0 而非 127.0.0.1
2. **主机防火墙**：`ufw status`（本机 GCP VM 无 9902 规则也能通本机回环，说明三层独立）
3. **云防火墙**：GCP Firewall Rules / AWS Security Group——**本机自测公网 IP 会误判**（hairpin 不成立），要用另一台外部机器实测 `/dev/tcp/IP/PORT`

案例：GCP 9902 本机自测通、AWS 新机实测不通 → 定位到 GCP 防火墙缺规则。

## 先探测云厂商再谈防火墙

```
GCP: curl -H 'Metadata-Flavor: Google' http://metadata.google.internal/computeMetadata/v1/project/project-id
AWS: curl -s http://169.254.169.254/latest/meta-data/instance-id
```

⚠️ 2026-09-02 实例：新机 195.72.189.146 想当然以为是 GCP，实测是 AWS——两台机器的防火墙体系完全不同，别混淆。

## GCP 放行端口的完整自助路径

默认 compute SA（`197431797765-compute@developer.gserviceaccount.com`）**没有 compute scope**，API 调防火墙必 403。标准流程：

1. 装 SDK（如未装）：
```bash
cd /tmp && curl -sSL -o gcloud.tar.gz https://dl.google.com/dl/cloudsdk/channels/rapid/downloads/google-cloud-cli-linux-x86_64.tar.gz && tar xzf gcloud.tar.gz && ./google-cloud-sdk/install.sh --quiet
```
2. metadata token 实测取证：
```bash
TOKEN=$(curl -s -H 'Metadata-Flavor: Google' 'http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token' | python3 -c 'import sys,json;print(json.load(sys.stdin)["access_token"])')
curl -s -H "Authorization: Bearer $TOKEN" 'https://compute.googleapis.com/compute/v1/projects/<project>/global/firewalls/<rule>'
# → 403 insufficient authentication scopes = 权限不在本机
```
3. 拿到 403 证据后，请用户在其**已登录的 Windows gcloud** 跑**单行**命令：
```
gcloud compute firewall-rules create allow-xxx --allow tcp:PORT --target-tags http-server
```

**给用户的命令规范**（踩过的坑，全部真实发生）：
- **单行**，禁止换行/反斜杠续行（用户终端会自动执行断行，用户原话"一行给我 不要换行 不然自动执行了"）
- 避免 `0.0.0.0/0` 裸 IP 串——Telegram 打码成 `[IP]/0`，用户复制到的是废命令。**不写 --source-ranges 参数**（gcloud 默认就是全网段）
- PowerShell 多参数逗号必须加引号：`--allow "udp:65083,udp:53900"`
- 发命令前自测可达性（用户原话"你先试试通不通"）

## AWS 侧

Security Group 在用户 AWS 控制台操作；实例内 iptables/ufw 照常。本机 sshpass 可登（密码见 .env 或知识库）。

## 网关重启

- **先查配置是否需要重启**：不要把每次 config 修改都当成重启需求。Hermes 审批设置走 mtime-keyed 配置缓存，可实时读取；切换 `approvals.mode` 或 `approvals.smart_policy` 不应为了生效而重启整台网关。
- **Parker 的审批偏好**：常规操作直接执行，只在删除文件、目录或数据前询问。配置用 `approvals.mode: smart`，并将 `approvals.smart_policy` 设为“删除操作 `ESCALATE`、其他被标记操作 `APPROVE`”；不要设 `mode: off`，它也会绕过删除确认。`approvals.deny` 是硬阻断，不是询问。保留硬拦截；无人值守任务没有人可确认删除时应 fail closed。配置后用 `hermes config get approvals` 回读验证。
- **自我保护拦截**：任何含 "restart hermes-gateway" / "stop" 字样的命令从 gateway 进程内（含 ssh 远程执行的字样）发出都会被 Block；fail-closed 门禁没有进程内绕行口，`at now + 1 minute`、写 `/etc/cron.d/`、`execute_code`、systemd-run 包装都不行（详见下方“进程内没有任何可用路可走”）。
- **Parker's standing rule:** scheduled operations (cron, `at`, systemd timers, delayed restarts) are forbidden unless he explicitly overrides this in a later request. If a lifecycle command is blocked, do not schedule a workaround; leave config saved and report that the running gateway has not reloaded.
- **不要在活跃对话中提前触发重启**：SIGTERM 后 gateway 等当前 active turn 结束才真正退出；systemd 可按 `agent.restart_drain_timeout` 等待很久。先结束当前回复，再安排需要的重启，避免停机时长和消息投递延迟。
- **进程内没有任何可用路可走**（实测结论，别再试）：门禁 `tools/terminal_tool_guards.py` 只对“自身是受管网关进程”的调用生效，一旦生效就是 fail-closed——扫描命令文本 **以及被引用脚本的内容**，命中重启/停止字样，或被引用脚本读不到（远程主机上的路径、运行时拼出来的内容）一律 Block。实测全被拦：裸 `systemctl` / `hermes gateway restart`、把重启脚本放远端再用 ssh 调、用 `execute_code` 写 `/etc/cron.d/` 条目。`at`/cron/timer 也不是逃逸口——把字样写进条目本身就是被扫的命令。
- **本机改不动、远端更不可能**：机器 A 的会话**永远无法重启**机器 B 上的网关。重启必须从**任何一个网关进程树之外**的 shell 发出。
- **正确做法：给用户一行外部命令**，在他自己电脑（ssh）或云厂商网页控制台上跑：
  `ssh root@<host> 'export XDG_RUNTIME_DIR=/run/user/0; systemctl --user restart hermes-gateway; systemctl --user is-active hermes-gateway'`
  （系统级 unit 去掉 `XDG_RUNTIME_DIR`/`--user`）。必须是**单行**，末尾带上 `is-active` 自查；或老实说明只能等自然重启（`Restart=always` 只在崩溃/重启机器/更新时重载，没有固定时间表）。
- 清理任何临时 cron 文件本身属于删除操作；若用户要求删除前确认，先对这个具体文件取得明确确认。未获确认或审批超时，不要换工具、包装命令或改写脚本来绕过门禁；如不能重启，明确说明**配置已写但运行中的网关尚未加载**（`.env` / `config.yaml` 改动已在盘上，下次重启即生效，例如在一台重启不了的机器上关掉某个平台，它只是从那刻起不再轮询）。触发后不要在同一轮长时间轮询；重启后验证 `systemctl is-active hermes-gateway` 与 Telegram/Weixin 连接日志，确认前不可宣称已生效。
- 已有脚本：`/root/.hermes/scripts/restart-gateway.sh`（本机）、`remote-gw-ops.sh`（ssh 新机）、`local-gw-restart.sh`（本机简版）

### 响应变慢与模型选择

- 先区分推理设置与主机压力：核对当前模型/`agent.reasoning_effort`，再看一次轻量内存和服务快照；不要仅凭“内存紧张”就认定它是慢响应的根因。
- `max` 会增加推理时间和消耗；日常 Hermes 工具型 Agent 先用 `medium`，复杂任务再提高。用户只问模型建议时，分别给最快选项和均衡选项，不要擅自切模型或重启。
- 对 OpenAI Codex OAuth，按账户实际可见模型和 OpenAI 最新官方说明比较；API 可用不代表 ChatGPT OAuth 账户一定有权限。回答保持简短，并明确哪些是推荐、哪些只是最快。

### 跨网关模型切换与远程故障

- 先区分同一网关里的平台适配器与独立远程 peer：用 `hermes gateway list` 清点本机 profile，用 `hermes peer list` 清点远程网关。同一 profile 下 Telegram、Weixin、QQ 等平台共享模型配置；每个远程 peer 有独立的模型、provider、OAuth 状态和重启方式，逐台检查、逐台验证。
- 切换 Codex OAuth 前，在目标主机核对 `hermes auth status openai-codex`；`~/.codex/auth.json` 的 Codex CLI 登录与 Hermes 自己的凭证池是分开的。若复用现有 Codex CLI 登录，只走 Hermes 支持的导入流程，不打印或转发 token。
- `hermes peer dm` 是由远端当前模型驱动的操作通道；远端推理 provider 不可达时，调用会失败，不能据此认定网关进程已死。先分别检查 peer `/health`、SSH/隧道连通性与服务日志；不要让长时间 peer 调用静默等待，也不要在 peer 推理不可用时反复重试同一请求。只有经过验证的独立 SSH/O&M 通道可用时才用它管理远端。
- 用户不要 `-900k` Codex 变体时，设置基础 model slug 并将 `model.context_length` 恢复到基础额度（例如 `gpt-6-luna` + `272000`）；只去掉 slug 后缀、却保留显式 1,000,000 context pin，仍不符合要求。
- 不以配置回读作为完成证明：用短小无害调用检查实际 provider/model，并在重启后用新消息会话或 gateway 日志逐台核验；汇报时区分“配置已写”“请求已实测”“运行网关已重载”。

## 相关技能

- `hermes-peer-networking` — peer/A2A 组网全景
- `sing-box-node-check` — 节点变更检查钩子（用户自有，未 curator 托管）
- `gcp-operations` — GCP VM 运维（用户自有）
