---
name: gcp-hermes-update-safety
description: GCP VM (instance-20260525-051751) 更新 Hermes 的安全流程。SSH 直跑 hermes update 会被断线打断、弄坏 venv（pydantic_core 消失）。必须用 systemd-run。也覆盖误触发 update 的识别与善后。
---

# GCP Hermes 更新安全流程

## 铁律
- 禁止直接 SSH 跑 `hermes update`。SSH 断线 = update 被杀 = venv 半坏 = 所有 agent run 报
  `No module named 'pydantic_core._pydantic_core'`（2026-09-28 事故实录）。
- 必须放进 systemd transient unit 跑，断线不死。
- 经 gcloud ssh 的 `--command` 传多行 heredoc 时引号极易被打散，可能意外触发本机或远端
  update。给远端写文件一律用 `gcloud compute scp` 传本地文件，不用内联 heredoc。

## 标准更新流程

```bash
# 1. 发起（systemd-run 包裹，日志落 /tmp）
systemd-run --unit=hermes-update --collect /bin/bash -lc \
  'hermes update > /tmp/hermes-update.log 2>&1; echo RC=$? >> /tmp/hermes-update.log'

# 2. 轮询直到结束（全程约 15 分钟，可能两轮：先补上次尾巴再拉新）
systemctl is-active hermes-update; grep 'RC=' /tmp/hermes-update.log; tail -2 /tmp/hermes-update.log
# 结束判定：unit inactive + RC=0

# 3. 重启 gateway 并验证
systemctl restart hermes-gateway && sleep 8 && systemctl is-active hermes-gateway
journalctl -u hermes-gateway --since '10 min ago' --no-pager | grep -cE 'pydantic_core|Failed to initialize OpenAI'
# 必须为 0

# 4.（可选）真实 venv 路径验证 —— 更新后 environments/ 会换新 hash，以 facts.json 为准
#    注意 /usr/local/lib/hermes-agent/venv 可能是旧软链，直接 import 测它会有假阴性
python3 -c "import json,glob; f=glob.glob('/root/.hermes/installs/*/facts.json')[0]; \
  print(json.load(open(f))['venv']['environment'])"
```

## 事故特征（识别旧伤）
- gateway active 但所有 agent run 报 pydantic_core 缺失
- `hermes pairing list` 打印 "an update is still running"（死锁标记）
- `cat /root/.hermes/installs/*/source-completion-pending` 存在 = 上次 update 没跑完
- 修复 = 按上面标准流程重跑 update + 重启 gateway

## 误触发 update 的善后（如被外层命令意外带起）
1. 别杀正在跑的 update（杀了才留残局）。`ps aux | grep 'hermes update'` 确认它还活着。
2. 等它自然结束，日志出现 `✓ Update complete!` 即安全。
3. 结束后验证：gateway active、pydantic 报错 0、`source-completion-pending` 不存在。
4. 版本可能被顺手升上去（本次 d9f6a84 → gfc4dbe3 一线），属于无害升级，不用回滚。

## 其他注意
- 这台是 1GB 内存 VM：web UI 构建可能 node OOM（"JavaScript heap out of memory"），
  不致命，重跑 update 会过。
- 更新后若微信/消息异常，先查本机 `platforms` enabled（config.yaml）——本机只启用了
  webhook + qqbot，微信问题别默认背到这台机器头上。
- gcloud 偶发 SSL 崩溃（compute.googleapis.com 连接被掐），等 10 秒重试即可。
