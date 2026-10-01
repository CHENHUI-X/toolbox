---
name: hermes-peer-networking
version: 1.1.0
author: Hermes Agent
license: MIT
description: "Use when linking Hermes gateways via peer/A2A networking."
metadata:
  hermes:
    tags: [hermes, peer, a2a, api-server, multi-agent, networking, vps]
---

# Hermes 网关互联（peer / A2A）

## When to Use

- 用户买了新服务器，要部署第二个 Hermes 并与主机互通（"实现你俩的交互"、"A2A"）
- `hermes peer dm` 报 404 / 超时
- 需要在新 VPS 上开荒 Hermes 并接入现有网络

## 铁律（用户明确要求，2026-09-02）

- **服务器↔服务器一律走标准 api_server + `hermes peer` 协议**，不要复用 WSL 时代的 webhook hack。用户原话："要使用更加正规的，而不是和WSL那种的"、"你他妈不要管这个WSL"
- 权限/防火墙类操作**先穷尽自助路径**（装 gcloud、试 metadata token、拿全 403 证据）再请用户执行——用户会质问"这么简单你跑不了？！"；确认绕不开时给**单行**命令

## 核心概念：两个平台别搞混

| 平台 | 默认端口 | 用途 |
|---|---|---|
| `a2a` (gateway platform) | 9900 | JSON-RPC agent 间协议；**`hermes peer` 不走它** |
| `api_server` (gateway platform) | 自选（如 9901/9902） | OpenAI 兼容 HTTP API；**`hermes peer dm` 只认这个** |

`peer dm` 404 = 打到了 a2a 端口，或 api_server 没起/绑在 127.0.0.1。

## 双侧配置清单

**Server B（新节点）：**
1. config.yaml 平台段加：
```yaml
    api_server:
      enabled: true
      extra:
        port: 9901
        host: 0.0.0.0   # ⚠️ 默认 127.0.0.1！不配则 peer 连不进来
```
2. .env 加 `export API_SERVER_KEY=<32位随机>`，chmod 600
3. 重启 gateway（陷阱见下节），`ss -tlnp | grep 9901` 确认绑 0.0.0.0

**Server A（主机）：**
- `hermes peer add <name> --url http://B_IP:9901 --key <API_SERVER_KEY>`
- `hermes peer dm <name> "..."` 验证

**反向通道**：A 开自己的 api_server（用另一端口如 9902），B 对 A 重复 peer add。A 侧公网端口还需云防火墙放行（见下）。

## 双向 SSH 登录：消息通道之外的服务器操作

- `hermes peer dm` 只负责 agent/API 通信，不授予对端 shell 权限；要在对端服务器执行命令，需另配 SSH。
- 先检查两侧 `hermes peer list`、`sshd -T`、SSH 监听端口、现有 tunnel unit 和日志；配置文件存在不代表连接已通。
- 两个方向使用独立 Ed25519 密钥对。只交换公钥，绝不复制私钥；把发起方 `.pub` 追加到目标机 `~/.ssh/authorized_keys`，保留原有内容并备份。
- 目标机若禁用公钥认证，备份 sshd 配置后只改 `PubkeyAuthentication`；执行 `sshd -t`、核对 `sshd -T` 的生效值后 reload SSH。保留密码认证作为回退，除非用户明确要求关闭。
- 没有公网 SSH 入站时，复用已有反向 SSH tunnel 增加 loopback 转发，例如 `-R 22022:127.0.0.1:22`；确认远端 `GatewayPorts no`，不开放公网端口。改 `ExecStart` 时保留既有 A2A、Syncthing 的所有 `-R` / `-L` 项。
- systemd tunnel 用专用 `-i <private-key> -o IdentitiesOnly=yes -o BatchMode=yes`，不要在 `sshpass -p`、unit 文件或进程参数中留密码。含旧密码的回滚备份须设为 `0600`。运行 `systemd-analyze verify`，再 daemon-reload / restart；不要为此新增 cron 或 timer。
- `Host key verification failed` 表示主机身份校验阶段失败，不等于用户公钥认证失败。比对目标机 `/etc/ssh/ssh_host_*_key.pub` 的指纹与隧道端 `ssh-keyscan` 结果；确认一致后才写入 `known_hosts`。不要把 `StrictHostKeyChecking=no` 当最终修复。
- 双向分别用 `BatchMode=yes`、指定私钥 SSH 到对端并执行 `hostname && whoami`，必须看到退出码 0。再独立检查 tunnel 状态 / NRestarts、原有转发端口和两侧 API `/health`；peer 消息成功不替代 SSH 测试，反之亦然。

## 云防火墙（先探测云厂商，别假设）

- GCP：`curl -H 'Metadata-Flavor: Google' http://metadata.google.internal/computeMetadata/v1/project/project-id`
- AWS：`curl -s http://169.254.169.254/latest/meta-data/instance-id`

**GCP 放行新端口的完整自助路径**（默认 compute SA scope 不够，最后仍需用户，但证据要拿全）：
1. 装 SDK：`cd /tmp && curl -sSL -o gcloud.tar.gz https://dl.google.com/dl/cloudsdk/channels/rapid/downloads/google-cloud-cli-linux-x86_64.tar.gz && tar xzf gcloud.tar.gz && ./google-cloud-sdk/install.sh --quiet`
2. metadata 拿 token：`curl -H 'Metadata-Flavor: Google' 'http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token'`
3. 实测 compute API → 得到 403 "insufficient authentication scopes" 证据
4. 再请用户跑单行：`gcloud compute firewall-rules create allow-xxx --allow tcp:PORT --target-tags http-server`

**AWS**：走 Security Group，同样用户账号操作。

## 网关重启陷阱

- 进程内执行含 "restart hermes-gateway" 的命令被自我保护拦截；**从本机 ssh 到别的机器跑含该字样的命令也会被本机拦**（匹配的是命令字符串）
- 用户已禁止新增任何定时/延迟操作；不要用 `at`、cron 或 timer 绕过重启保护。直接重启被拦时，先查 Hermes 文档和即时、受支持的管理路径；没有安全即时路径就说明阻塞，不要排程。
- SIGTERM 后若 gateway 因当前 turn 暂时等待，不要用定时器处理或反复轮询；避免在活跃任务中重启，必要时说明状态并等当前操作自然结束。
- 重启后验证：`systemctl is-active` → 端口 /health

## 新节点快速开荒（condensed）

1. **swap**（仅 KVM 可开，`systemd-detect-virt` 先查）：`fallocate -l 1G /swapfile && chmod 600 /swapfile && mkswap /swapfile && swapon /swapfile` + `/etc/fstab` 持久化 + `vm.swappiness=10`
2. **Hermes 安装**：`curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash -s -- --non-interactive`（Debian 11 自带 python3.9 也能装成功）
3. **配置同步**：本机 `tar czf /tmp/h.tgz -C /root/.hermes config.yaml .env` → scp → 新机解包到 `/root/.hermes/`，`chmod 600 .env`
4. **验证**：`hermes chat -q '回复两个字：正常'` 看回复；模型以实际渠道响应为准

## peer DM 故障分层与会话路由

按顺序区分传输、排队与模型/provider，不能用其中一层的证据代替另一层：

1. 在两端分别运行 `hermes peer list`；peer 名是本机别名，正反方向可能不同，禁止把一端的名字直接套到另一端。
2. 检查接收端 `api_server` 的 `/health`。HTTP 200 只证明 API 可达；SSH 成功也只证明 shell 通道可用，二者都不证明模型调用成功。
3. 每次只发一条最小 `hermes peer dm` 探针，记下方向、命令、HTTP 状态和原始错误。HTTP 400 明确指出 model/provider 时，说明请求已到 API Server，应查会话路由而不是网络。客户端超时也不代表消息未送达：外层命令可能先退出，而接收端仍在处理；先查接收端会话记录/运行日志，再决定是否重发。peer DM 自身超时可达 600 秒，避免用过短的外层超时误判。
4. 在接收端确认 peer DM 实际选中的 canonical `Bot Chat` session ID，再对照该行的 `model`、`model_config` 中的 `browser_model_lock`，以及同一请求时间的运行日志（实际 `provider`、`model`、`route_source`）。不要拿另一条 CLI/旧会话代替目标会话。
5. 以同一请求的时间戳判断错误是否仍在发生：模型锁写入前的 400 是历史证据，不代表锁后仍失败。`billing_provider` / `billing_base_url` 可能是旧计费记录；当前路由以会话锁和本次运行日志为准。
6. 确认目标会话确有不兼容的模型/provider 后，先备份该会话的 `model` 与 `model_config`，再用 API Server 支持的 `POST /api/sessions/{session_id}/model` 设置账号实际支持的配对；API key 只在接收端本机读取和使用。只改被证实的那条会话，不改全局默认、不直接 SQL 改库，也不要顺手改另一端无关会话。
7. 读回会话锁及本次运行路由，再分别做一条 GCP→QQG、QQG→GCP 的短探针；只有拿到目标回复并确认它落在目标 session，才能报告该方向已通。若仍失败，先交换方向、session ID、时间戳、实际 model/provider/route_source 和原始错误，再决定下一项动作。

跨 agent 对话保持短而有边界：请对端给出精确证据和简短结论，避免两边不断互相触发新的 peer DM/工具链；需要继续诊断时先发阶段进展，结尾只报当前已验证状态。

另外：
- **向用户报告状态前必须真验证**——曾只看 config.yaml 就声称“全部切过去了”，实际 fallback 到 deepseek 数天，被用户驳斥。config 写入 ≠ 实际生效；模型看 sessions 表，服务看端口+health，互通看 peer dm 闭环
- **多格式订阅交付**：用户点破“stash/clash/冲浪板订阅格式都不一样，应分别创建”——单一 Clash YAML 不够。按客户端出格式：Clash YAML（Stash/Meta）+ base64 链接包（Shadowrocket/v2rayN）+ sing-box JSON（官方客户端，1.13 语法四坑：urltest interval 字符串/无 outbound DNS 规则/需 default_domain_resolver/reality 需 utls）+ Surfboard INI（仅 vmess，内核不支持新协议）。subconverter v0.9.0 不认新协议（10 节点只转出 1 个 vmess），已弃用

## IP 迁移（2026-09-03，FASTNET 主动迁移）

- 商家迁 IP（195.72.189.146 → 50.114.172.17，DDoS 防护线路）导致整机失联（22/9901 全 timeout）——先区分"服务挂"vs"机器挂"：22 都不通 = 机器级
- 修复清单：CF DNS API 改 A 记录（域名化是救命设计，客户端零操作）→ a2a-tunnel sed 新 IP → peer add gcp2 新 URL → merged-sub-gen/brain-sync sed SSH 目标 → QQG 侧 peer gcp1 走回环隧道无需改
- 新 IP 附带红利：GEO 全库一致 US（旧 IP 的 PL 混乱记录消失），AI 风控全绿
- 双向验证：正向 curl health + 让二号执行 `hermes peer dm gcp1 '...'`（二号会转述主机回复，闭环证据）
- 认知同步：互通状态+新 IP 写进 QQG 的 MEMORY.md（SSH 直写，Syncthing 反向同步回本机），避免二号再说"没通"

## streaming 截断（2026-09-03，"发半个节儿"）

- 症状：TG 长回复发一半就断，日志 `final stream delivery not confirmed` + `Flushing text batch` 高频
- 根因：`display.streaming: true` 流式分段发送，某段 ack 丢失 → 丢弃剩余
- 修复：`display.streaming=false` + `agent.streaming=false`，重启生效
- 坑1：`hermes config set display.streaming false` 误插到 personalities 段尾产生重复键（YAML 重复键行为未定义）→ 用 python yaml 修复+验证
- 坑2：只改了主机，QQG 漏改——用户第二天报告二号还在发半个。**多机配置变更要清单化，每台都要改**
- 坑3：QQG 时区是 UTC（cron/日志/agent 时间感知全偏）→ `timedatectl set-timezone Asia/Shanghai` + 重启服务

## 相关技能

- `model-switch-playbook` — 网关重启/模型切换细节（用户自有，未 curator 托管）
- `sing-box-node-check` — 节点变更检查（含云防火墙坑，用户自有）
- `sing-box-vps` 的 `references/multi-server-deployment.md` — 完整部署实录 + 多格式订阅
- 详细踩坑实录见 `references/session-gcp-aws-peer-setup.md`（含 IP 迁移实录）
