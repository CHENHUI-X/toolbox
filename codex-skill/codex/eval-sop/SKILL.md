---
name: eval-sop
description: 编排司机助手离线或线上评估的 DMS 闭环与断点恢复。用于完整评估、线上效果分析、明确要求的回放或配置对比；默认直评已有线上 output，支持用户明确选择 local-only。专项评分交给对应评估 Skill，单独查数或 DMS 接口操作使用对应技能。
---

# Eval SOP

专项 Skill 负责输入契约和评分；本 Skill 负责编排、状态和平台交付。业务结果以实际产物与 DMS 回读为依据。

## 范围、依赖与授权

- 完整评估默认 `delivery_mode=platform`；用户明确“仅本地”“不要上传”时新建 `local-only` run，不在运行中静默降级。
- 平台模式需要 `$dms`；本地模式不要求 DMS。仅需线上取数时依赖 `$fetch-online-trace-full`；所有评分需要匹配的专项 Skill。
- 从实际安装路径读取所需 Skill。明确的专项名称且已安装版本唯一时直接采用并记录版本；用户指定版本时遵从。只有多种实现或版本会影响结果且上下文无法确定时才询问。
- 缺少指定技能时，可用 `$dms skill-download` 下载精确 `skill_id + version` 到独立工作目录，安全解压后读取入口。可查询 [DMS Eval Skills](http://dmstest.didichuxing.com/eval/skills)。未经明确要求不覆盖已安装版本；缺失能力只阻断依赖步骤。
- DMS 地址按“本次用户 `base_url` → `DMS_BASE_URL` → `https://dms-server-test.didichuxing.com`”解析并记录，默认测试环境无需再次确认。
- 用户要求完整评估且目标环境明确时，授权覆盖闭环内数据集、任务、记录和报告写入，无需逐步确认。本地审计、修改或方案准备不授权平台写入或 Skill 上传。目标冲突或新增范围需先澄清，可先用 `$dms --dry-run` 准备请求。

## 模式与最小输入

| 目的 | 模式 | 答案来源 |
| --- | --- | --- |
| 离线 Case Set 验证候选工程链路 | `offline` | 按专项离线契约生成/评分 |
| 已上线、昨天或最近的真实效果 | `online` + `direct_output`（默认） | 已有 Trace output |
| 明确要求回放、重新生成或验证候选 Prompt/Base Model | `online` + `replay` | 回放的新 output |

复用已明确的模式、时间范围、路径与配置。平台还需要 `application_id`、工作目录、专项版本、`category` 和结果任务解析策略，不要求用户预先创建 `task_id`。仅回放需要目标 Agent/版本、运行环境 IP/端口、并发度及稳定配置标识；比较时保留基线与候选标识。

回放运行环境按“用户明确指定的环境 → 恢复时 checkpoint 已验证的环境 → 默认 `10.179.63.17:8991`”解析。未特殊指定且无可复用配置时，直接使用默认 IP `10.179.63.17`、端口 `8991`，无需再次询问，并将实际环境写入 `replay.configuration` 和配置指纹。此默认值仅用于 Agent 回放执行环境，不替代 DMS `base_url` 或 Judge 地址；恢复已有 run 时仍遵守配置变更需新建 run 的规则。

`category` 保留用户选择：`regression`（回归）、`release`（验收）、`benchmark`（基准）、`smoke`（冒烟）；在线还允许 `online_replay`（线上 Trace 集，可直评或回放）。未指定时说明含义并请用户选择，不擅自决定。

平台模式在大量取数、回放或 Judge 调用前完成 `platform_preflight`：记录上述配置，确认可以复用本 run 关联且已核验为 `source=offline` 的结果任务，或有权威离线创建契约。缺参/缺能力保存失败阶段，继续能独立完成的准备；不以本地结果冒充平台交付。

## 状态与恢复

首次外部调用前创建持久化目录与唯一 `run_id`。读取 [checkpoint-contract.md](references/checkpoint-contract.md) 获取字段、阶段、原子写入命令及门禁，用 `scripts/checkpoint.py` 更新状态。调用前写 `running`，成功保存回执和 ID 后写 `completed`，失败保存脱敏错误。

```bash
python3 <skill-dir>/scripts/checkpoint.py init \
  --run-dir /absolute/path/to/eval-run \
  --mode online --online-strategy direct_output --delivery-mode platform
```

恢复使用本会话已明确的 `run_id` 或状态路径；不自动选最近一次。先 `verify`、再 `resume`，按已验证的 ID、配置和指纹复用产物。外部写入前保存请求指纹及含 `run_id` 的确定性名称；超时结果不明时先查询或人工核对，不盲目重复创建、启动或新增记录。

数据集、策略、回放配置或评分方法发生语义变化时新建 run，保留旧产物。旧 checkpoint 缺 `online_strategy` 时按历史 `replay` 恢复，缺 `delivery_mode` 时按 `platform`；不改变新 run 的直评默认值。

## 数据、回放与评分

1. **准备输入。** 已有文件直接复用；已有 `case_set_id` 下载到明确且不存在的路径，不重复导入。取数调用 `$fetch-online-trace-full` 获取 `[start, end)`，交接 `raw_trace_full.jsonl`，CSV 仅核对。原文件不修改，转换用保留稳定 Case/Query ID、顺序和指纹的派生文件。限制司机数据访问，不展示完整 Trace。
2. **登记数据集。** 按专项契约校验完整输入，不静默过滤以改变分母。平台新导入的离线/直评数据显式传 `source=offline`，回放输入传 `source=online`，避免 CLI 的分类默认值误用于直评。保存来源、分类、版本、ID、指纹及回执到 `dataset_ready`/`uploads.dataset`；已有集合来源不兼容时先解决输入选择，不能伪标来源或自动复制。
3. **仅 replay 回放。** 核对集合实际 `source=online`，按 `$dms` 契约创建并启动 `replay_only`，保存 `replay_task_created`，轮询到 `replay_completed`，从真实 `report_id` 导出到 `results_exported`。恢复先查原任务。按稳定 ID 提取新 response；比较报告两组分母、差值、提升/退化/持平和单侧失败，不静默丢行。
4. **结果任务（仅平台）。** 离线/直评在 `dataset_ready` 后执行，回放在 `results_exported` 后执行。优先复用本 run 关联且经 `task-detail` 核验为 `source=offline` 的任务，包括符合条件的本次回放任务；否则用权威接口、确定性名称和真实 `case_set_id` 创建。保存 `result_task_created`/`uploads.task`。资格取决于实际 `source`，不只看 `run_mode`。缺少创建契约且无法复用时停在本阶段，不猜 schema 或要求用户先手工建任务。
5. **专项评分。** 校验/prepare 通过后运行对应模式；直评不调用答案生成，回放评分只用新 output。不支持所需模式时请求兼容 Skill。保存 `evaluation_prepared`、`evaluation_completed`、输入指纹、专项版本、Judge/Prompt/Model 标识、逐 Case 结果、错误及汇总；在线 `evaluation.input_source` 分别为 `trace_output`/`replay_output`。平台模式先完成数据集和结果任务阶段；local-only 跳过平台动作。

## Judge 配置与恢复

- 按“本次显式值 → checkpoint 已验证值 → 专项默认值或环境变量”解析。保留专项端点、Model 和请求能力，不因本指南而替换模型。
- 新配置或兼容性存疑时，全量评分前用非敏感短 Prompt 做一次最小探测，核对连接、模型、响应结构和实际需要的可选参数。本 run 相同已验证配置不重复探测；探测不计入分母。
- 缺参、认证失败、超时、持续服务错误或格式不兼容时保存脱敏错误及已评分数；有限重试后停止依赖调用，不静默换模型。只请求需补充/替换的 Base URL、Model、认证安全传递方式和必要请求约束；凭证通过环境变量，不粘贴到聊天或 checkpoint。
- 新配置探测成功后从评分失败阶段继续，复用已验证取数/回放产物。零成功 Case 可在同一 run 记新 attempt；已有成功 Case 且 Model、Prompt 或判分语义变化时新建 run，用单一配置全量重评。仅传输兼容调整且语义不变时可继续原 run，保留失败产物与说明。新 run 复用平台对象须重新核验归属和来源，不能继承写入完成状态。

## 平台回写与完成

评分成功后自动继续，不等待再次触发；local-only 仅完成本地阶段和相应门禁。

1. 使用 `result_task_created` 中已核验的离线 `task_id`，不在回写阶段临时换任务。保留 output 和链路元数据，按 `$dms` 契约映射字段，JSON 列序列化为 JSON 字符串。
2. 先 `record-save`。无 ID 是新增，首次提交前核对本 run 同批记录不存在，超时先查询；更新现有回放记录携带其 `id > 0` 并核对归属，新结果任务按新增处理。保存 `records_uploaded`/`uploads.records` 和回执。
3. 再 `report-save`，按同一 `task_id` UPSERT，不要求预先有 `report_id`。映射 `exec_summary`、`quality_summary`、`performance_summary`、`diagnosis`、`content`、`error_detail` 和短 `conclusion`，`source=offline`。检查 HTTP、`code == 0` 和返回 ID，保存 `report_uploaded`/`uploads.report`。
4. `8304148` 时回读来源、记录失败并停止该写入，不反复提交、换任务或伪造成功。部分成功保留真实回执，不能通过整体门禁。
5. 回读核对任务、记录/评分/跳过/错误数、报告 ID、指标和更新时间，完成 `verified`。当前完成门禁只接受测试报告路由 `http://dmstest.didichuxing.com/eval/tasks/{task_id}/report`。其他环境若使用不同路由，须在预检报告此实现限制并先完成适配；不能填测试 URL 冒充该环境报告或宣称门禁通过。
6. 保存 `completed=completed`（脚本先执行门禁），再执行 `checkpoint.py gate --state <run_state.json>`；只有 `ready: true` 才能宣称相应交付完成。平台必需阶段不能 skipped，失败保留 checkpoint 与产物，说明剩余工作。

认证和下载策略遵循 `$dms`：无认证配置时先请求，仅遇 `401`/`403` 或明确权限错误时补充；不读取浏览器 Cookie，不回显密钥。示例 ID、Agent 和环境不能作为真实参数。

## 交付与维护

报告模式/策略、数据和评分来源、数量、核心指标、平台门禁或具体阻塞及绝对产物路径。平台附 `case_set_id`、`task_id`、`report_id` 和已核实报告链接；完整配置指纹、回执和诊断留在 `run_state.json`/报告中。区分输入准备、评分完成与平台已核验。

每个已验证变更集将 `skill.version` patch 递增一次，以 Asia/Shanghai 的 `%Y%m%d%H%M` 更新 `updated_date`，保留 `created_date`；用户明确要求其他语义版本时遵从。
