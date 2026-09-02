---
name: plan-execute-orchestrator
description: "运行透明、审慎的 Codex 编排流程：委派前按四象限告知规划、复杂执行、低复杂度实现和机械化任务的模型与思考强度；默认使用 Sol / high 规划，并在实际执行范围复杂时自动延长为 Sol / xhigh 深度规划，Terra / xhigh 处理复杂实现、Luna / medium 处理确定且低复杂度的实现、Luna / low 处理机械化只读操作，并可选注册第三方 Responses API profile 用于规划或执行。适用于用户要求规划/执行编排、Sol 规划 Terra 执行、按项目复杂度增加规划深度、第三方模型规划或执行、先出计划、成本敏感的多 Agent 实施，或为该流程注册第三方供应商的编码、调试、重构和配置任务。不要用于纯只读问答（除非用户明确要求测试本 Skill），或必须由用户先做产品决策的任务。"
---

# 规划-执行编排

保持规划与实施分离。父 Agent 负责编排，明确告知实际模型路由，把规划 Agent 的完整结果传给一个执行 Agent，并报告经验证的结果。

## 模型路由告知

委派任何子 Agent 前，检查可用的模型覆盖能力，并向用户发送可见的模型路由说明。在发送说明前，不要开始委派。

用户没有指定时，按以下四象限选择：

| 象限 | 默认模型 | 默认思考强度 | 适用范围 |
| --- | --- | --- | --- |
| 高创造性 + 模糊需求 | `gpt-5.6-sol`，或用户指定的已注册第三方 profile | `high`，或已验证的供应商-模型设置 | 架构、技术选型、PRD 拆解和规划。 |
| 高复杂度 + 确定目标 | `gpt-5.6-terra`，或用户指定的已注册第三方 profile | `xhigh`，或已验证的供应商-模型设置 | 老代码重构、多文件联动、顽固 Bug 和复杂实施。 |
| 低复杂度 + 确定目标 | `gpt-5.6-luna` | `medium` | 单一、套路固定且可验证的单测、格式转换或 API 文档等小改动。 |
| 机械化操作 | `gpt-5.6-luna` | `low` | 读取文件、列目录、全局搜索和初筛日志；只读。 |

规划默认从 `gpt-5.6-sol / high` 开始。若任务描述已明确属于复杂实施，或初始调研发现执行范围复杂，必须在启动写入型执行器前延长规划：使用 `gpt-5.6-sol / xhigh` 完成一次受限的深度规划补充。路由说明中要提前告知这个可能的升级；不因单文件、边界清晰的小改动而升级。

用用户的语言说明实际配置和任何回退。例如：

```text
本次模型编排：规划初始使用 gpt-5.6-sol / high；若调研确认执行范围复杂，我会在实施前增加一次 gpt-5.6-sol / xhigh 深度规划；复杂实施使用 gpt-5.6-terra / xhigh；确定且低复杂度的小改动使用 gpt-5.6-luna / medium；读文件、列目录或搜索等机械化只读操作使用 gpt-5.6-luna / low。测试和构建属于验证，由执行 Agent 按其实际副作用运行。你也可以指定已注册的第三方 profile 用于规划或执行；我会说明供应商、模型和已接受的思考强度。若尚未注册，我可以按可选注册流程配置。第三方 profile 会启动独立的 Codex CLI 会话，不会让第三方模型出现在桌面端与官方模型并列的选择菜单中。请回复“按此配置开始”，或直接改写任一象限的模型/思考强度。
```

### 原生委派接口未列出 Luna 时

不要把 Luna 称为“当前运行时不可用”。若原生子 Agent 的模型列表未列出 Luna，但当前官方登录可通过 CLI 调用它，应在路由说明中明确改为 **官方 CLI 调用 Luna**，例如：

```text
低复杂度实现仍使用 gpt-5.6-luna / medium，机械化只读操作仍使用 gpt-5.6-luna / low。当前原生子 Agent 委派接口未列出 Luna；确认后我会使用隔离用户 custom 配置的官方 OpenAI CLI 会话调用它。这样保留指定的模型和思考强度，改动仍在同一工作区。差异是首次调用有 CLI 启动开销，父 Agent 需显式传入计划和必要上下文，CLI 会话独立于桌面端主会话；同一任务的后续修正会续接该角色已有会话，不会重复新建上下文。
```

这是传输方式变化，不是模型回退。用户已确认该路由时，直接使用 CLI，不再要求把 Luna 换成 Terra。仅当用户明确只接受原生子 Agent，或官方 CLI 也实际拒绝 Luna 时，才说明 Luna 不能满足该角色，并询问：`是否允许将低复杂度实现回退为 gpt-5.6-terra / medium、机械化只读操作回退为 gpt-5.6-terra / low？` 未获明确同意不得回退。

### 启动门槛

在开始任何实际任务前，必须先发送上方的中文模型路由说明，明确列出本次的规划、复杂执行、低复杂度实现和机械化操作模型及各自思考强度，并说明复杂范围触发时是否会增加 Sol / xhigh 深度规划。若原生委派接口未列出 Luna，要按上一节告知官方 CLI 调用方式和实际差异，不能只写“不可用”。此时只允许检查当前运行时的模型控制能力；不得检查仓库、委派子 Agent、修改文件、写入凭据/配置或发起计费请求。

路由说明结尾必须请用户确认或修改，例如：`请回复“按此配置开始”，或直接改写任一象限的模型/思考强度。` 收到用户确认或修改后，复述最终完整路由，再开始规划和执行。只有用户在初始任务中明确写明“按默认直接开始”或等价表述时，才可将其视为已确认，不必等待额外回复。

用户指定模型或思考强度后，复述完整的最终配置并遵守它。第三方角色请求必须指向本 Skill 注册并验证过的 profile；仅给出模型 ID 不足以选择供应商。若用户想用的第三方供应商尚未注册，先提供下方的可选注册流程。若偏好与角色冲突、遗漏重要决策，或指定的模型/profile 不可用，要求用户澄清。不要静默替换模型或供应商。

首次让某个第三方 profile 处理当前仓库任务前，单独说明供应商与接口地址、角色、将发送的内容类别（原始请求、计划、相关代码/配置/日志片段）和仓库范围，并取得明确确认。注册 profile、批准计费验证与允许本任务的数据发送是独立的确认边界。

## 可选：注册第三方 profile

仅当用户要求用第三方模型做规划或执行，或明确要求注册时，才运行本节。其他情况下保持默认的官方模型路径不变。第三方模型只注册给 CLI 编排使用；不要修改桌面应用、补丁模型选择菜单、替换基础 OpenAI 供应商，也不要承诺统一的桌面历史记录或模型菜单。

### 用中文收集信息

先判断当前环境是 macOS 桌面端、macOS 命令行、Linux 服务器命令行还是 CI。然后仅询问缺失项；一套凭据可填写多个模型：

```text
凭据保存方式：macOS 钥匙串 / 环境变量 / 现有凭据管理器
供应商名称：
供应商文档链接（可选）：
接口地址（Base URL，含不含 /v1 均按文档填写）：
接口协议：Responses / 不确定，允许我测试确认
计划用途：规划 / 执行 / 两者都要
模型列表（每个模型单独一项）：
1. 实际 API 模型 ID：
   本地显示名称：
   规划或执行的思考强度：
```

说明“实际 API 模型 ID”会发送给供应商；“本地显示名称”只是易读的 profile 标签，不代表模型会显示在桌面端选择菜单中。询问所有模型是否共用同一 API Key。不得把 Key 放入 shell 命令、TOML、输出或日志。保存凭据、写入任何用户级 profile，或发起可能计费的真实请求前，必须取得用户明确确认。

### 选择持久凭据存储

- 在 macOS 桌面端或 macOS 命令行，推荐当前 macOS 用户使用 **macOS 钥匙串**。说明 Keychain 的“服务名称”是查询标签，例如 `Codex Provider packyme`；账户名固定为 `api-key`。它可供该用户的桌面端和终端会话使用，但不能供其他 macOS 用户使用。若用户手动录入，指导其打开 **钥匙串访问**，选择 **登录** 钥匙串，点击 **文件 → 新建密码项目**，将项目名称设为服务名称、账户名设为 `api-key`，并只在密码字段粘贴 Key。
- 在服务器或 CI，优先使用平台自身的凭据管理器。若选择环境变量，建议不冲突的名称，例如 `<PROVIDER_SLUG>_CODEX_API_KEY`：其中 slug 为大写 ASCII，非字母数字字符替换为下划线。说明必须按照实际启动 Codex 的方式持久设置：个人服务器账号使用该用户的登录/服务环境，CI 使用 CI 密钥库。不要把一次交互式 shell 的 `export` 说成全局设置。机器级明文 `/etc/profile` 变量会把共享密钥暴露给无关用户，不是推荐默认方案；任何共享凭据设计都需要管理员和用户明确确认。
- 若用户已有凭据助手命令，使用 `[model_providers.<id>.auth]`，不要使用 `env_key`。命令型 `auth` 不得与 `env_key`、`experimental_bearer_token` 或 `requires_openai_auth` 组合。

钥匙串 profile 应通过下方 provider 认证块按需读取密钥；只替换供应商标识和服务名称：

```toml
[model_providers.<provider_id>.auth]
command = "/usr/bin/security"
args = ["find-generic-password", "-s", "Codex Provider <provider_slug>", "-a", "api-key", "-w"]
timeout_ms = 5000
refresh_interval_ms = 300000
```

### 创建 profile，但不接管官方 Codex

保持现有 `~/.codex/config.toml` 中的官方供应商和登录不变。每个实际 API 模型创建一个用户级 profile 文件：`~/.codex/<profile-name>.config.toml`；绝不能把 provider 配置写进项目的 `.codex/config.toml`。使用稳定的 profile 名称，例如 `thirdparty-<provider-slug>-<model-slug>`；确保不与已有 profile 冲突，并在注册结果中记录“本地显示名称 → profile 名称”的映射。

每个模型使用以下结构；仅在取得确认后再替换为真实值：

```toml
model_provider = "<provider_id>"
model = "<actual_api_model_id>"
model_reasoning_effort = "<verified_effort>"

[model_providers.<provider_id>]
name = "<provider_name> — <local_display_name>"
base_url = "<base_url>"
wire_api = "responses"
supports_websockets = false

# 认证方式只能二选一：
env_key = "<PROVIDER_SLUG>_CODEX_API_KEY"
# 或使用上方的钥匙串/凭据助手 auth 块，不要同时使用 env_key。
```

`responses` 是唯一支持的自定义 provider 协议。不要假设支持 WebSocket 或工具调用；除非已验证兼容的 Responses WebSocket 传输，否则保持 `supports_websockets = false`。仅为运行 CLI profile 时，不要添加 `model_catalog_json`。第三方 profile 通过 `codex --profile <profile-name>` 选择，因此不会影响该进程之外的官方订阅配置。

### 在路由任务前验证每个 profile

用户批准计费验证后，逐个测试模型。原样报告供应商的错误响应，但绝不输出 API Key。

1. 在已验证的仓库根目录中，通过 `codex exec --profile <profile-name> --sandbox read-only --cd <repo-root> --json -` 发起最小 Responses 文本请求，并确认返回的 `thread.started.thread_id`；完整测试内容通过标准输入传入，不拼接 shell 命令。
2. 对每个拟用于执行的模型，运行 `pwd` 等最小工具调用任务；工具调用失败时，不得标为可执行。
3. 用相同的 thread ID 续接一次简短追问。这只证明 Codex 会话续接，不代表供应商一定命中提示词缓存。
4. 测试用户要求的思考强度；若被拒绝，报告已验证证据，在改动配置中的思考强度或省略它前询问用户。

文本测试成功后将 profile 标记为 `planning-only`；工具调用也成功后才能标记为 `execution-capable`。如果供应商没有兼容实现 `/v1/responses`、不接受该模型，或拒绝 Codex 工具流量，则该角色不可注册；提供官方模型作为回退。不要通过补丁桌面应用来规避此限制。

## 用户确认后的执行前检查

1. 发送模型路由说明前，检查子 Agent 委派工具和官方 CLI 的有效 provider。只有已确认是 OpenAI 的 CLI 配置才可称为“官方 Luna”；不要仅因模型名相同就继承当前 custom provider。无法确认时说明实际 provider，并让用户选择官方 CLI profile、已确认的第三方 profile 或 Terra 回退。
2. 确定且低复杂度的小改动固定使用 `gpt-5.6-luna / medium`；纯机械化只读操作固定使用 `gpt-5.6-luna / low`，不得静默改用 Terra。Skill 在任务中只读取现有 `~/.codex/config.toml`，绝不自动修改全局默认；用户若希望持久设置子 Agent 默认模型，必须单独说明其跨任务影响并取得确认。原生路径仅在实际模型回报为 Luna 时可用于低复杂度实现；机械化只读操作统一使用 `read-only` CLI，避免继承父会话写权限。
3. 在规划前为每个请求象限选择传输方式：官方 Sol/Terra 路径使用原生子 Agent 的显式覆盖；Luna / medium 路径仅在原生委派实际应用 Luna 时使用，否则使用已确认 OpenAI provider 的官方 CLI；Luna / low 机械化路径使用只读官方 CLI；第三方路径使用一个已注册的 CLI profile。不要只传一个模型字符串给原生委派工具来选择第三方供应商。
4. 每个第三方角色都必须有已注册 profile、精确的供应商/模型信息、角色能力标记（`planning-only` 或 `execution-capable`）和已接受的思考强度。若有任一项缺失，仅在用户要求配置时运行可选注册流程；否则请用户选择官方模型或提供已有 profile。
5. 每个第三方角色在每个用户任务中只创建一个角色**会话**。启动前完成当前仓库的数据发送确认；第三方规划会话必须只读，第三方执行会话是唯一写入者。
6. 若所请求的官方规划、执行或简单任务模型控制不可用，先尝试已确认 provider 的官方 CLI 路径。原生委派不能选 Luna但 CLI 可用时，继续以 Luna 执行；仅在两条路径都被拒绝时报告实际错误，并在需要回退时取得用户对 Terra / medium 和 Terra / low 的明确同意。不要静默让父 Agent 同时承担两个角色，也不要把 Luna 静默替换为 Terra。
7. 使用串行流水线。规划未返回完整计划前，不得启动执行；原生子 Agent 使用 `fork_turns: "none"`，并且不得让 profile 执行器与其他写入者并发运行。
8. 保留用户原有的权限策略。规划 Agent 不得修改工作区文件；执行 Agent 仅可修改计划所支持的文件。

### 子 Agent 协作状态

根据原生子 Agent 的 Active、Done、需要输入、失败状态，或 CLI 的 JSON 终态和进程退出码协作：Active 时持续等待并简要同步，Done 时汇总结果，需要输入或失败时保留已有发现并上报。耗时和暂时无输出只触发状态检查，不自动终止或新建替代执行器；CLI 同一角色续接记录的 `planner_session_id` / `executor_session_id`。

## 阶段一：使用选定的规划 Agent

默认官方规划路径先使用一个初始规划子 Agent：

```text
task_name: sol_planner
model: gpt-5.6-sol
reasoning_effort: high
fork_turns: none
```

已注册的第三方规划 profile 使用一个只读 CLI 会话：

```text
codex exec --profile <planner_profile> --sandbox read-only --cd <repo-root> --json -
# 通过标准输入传入原始请求、约束、仓库位置和规定的规划输出格式。
```

捕获其 `thread.started.thread_id` 为 `planner_session_id`。标为 `planning-only` 的 profile 不得用作执行器。

给规划 Agent 原始请求、已知约束、仓库位置及用户验收标准，要求它检查相关代码路径、估计实际执行范围，并严格返回：

```markdown
## 目标和约束
## 证据
- 文件/符号：观察到的行为或依赖

## 复杂度与规划深度
- 常规 / 深度：判定结果及证据
- 预计执行模型：Terra / Luna 及原因

## 实施计划
1. 文件/符号 — 计划改动及原因

## 验证
- 精确命令或人工检查

## 风险和停止条件
- 假设、兼容性风险或需要用户决定的事项
```

规划 Agent 必须区分观察事实与假设；不得编辑文件、应用补丁、创建提交、执行破坏性命令，或代替用户做产品决策。

### 按执行复杂度延长规划

初始规划后、启动执行前，由父 Agent 根据初始规划的证据判定规划深度。满足以下任一高风险信号，或满足以下普通信号中的两项时，判定为**深度规划**：

- 高风险信号：安全/权限边界、数据迁移或兼容、并发与一致性、跨仓库协调。
- 普通信号：跨多个子系统或公共接口、多文件依赖链不清、旧代码缺少可靠测试或文档、外部服务副作用不明确、验证或回滚路径复杂。

需求本身已明确属于深度规划时，可在用户确认的路由中直接使用 Sol / xhigh；否则先完成 Sol / high 初始调研。判定为深度规划后，必须在执行器启动前增加且仅增加一次深度规划补充：

```text
task_name: sol_extended_planner
model: gpt-5.6-sol
reasoning_effort: xhigh
fork_turns: none
```

向该 Agent 传入原始请求、初始规划全文和已收集证据。它只补齐实际执行所需的内容：调用链与依赖顺序、影响文件和接口契约、边界条件与失败模式、迁移/回滚方案、最小验证矩阵；随后返回一份可替换初始计划的完整最终计划。不得为了“多想一会儿”重复探索已确认的事实，不得扩展为全仓库调研、启动写入、执行无关测试或代替用户作产品决策。

### 规划与验证预算

深度规划是提高必要细节，不是提高覆盖面。规划 Agent 只读取能证明当前变更影响的代码、配置、测试和文档；已有证据足够时立即停止调研。禁止为“保险”扫描无关目录、枚举全量依赖、重做相同检索，或将一次深度规划再拆成多轮泛化探索。

验证默认只选能直接证明用户验收标准和改动行为的最小检查：优先受影响模块的定向测试、类型/构建检查或一项人工验证。除非初始证据表明改动触及共享契约、迁移、安全、并发、构建链路，或用户明确要求，否则不得自动运行全量测试、长时间集成/E2E、网络调用、负载测试或重复验证。深度规划输出中必须为每一条验证说明“验证什么”和“为何足够”；无法证明必要性就不加入计划。

用户明确要求保持短规划时不自动升级；但发现上述高风险信号时，必须说明风险和短规划的局限。第三方规划 profile 只可使用已验证的思考强度；若不支持相当于 `xhigh` 的设置，则在同一 profile 下增加一次只读规划补充，并在最终报告中如实说明实际强度，不能宣称已使用 Sol / xhigh。

规划发现重大的产品、安全、迁移或破坏性选择时，把选项交给用户并停止，不得猜测并实施。

## 阶段二：选择并使用执行 Agent

### 四象限分流

规划、技术选型或需求尚模糊时，使用 Sol / high。多文件改动、遗留代码重构、顽固 Bug、迁移、复杂依赖或安全敏感实现，使用 Terra / xhigh。仅当计划是单一、固定套路、范围明确且可独立验证的小改动时，才使用 Luna / medium，例如补充单元测试、格式转换或 API 文档；涉及接口契约、运行时行为或跨文件协调时改用 Terra。读取文件、列目录、全局搜索和初筛日志属于机械化只读操作，使用 Luna / low；测试和构建由执行 Agent 按实际副作用与最小验证要求运行。用户明确指定模型或强度时，优先遵守用户指定。

确认初始规划或深度规划的最终计划已返回具体步骤和验收检查。常规或复杂任务的默认官方执行路径使用一个子 Agent：

```text
task_name: terra_executor
model: gpt-5.6-terra
reasoning_effort: xhigh
fork_turns: none
```

判定为低复杂度、确定目标的小改动时，使用 Luna / medium。只有原生子 Agent 实际报告 Luna / medium 时才保留原生路径：

```text
task_name: luna_executor
fork_turns: none
```

若该原生路径没有实际应用 Luna，或原生委派模型列表未列出 Luna，则用官方 CLI 建立同一角色的单一会话。这保留 Luna / medium，不是 Terra 回退；路由确认中已说明 CLI 的启动和独立会话差异后，直接执行：

```text
codex exec --ignore-user-config --model gpt-5.6-luna --config 'model_reasoning_effort="medium"' --sandbox workspace-write --cd <repo-root> --json -
# 通过标准输入传入原始请求、完整计划、约束和验收检查；首次使用前确认该隔离配置实际指向 OpenAI。
```

读取该 CLI 的 `thread.started.thread_id` 并保存为 `executor_session_id`；后续修正必须续接这个会话。

机械化只读操作使用独立的 Luna / low CLI 会话；它不参与代码实施：

```text
codex exec --ignore-user-config --model gpt-5.6-luna --config 'model_reasoning_effort="low"' --sandbox read-only --cd <repo-root> --json -
# 通过标准输入传入精确的只读任务；首次使用前确认该隔离配置实际指向 OpenAI。
```

这是 Luna 的 CLI 传输方式，不是模型回退。返回精简的证据，不输出冗长推理。

已注册且标为 `execution-capable` 的第三方执行 profile，在同一仓库中启动一个串行 profile 会话：

```text
codex exec --profile <executor_profile> --sandbox workspace-write --cd <repo-root> --json -
# 通过标准输入传入原始请求、完整计划、约束和验收检查。
```

读取 `thread.started.thread_id` JSON 事件并保存为 `executor_session_id`。之后的 `resume` 会启动新的 CLI 进程，但续接的是同一个 Codex 执行会话，并非新的执行上下文。使用 profile 已验证的供应商/模型配置；不得注入 API Key、改动 profile，或在命令行传入未经验证的思考强度。将它的最终消息和工作区差异视作执行结果。

### CLI 执行会话与缓存边界

- 每个用户开发任务仅创建一个 CLI 执行会话（官方 Luna 或第三方）。不得用于不相关的任务，因为陈旧上下文的危害大于可能的缓存收益。
- 计划需要修正时，在相同配置下续接精确的 `executor_session_id` 并从标准输入传入修正计划；不要为修正新建 `exec` 会话。顶层配置必须位于 `resume` 前，例如：`codex exec --profile <executor_profile> --sandbox workspace-write --cd <repo-root> --json resume <executor_session_id> -`；官方 Luna 路径保留相同的 `--ignore-user-config`、模型和思考强度覆盖。
- 续接会保留 Codex 的对话/会话上下文，但**不保证**供应商侧提示词缓存复用；这取决于第三方模型、精确提示词前缀、缓存 TTL 和供应商实现。
- 规划和执行会话是独立的供应商请求。即使使用同一供应商，缓存复用也由供应商决定且不保证；应把计划作为普通任务上下文传递。

向任一执行 Agent 提供原始请求、规划 Agent 的完整计划、约束和验收检查，并要求它：

- 只实施已批准的计划，避免无关清理；
- 修改前检查已有代码；
- 遵循工作区编辑约定，并仅执行计划中与验收直接相关、与风险相称的最小验证；
- 报告改动文件、验证命令及结果、偏差和阻塞项；
- 不得自行发明新架构或静默扩大范围，必要时停止并报告。

官方 Terra 执行器默认使用 `xhigh`；低复杂度、确定目标的小改动使用 Luna / `medium`；机械化只读操作使用 Luna / `low`。第三方执行器只使用已为该供应商/模型验证的思考强度，不得臆造等效设置。仅当用户明确要求更低成本配置时才降低强度。

## 恢复与交接

实施暴露出计划的重大错误时，保留执行器的部分发现。仅向同一规划传输方式请求一次针对性修正：原生规划 Agent 使用已有 Agent 跟进；第三方规划 Agent 使用相同 profile 续接已记录的 `planner_session_id`。然后把修正后的计划发给已有执行器：原生 Terra 或 Luna 执行器使用已有 Agent 跟进；CLI 执行器（官方 Luna 或第三方）续接 `executor_session_id`。任一必需会话不可用或无法续接时，停止并报告恢复阻塞；不要新建角色会话作为回退。一次修正后仍有问题时，停止并解释阻塞，而不是无限循环。

执行成功后，检查执行器报告的差异和验证证据，再报告完成。说明最终生效的规划和执行供应商/模型/强度、规划深度判定及触发证据、改动文件、验证结果和遗留风险。
