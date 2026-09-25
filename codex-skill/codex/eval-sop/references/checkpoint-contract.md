# Eval Run Checkpoint Contract

在第一次外部调用前创建 `run_state.json`，并在每个阶段开始、成功或失败时原子更新。状态文件是恢复依据，不是评估数据本身；不要写入认证信息或完整 Trace 内容。

## 必须记录的状态

每个 run 使用唯一且稳定的 `run_id`，并至少保留：

- `delivery_mode`：`platform`（默认）或用户明确选择的 `local-only`；创建后不可修改；
- `online_strategy`：线上新 run 默认为 `direct_output`；仅用户明确要求回放、重新生成或配置对比时使用 `replay`；创建后不可修改；
- `dms`：环境、`application_id`、已创建或复用且核验为离线的结果任务 ID、报告 ID，以及报告 URL（默认测试环境为 `http://dmstest.didichuxing.com/eval/tasks/{task_id}/report`，当前 gate 固定校验该路由；其他报告路由需先适配实现）；
- `dataset`：数据集 ID、版本、来源、分类；
- `replay.tasks`：仅 `online_strategy=replay` 时保存每个基线/候选回放任务的任务 ID、报告 ID 和状态；
- `replay.configuration`：仅回放时保存运行环境、Agent、Agent 版本、Prompt/Model 标识、并发度及配置指纹；
- `artifacts`：原始输入、Trace、回放导出、逐 Case 结果和报告的绝对路径、SHA-256 与大小；
- `evaluation`：专项评估方法、Skill 版本、Judge/Prompt/Model 标识、非敏感 Judge 配置指纹、`judge_attempts`、`input_source`（`trace_output` 或 `replay_output`）和结果位置；每次 Judge 尝试至少记录 Base URL、Model、请求能力、状态、脱敏错误、成功/失败 Case 数和产物路径，禁止记录凭证；
- `uploads`：按 `dataset`、`task`、`records`、`report` 等键保存上传/创建回执和服务端 ID；
- `current_stage`、`status`、各阶段的 `attempt`、时间、错误与事件历史。

状态文件只保存必要元数据。禁止保存 Authorization、Cookie、密码、API Key、访问令牌或完整司机 Trace。

## 标准阶段

线上真实效果默认使用 `direct_output`：

```text
initialized → platform_preflight → trace_acquired → dataset_ready → result_task_created → evaluation_prepared
→ evaluation_completed → records_uploaded → report_uploaded → verified → completed
```

仅在用户明确要求时使用 `replay`：

```text
initialized → platform_preflight → trace_acquired → dataset_ready → replay_task_created
→ replay_completed → results_exported → result_task_created → evaluation_prepared → evaluation_completed
→ records_uploaded → report_uploaded → verified → completed
```

离线流程跳过 Trace 和回放阶段：

```text
initialized → platform_preflight → dataset_ready → result_task_created → evaluation_prepared → evaluation_completed
→ records_uploaded → report_uploaded → verified → completed
```

`platform` 模式下，不得跳过平台预检、数据集、离线结果任务创建、记录/报告上传和核验阶段。`direct_output` 的门禁不包含任何回放阶段；`replay` 才强制回放任务创建、完成和导出。在线输入已是 DMS Case Set 时，仅 `trace_acquired` 可标记为 `skipped`。只有显式 `local-only` run 才能跳过平台阶段，且仍需完成输入获取、评估准备、评估和最终阶段。

平台预检确认结果任务解析策略和必填参数可用，不要求用户预先提供 `task_id`。已有任务成功回读为 `source=offline` 时直接复用；否则由流程通过权威能力创建离线结果任务。只有来源核验成功后，才能完成 `result_task_created`。

## 写入顺序

1. 在调用外部接口前将阶段保存为 `running`。
2. 外部调用成功后先捕获返回 ID、版本、配置和回执，再把它们放进 patch 文件。
3. 对生成或下载的文件运行 `artifact`，保存绝对路径和 SHA-256。
4. 最后将阶段连同 patch 保存为 `completed`。
5. 任一步骤失败时保存为 `failed` 并写入精简错误；不得把凭证或完整数据写进错误字段。
6. `evaluation_completed` 成功后自动进入记录与报告回写。`report-save` 使用已核验的结果 `task_id` 作为 UPSERT 主键；成功后保存返回 `report_id`、回执和按 `task_id` 拼接的报告 URL，不等待用户再次触发。

示例：

```bash
python3 <skill-dir>/scripts/checkpoint.py init \
  --run-dir /absolute/path/to/eval-run \
  --mode online \
  --online-strategy direct_output \
  --delivery-mode platform

python3 <skill-dir>/scripts/checkpoint.py save \
  --state /absolute/path/to/eval-run/run_state.json \
  --stage dataset_ready \
  --status running

python3 <skill-dir>/scripts/checkpoint.py save \
  --state /absolute/path/to/eval-run/run_state.json \
  --stage dataset_ready \
  --status completed \
  --patch-file /absolute/path/to/dataset-checkpoint.json

python3 <skill-dir>/scripts/checkpoint.py artifact \
  --state /absolute/path/to/eval-run/run_state.json \
  --stage results_exported \
  --name replay_export \
  --path /absolute/path/to/replay-export.json
```

Patch 文件是合并到顶层状态的 JSON 对象。例如：

```json
{
  "dataset": {
    "id": "289",
    "version": "v1",
    "source": "online",
    "category": "online_replay"
  },
  "uploads": {
    "dataset": {
      "kind": "dataset",
      "receipt_id": "receipt-123",
      "status": "success"
    }
  }
}
```

## 恢复规则

1. 恢复时使用本会话已明确的 `run_state.json` 或 `run_id`；无法唯一确定时询问，不自动选择“最近一次”运行。
2. 先执行 `verify`，再执行 `resume`。文件缺失或指纹不一致时先修复状态，不得继续使用损坏产物。
3. `completed` 阶段只有在 ID、回执和产物仍可验证时才跳过。平台必需阶段即使旧状态写成 `skipped`，`resume` 也必须把它识别为待完成；旧状态未记录 `delivery_mode` 时按 `platform` 处理。
4. `running` 或 `failed` 的外部阶段必须先查询服务端状态：
   - 已有数据集 ID：下载或查询原数据集，不重新上传；
   - 已有离线结果任务 ID、可复用回放任务 ID 或创建回执：查询原任务并核对 `source=offline`，不重新创建；
   - `replay` 已有回放任务 ID：调用 `task-detail`，不重新创建或启动；
   - 已有报告 ID：导出并核验，不重新回放；
   - 已有上传回执或记录 ID：查询原记录，不以无 ID 的新增请求重试。
5. 外部写入前先保存非敏感请求参数、请求指纹和包含 `run_id` 的确定性对象名称。若请求超时且没有拿到 ID 或回执，先按对象名称在 DMS 查询或人工核对；在无法确认服务端是否已受理前禁止盲目重试。
6. 本地评估结果只有在输入文件、评估 Skill 版本、Prompt/Model 和结果指纹一致时才复用。
7. 数据集、线上策略、回放配置、评估方法或版本发生语义变化时创建新的 `run_id`。不要在原 run 中覆盖配置后继续复用下游结果。旧 checkpoint 未记录 `online_strategy` 时按历史语义 `replay` 恢复；不得把旧 run 自动改成直评。
8. 完成回写并回读核验后，才将 `verified` 和 `completed` 标记为完成。`save --stage completed --status completed` 会执行完成门禁；任何缺失阶段、数据集 ID、分类或上传回执都会拒绝落盘。
9. Judge 恢复按 [SKILL.md 的 Judge 配置与恢复](../SKILL.md#judge-配置与恢复) 执行：零成功 Case 可在同一 run 新增 attempt；已有成功 Case 且 Model/Prompt/判分语义变化时新建 run 并全量重评。仅传输兼容调整且语义不变可继续原 run。保存配置指纹、失败产物和说明；新 run 复用平台对象时重新核验归属和来源，不能继承写入完成状态。

## 完成门禁

平台模式必须同时满足：

- 标准阶段完成；在线仅在已记录 `dataset.id` 时允许跳过 Trace 获取；
- `direct_output` 不要求任何回放阶段，但必须记录 `evaluation.input_source=trace_output`；`replay` 必须完成回放任务创建、完成和导出阶段，并记录 `evaluation.input_source=replay_output`；
- `dataset.id` 非空、分类合法；`online_strategy=replay` 的回放数据集记录为 `dataset.source=online`，其他流程记录为 `dataset.source=offline`；
- DMS `base_url`、`application_id`、已创建或复用的离线结果任务 ID、报告 ID 和按任务 ID 拼接的报告 URL 已记录；回放模式还必须记录回放任务 ID，允许它与结果任务 ID 相同；
- `uploads.dataset`、`uploads.task`、`uploads.records`、`uploads.report` 都是非空成功回执；
- 所有已登记产物的路径和 SHA-256 仍可验证。

完成后再次运行：

```bash
python3 <skill-dir>/scripts/checkpoint.py gate \
  --state /absolute/path/to/eval-run/run_state.json
```

只有输出 `ready: true` 才能对外宣称平台评估完成。`local-only` run 不要求 DMS 回执，但必须完成本地输入、评估准备、评估和最终阶段。

恢复检查：

```bash
python3 <skill-dir>/scripts/checkpoint.py verify \
  --state /absolute/path/to/eval-run/run_state.json

python3 <skill-dir>/scripts/checkpoint.py resume \
  --state /absolute/path/to/eval-run/run_state.json
```
