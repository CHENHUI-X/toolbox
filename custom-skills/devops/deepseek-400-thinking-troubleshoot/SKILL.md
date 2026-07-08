---
name: deepseek-400-thinking-troubleshoot
description: DeepSeek 模型 HTTP 400 报错排查 — reasoning_effort + api_mode 不兼容导致
category: devops
---

# DeepSeek HTTP 400 报错排查

## 现象

- Hermes 回复时突然报 `HTTP 400` 或 `Bad Request`
- 通常在开启 reasoning/thinking 模式后出现
- DeepSeek 返回 `thinking` 内容后，后续请求报 400

## 根因

DeepSeek API 有个特殊规则：**一旦模型输出了 `thinking`/`reasoning_content`，后续所有 assistant 消息都必须回传这个字段**，否则报 400。

当 `api_mode: anthropic_messages` 时，Hermes 用 Anthropic 格式封装请求，但 DeepSeek 的 thinking 字段在 Anthropic 格式下翻译不正确，导致 reasoning_content 丢失 → 400。

## 排查步骤

### 1. 查配置

```bash
grep -E "reasoning_effort|api_mode" ~/.hermes/config.yaml
```

关键看两处：
- `reasoning_effort: high`（或 non-empty）— 思考模式开了
- `api_mode: anthropic_messages` — **罪魁祸首**

### 2. 修

**方案 A（推荐）：保留 reasoning，改 api_mode**
```bash
hermes config set model.api_mode chat
```
把 `api_mode` 改成 `chat`（标准 Chat/OpenAI 格式）。DeepSeek 的 reasoning 在这种格式下透传正常。base_url 已经有 `/v1` 后缀就对了。

**方案 B（备用）：关 reasoning**
```bash
hermes config set agent.reasoning_effort none
```
但这样思考模式就关了，不推荐。

### 3. 验证

```bash
grep -E "reasoning_effort|api_mode" ~/.hermes/config.yaml
```

预期结果：
```yaml
api_mode: chat
reasoning_effort: high  # 或你想要的级别
```

同时检查 `base_url` 是否带了 `/v1`（如 `https://xxx.com/v1`），这是 Chat API 的标准路径。

然后 `/reset` 重开会话测试。

## 注意事项

- `api_mode: anthropic_messages` 适合 Anthropic 自家模型（Claude），不适合 DeepSeek
- `api_mode: chat` = 标准 Chat/OpenAI 格式，base_url 带 `/v1`，DeepSeek 原生支持
- 自定义 provider（如 packyapi.com）即使底层转发了深求 API，也要用 OpenAI 格式
- 远程 Hermes 已有相关修复（`ad0ac8947`、`bfb704684` 等），但核心还是配置兼容问题

## 参考

- `references/anthropic-messages-deepseek-fix.md` — 完整修复记录和配置对照
