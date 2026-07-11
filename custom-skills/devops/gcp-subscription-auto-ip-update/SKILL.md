---
name: gcp-subscription-auto-ip-update
description: GCP 订阅 IP 自动更新 — IP 变更时自动修正本地配置（clmi.yaml、jhsub.txt）并通过本地 HTTP 服务 + GitHub 推送分发订阅，适配 Stash 覆写
category: devops
---

# GCP 订阅 IP 自动更新

当 GCP VM 的公网 IP（临时 IP）发生变化时，自动更新所有节点配置并重新分发订阅。

## 架构概览

```
GCP IP 变化
  → 检测触发: cron (每30分钟) + boot systemd service (开机自启)
  → gcp-ip-check.sh 检测到 IP 变更
      ├── cf-update-dns.py → 更新 Cloudflare DNS A 记录
      ├── 更新本地 clmi.yaml / jhsub.txt / jhdy.txt 中的 IP
      ├── push-sub-to-github.py → 生成 override YAML 推送到 GitHub
      └── 重启 subscription-server.service → Stash 立刻拉到最新
```

**核心原则**：Stash 不碰 GitHub，只从本机 HTTP 服务拉取。GitHub 仓库可以设为 private。

## 触发机制

| 方式 | 触发 | 频率 |
|------|------|------|
| cron | `/etc/cron.d/gcp-ip-check` | 每30分钟 |
| boot | `gcp-ip-check-boot.service` (systemd oneshot) | 每次服务器重启 |

IP 没变时静默，变了才执行完整链路。首次运行也会通知。

## IP 变更完整流程

| 文件 | 用途 |
|------|------|
| `/root/.hermes/scripts/gcp-ip-check.sh` | IP 检测入口，cron 每30分钟触发 |
| `/root/.hermes/scripts/push-sub-to-github.py` | 生成 YAML → 推送 GitHub + 写本地副本 |
| `/root/.hermes/scripts/cf-update-dns.py` | Cloudflare DNS A 记录 DDNS 更新 |
| `/root/.hermes/scripts/subscription-server.py` | 本机 HTTP 服务，serve custom-sub.yaml |
| `/root/.hermes/scripts/hermes-skills-backup.py` | Python 脚本 — 分类备份自定义/自带 skill |
| `/etc/systemd/system/subscription-server.service` | HTTP 服务的 systemd 单元 |
| `/root/.github_token.txt` | GitHub PAT（推私有仓库用） |
| `/root/.cloudflare_token.txt` | Cloudflare API Token（DNS:Edit 权限） |
| `/etc/cron.d/gcp-ip-check` | 30 分钟 cron（IP 检测） |
| `/etc/cron.d/hermes-skills-backup` | 每天 10:00 UTC cron（skills 备份） |
| `/etc/s-box/custom-sub.yaml` | Stash 实际拉取的订阅文件（override 格式） |
| `/etc/s-box/clmi.yaml` | 完整 Clash Meta 配置 |
| `/etc/s-box/jhsub.txt` | V2Ray share link 格式订阅 |
| `/root/toolbox/` | 克隆的 toolbox 仓库本地副本 |

## IP 变更完整流程

### gcp-ip-check.sh

```bash
if [ "$CURRENT_IP" != "$LAST_IP" ]; then
    # 更新 IP 记录
    echo "$CURRENT_IP" > /root/.hermes/scripts/.last_public_ip
    echo "$CURRENT_IP" > /etc/s-box/server_ip.log
    echo "$CURRENT_IP" > /etc/s-box/server_ipcl.log

    # 更新本地 clmi.yaml（VLESS 节点 server 字段）
    sed -i "s/server: $LAST_IP/server: $CURRENT_IP/g" /etc/s-box/clmi.yaml

    # 更新本地 jhsub.txt / jhdy.txt（vless:// 链接中的 IP）
    sed -i "s/@$LAST_IP:/@$CURRENT_IP:/g" /etc/s-box/jhsub.txt
    sed -i "s/@$LAST_IP:/@$CURRENT_IP:/g" /etc/s-box/jhdy.txt

    # 更新 DDNS
    /root/.hermes/scripts/cf-update-dns.py

    # 生成订阅文件 + 推送到 GitHub
    /root/.hermes/scripts/push-sub-to-github.py

    # 重启本地订阅服务（Stash 拉取的最新订阅立即可用）
    systemctl restart subscription-server.service || pkill -f subscription-server.py

    # Telegram 通知
    tg_notify "..."
fi
```

### push-sub-to-github.py

- 获取当前公网 IP（GCP metadata → ipify 兜底）
- 生成精简 Clash 格式 YAML（只有 proxies / proxy-groups / rules，不含 port/dns 等）
- PUT 到 `https://api.github.com/repos/CHENHUI-X/sub/contents/custom.yaml`
- 同时写入 `/etc/s-box/custom-sub.yaml`

### subscription-server.service

- Python http.server，绑定 `0.0.0.0:8888`
- 仅响应 `/custom.yaml`、`/clmi.yaml`、`/sub`、`/health`
- 其他路径返回纯文本提示（含订阅地址）
- systemd 管理，自动重启

```ini
[Unit]
Description=Subscription YAML HTTP server for Stash

[Service]
Type=simple
ExecStart=/usr/bin/python3 /root/.hermes/scripts/subscription-server.py 8888
Restart=always
RestartSec=10
```

## Stash（iOS）配置

在 Stash 中添加覆写（Override）：

```
类型: HTTP
URL: http://google.cloud.eosphor.dpdns.org:8888/custom.yaml
更新间隔: 按需
```

仓库 private 不影响此 URL 的正常访问。

## GitHub 仓库设为 Private

操作步骤：
1. GitHub → CHENHUI-X/sub → Settings → Danger Zone → Change visibility → Make private
2. 推送脚本不受影响（token 已有写入权限）

## 手动测试

```bash
# 模拟 IP 变更
echo "1.2.3.4" > /root/.hermes/scripts/.last_public_ip
bash /root/.hermes/scripts/gcp-ip-check.sh

# 直接测试推送（不走 IP 检测）
export GH_TOKEN=$(cat /root/.github_token.txt | tr -d '\n')
python3 /root/.hermes/scripts/push-sub-to-github.py

# 测试 HTTP 服务
curl -s http://localhost:8888/custom.yaml | head -10
curl -s http://google.cloud.eosphor.dpdns.org:8888/custom.yaml | head -5
```

## 安装/重置 HTTP 服务

```bash
# 启动
systemctl enable --now subscription-server.service

# 查看状态
systemctl status subscription-server.service --no-pager

# 重启
systemctl restart subscription-server.service

# 日志
journalctl -u subscription-server.service --no-pager -n 20
```

## 注意

- **systemd 重启问题**：从 Hermes gateway 内部无法 `systemctl restart hermes-gateway`（gateway 会阻止）。需要在 `/etc/cron.d/` 或外部 ssh 里执行。gateway 内部的 `hermes send` 到 QQ 也会超时 — QQ bot 走 WebSocket 需要指定 `qqbot:CHANNEL_ID`，纯 `--to qqbot` 会因为没设 home channel 而失败。
- **`hermes send` 时效性**：发送到 Telegram 不超时，发送到 QQ bot 偶尔会因重连周期超时 60s 才返回，但实际消息已发出
- **IP 变更完整链路**：gcp-ip-check.sh 现在包括 cf-update-dns + push-sub-to-github + subscription-server 重启三件套

- **token 安全问题**：`/root/.github_token.txt` 中的 PAT 涉及写入权限，注意文件权限
- **GitHub PAT auth failure** — when GitHub API returns 401 `Bad credentials` even though the token was correctly generated, the most common causes (in order): (1) token was created for a different GitHub account, (2) fine-grained token permissions didn't include `Contents: Read and write`, (3) token needs SSO authorization. Classic tokens (`ghp_...`) with `repo` scope are more reliable than fine-grained tokens (`github_pat_...`) for automation. To test: `curl -u "username:token" https://api.github.com/user` — if 200 but write returns 404, it's a permission issue.
- clmi.yaml 只有 VLESS 节点的 server 是动态 IP，其他 4 个节点用 DDNS 域名（google.cloud.eosphor.dpdns.org）固定不变
- jhsub.txt 中只有 vless:// 链接包含实际 IP，其他协议用域名
- cron 每 30 分钟跑一次，IP 不变时完全静默
- 服务端口 8888 不对外暴露敏感信息，只有 YAML 文件可下载

## Skills Backup to GitHub

The `hermes-skills-backup.sh` script syncs the entire `~/.hermes/skills/` directory to the `CHENHUI-X/toolbox` GitHub repo. This is a separate pipeline from the subscription push but shares the same GitHub token and cron infrastructure.

### Skills Backup Workflow

Skills are synced to `CHENHUI-X/toolbox` in two directories:
- **custom-skills/** — skills created by the user or agent (not in Hermes bundle)
- **official-skills/** — built-in skills shipped with Hermes

The split is determined by comparing against `.bundled_manifest` in the skills directory.

```bash
# Script: /root/.hermes/scripts/hermes-skills-backup.py (Python, called by .sh wrapper)
# Cron:   /etc/cron.d/hermes-skills-backup (daily at 10:00 CST = 02:00 UTC)

# What it does:
# 1. Reads .bundled_manifest to identify built-in skills
# 2. Clones/pulls toolbox repo to /home/projects/toolbox/
# 3. Copies custom skills → toolbox/custom-skills/ (by category)
# 4. Copies official skills → toolbox/official-skills/ (by category)
# 5. If there are changes, commits and pushes
# 6. If nothing changed, exits silently
```

The cron entry is:
```
0 2 * * * root /root/.hermes/scripts/hermes-skills-backup.sh
```

### Manual Test

```bash
bash /root/.hermes/scripts/hermes-skills-backup.sh
```

### Related Cron Tasks

All cron + systemd one-shot tasks:

| File | Schedule | Purpose |
|------|----------|---------|
| `gcp-ip-check` | Every 30 min | IP change detection + auto-fix |
| `gcp-ip-check-boot.service` | On every reboot | IP check at boot (systemd oneshot) |
| `hermes-skills-backup` | Daily 10:00 CST | Skills → GitHub toolbox |
| `hermes-scripts-backup` | Daily 09:05 CST | Scripts → hermes-scripts repo |
| `hermes-update` | Daily 09:00 CST | Hermes agent version check |
| `sing-box-check` | Daily 08:00 CST | Sing-box health check |

## 参考脚本

- `scripts/subscription-server.py` — HTTP 服务完整实现
