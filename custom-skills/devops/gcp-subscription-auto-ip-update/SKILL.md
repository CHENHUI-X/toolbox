---
name: gcp-subscription-auto-ip-update
description: GCP 订阅 IP 自动更新 — IP 变更时自动更新 DDNS + 重新生成分发订阅（custom-sub.yaml 等）并推送 GitHub，通过本地 HTTP 服务分发，适配 Stash 覆写
category: devops
---

# GCP 订阅 IP 自动更新

当 GCP VM 的公网 IP（临时 IP）发生变化时，自动更新所有节点配置并重新分发订阅。

## 架构概览

```
GCP IP 变化（仅服务器重启时触发，无定期 cron）
  → gcp-ip-check-boot.service (systemd oneshot, after network-online.target)
  → gcp-ip-check.sh 检测到 IP 变更
      ├── cf-update-dns.py "$CURRENT_IP"  → Cloudflare DNS A 记录
      ├── push-sub-to-github.py            → 生成 override YAML 推送到 GitHub
      └── systemctl restart subscription-server.service → Stash 立刻拉到最新
```

**核心原则**：Stash 不碰 GitHub，只从本机 HTTP 服务拉取。GitHub 仓库可以设为 private。

## 触发机制

| 方式 | 触发 | 频率 |
|------|------|------|
| ~~cron~~ | ~~`/etc/cron.d/gcp-ip-check`~~ | ~~每30分钟~~ **已删除**（用户要求仅重启触发） |
| boot | `gcp-ip-check-boot.service` (systemd oneshot) | 仅服务器重启 |

IP 没变时静默，变了才执行完整链路。不再有定期轮询，减少资源占用。

## IP 变更完整流程

| 文件 | 用途 |
|------|------|
| `/root/.hermes/scripts/gcp-ip-check.sh` | IP 检测入口（仅开机由 gcp-ip-check-boot.service 触发） |
| `/root/.hermes/scripts/push-sub-to-github.py` | 生成 YAML → 推送 GitHub + 写本地副本 |
| `/root/.hermes/scripts/cf-update-dns.py` | Cloudflare DNS A 记录 DDNS 更新 |
| `/root/.hermes/scripts/subscription-server.py` | 本机 HTTP 服务，serve custom-sub.yaml |
| `/root/.hermes/scripts/hermes-skills-backup.py` | Python 脚本 — 分类备份自定义/自带 skill |
| `/etc/systemd/system/subscription-server.service` | HTTP 服务的 systemd 单元 |
| `/root/.github_token.txt` | GitHub PAT（推私有仓库用） |
| `/root/.cloudflare_token.txt` | Cloudflare API Token（DNS:Edit 权限） |
| `/etc/cron.d/gcp-ip-check` | 30 分钟 cron（IP 检测） |
| `/etc/cron.d/hermes-skills-backup` | 每天 10:00 UTC cron（skills 备份） |
| `/etc/s-box/custom-sub.yaml` | Stash 实际拉取的订阅文件（override 格式，/nx4hspzb 端点） |
| `/etc/s-box/sub-links-plain.txt` `sub-links-b64.txt` `sub-singbox.json` `sub-surfboard.ini` `merged-sub.yaml` | 订阅服务其余分发文件（全表见 subscription-server.py 的 PATH_MAP） |
| ~~`/etc/s-box/clmi.yaml` `/etc/s-box/jhsub.txt`~~ | **已归档** 2026-09-06 → /root/net-tune/legacy-backup/（含 8-29 旧 Reality 钥，勿再引用） |
| `/root/toolbox/` | 克隆的 toolbox 仓库本地副本 |

## IP 变更完整流程

### gcp-ip-check.sh

```bash
if [ "$CURRENT_IP" != "$LAST_IP" ]; then
    # 更新 IP 记录
    echo "$CURRENT_IP" > /root/.hermes/scripts/.last_public_ip
    echo "$CURRENT_IP" > /etc/s-box/server_ip.log
    echo "$CURRENT_IP" > /etc/s-box/server_ipcl.log

    # ⚠️ 2026-09 起：不再本地 sed clmi.yaml / jhsub.txt / jhdy.txt（均已归档）
    # 节点全部用 DDNS 域名，订阅里不嵌裸 IP，IP 同步只靠下面这步

    # 更新 DDNS — 必须传 IP 参数，否则静默失败！
    /root/.hermes/scripts/cf-update-dns.py "$CURRENT_IP"

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

- Python http.server，绑定 `0.0.0.0:443`（端口由启动参数传入）
- PATH_MAP：/nx4hspzb→custom-sub.yaml、/merged9k2m→merged-sub.yaml、/sub-b64→sub-links-b64.txt、/sub-links→sub-links-plain.txt、/sub-sb→sub-singbox.json、/sub-surf→sub-surfboard.ini
- 密码保护：须 `?key=<sub-key 文件内容>`，否则 401
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

**用户偏好（铁律）：默认只发 Stash 能用的链接，不要一次甩一堆格式。** 用 Stash 就只需两条：

```
主订阅（自建节点）: https://google.cloud.eosphor.dpdns.org/merged9k2m?key=<sub-key>
覆写（默认给这条）: https://google.cloud.eosphor.dpdns.org/override?key=<sub-key>
```

**覆写文件的真实设计（2026-10-14 用户明确，别再自创）：**

- `/override` = **极简补充**：10 个自建节点（名字带「 追加」后缀，与主订阅节点名零重叠，否则 Stash 报“节点名重复”）+ 一个「自建节点」select 策略组（用户手动选） + 仅 PayPal 分流规则（`DOMAIN-SUFFIX,paypal.com` / `paypalobjects.com` / `DOMAIN-KEYWORD,paypal` → 自建节点）。**不要** `#!replace`（主力订阅自带规则必须原样保留），也**不要**塞 33 规则集 / 37 条分流 / 4 个主策略组——用户明确说用不到。
- **覆写只有 `/override` 一条（唯一正确，用户 2026-10-14 明确）**：其他 `.stoverride` 文件（`/qqg-attach.stoverride`、`/qqg-rules.stoverride`、`/qqg-rules-pure.stoverride`、`/override-min`）**内容/设计都是错的，不要再发、不要再新做**。用户原话："覆写规则就要这一个，其他的全是错的"。
- **443 卡死排查（2026-10-15 实例）**：症状 = 订阅链接 curl 超时（连 127.0.0.1:443 也超时），但 8080 正常、服务 status 显示 active。诊断看 `ss -tlnp | grep :443` 的 **Recv-Q**：非 0（如 6）即 accept 队列积压 = 前端卡死不接新连接。根因 = `sub-tls-proxy.py` 对**监听 socket** 做 `ctx.wrap_socket()`，TLS 握手落在 accept 主循环，一个只连不握手的扫描器就能堵死整端口。正确写法：监听 socket 不包 TLS，在 handler 的 `setup()` 里对已接受的连接 `wrap_socket`（握手在子线程）；Server 类设 `daemon_threads=True`、`request_queue_size=128`，handler 设 `timeout=10`。回归测试 = 挂 3 条只连不握手的连接，正常请求仍应 <100ms。
- **入口契约（2026-10-16 收敛后，两机一致）**：只保留两个入口 —— `/merged9k2m`（merged-sub.yaml）+ `/override`（override-stash.yaml）；两机 `/etc/s-box/sub-key` 同一个值；其余路径（raw/rawtxt/sub-b64/sub-links/sub-sb/sub-surf/nx4hspzb/wechat-fix/convert）与根路径一律 **404**（FILE_PATH 兜底已删）。别再加新别名；内部脚本要拉订阅就直接走 `http://127.0.0.1:8080/merged9k2m?key=<sub-key>`。
- **两机订阅必须“同一套”（2026-10-16 统一）**：同一个 sub-key（`/etc/s-box/sub-key`，GCP/QQG 一致）+ 同一份内容（`merged-sub.yaml`、`override-stash.yaml` 两机逐字节一致）。改内容时用 scp 推到对端并 `md5sum` 对账（两侧各拉一次比 md5），别只改一台。canonical 内容 = 含 Wechat 直连规则 + 广告规则 REJECT 的那份。
- **改完覆写/订阅文件必须先用 YAML 严格校验再上线**：`/usr/bin/python3 -c "import yaml;d=yaml.safe_load(open('/etc/s-box/override-stash.yaml'));print(list(d.keys()))"`（系统 python3 在 `/usr/lib/python3/dist-packages` 下有 PyYAML；Hermes venv 外的 python3 没装）。2026-10-14 就是因为拼接时漏掉 `proxies:` 键头，第 5 行出现孤立 `- name:`，Stash 报"覆写格式不正确"。校验通过后还要 `curl -sS` 拉一次端点确认 200 且内容对。
- 新需求先问清：覆写的职责只有「自建节点（后缀名）+ 一个手动选的「自建节点」策略组 + 指定分流」，不要自作主张加规则集/主策略组/`#!replace`。
- **覆写现有分流（2026-10-16 定稿）**：只保留 **PayPal 3 条**（paypal.com / paypalobjects.com / 关键词 paypal）+ **Talkatone 33 条**（来源：github.com/carlleilzj/Talkatone_Rules 的 Clash 分流表 —— talkatone.com / talkamobile.com / tktn.at / tktn.be、各 talkatone 子域、tenor、20 个通话 IP 段，`no-resolve` 原样保留）+ **广告拦截 32 条 → REJECT**（同一个库的 Talkatone_Ads 表，放在 Talkatone 分流之前，顺序照 README：广告在分流上面）。Claude/Anthropic 那批已按用户要求撤回；用户原话：只覆盖“他自己相关的”，不相关的一律不走自建（npm/github/storage 永不加，除非用户点名）。
- 改动前的背景：起因是主订阅与覆写节点名完全重叠（各自 10 个同名节点），Stash 报“节点名重复”→ 给覆写的节点统一加后缀解决。

`sub-b64`（小火箭/v2rayN）、`sub-sb`（sing-box）、`sub-surf`（Surfboard）、`raw`/`rawtxt`、`qqg-*.stoverride` 只在明确要对应客户端或调试时才发。

### 域名与 TLS（2026-10-14 起）

- **443 是 HTTPS/TLS**：`sub-tls-proxy.py` 终止 TLS → 转发 `127.0.0.1:8080`（`subscription-server.service`）；80 仍是明文 `subscription-server-80.service`。客户端必须用 `https://`，老的 `http://…:443` 会被 RST。
- **证书 SAN**：`google.cloud.eosphor.dpdns.org` + `gcp.eosphor.dpdns.org`（两个域名都可用，旧帖子里只写 SAN 里的那个名）。
- **签发/续期**：acme.sh + **DNS-01（dns_cf，token 在 `/root/.cloudflare_token.txt`）**，证书在 `/root/.acme.sh/google.cloud.eosphor.dpdns.org_ecc/`（含 SAN，lease 至 2027-01；每天 00:00 `~/.acme.sh/acme.sh --cron -f` 自动续）。
- 加域名：`CF_Token=$(cat /root/.cloudflare_token.txt) acme.sh --issue --dns dns_cf -d google.cloud.eosphor.dpdns.org -d <新域名> --keylength ec-256`（保持第一个 `-d` 不变，证书路径才不会变），然后 `systemctl restart sub-tls-proxy.service` 生效。
- **验证**：`openssl s_client -connect <IP>:443 -servername <域名>` 看 SAN；再用**不带 `-k` 的** `curl` 拉一次订阅（严格校验，`gcp.*` 上次就是这样暴露证书不匹配的）。

IP 判断/DDNS 变更流程不受影响；本机 IP 不变时静默。

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
K=$(cat /etc/s-box/sub-key)
curl -s "http://localhost:443/nx4hspzb?key=$K" | head -10
curl -s "http://google.cloud.eosphor.dpdns.org:443/nx4hspzb?key=$K" | head -5
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

## 相关技能

此技能已将大部分内容整合到 `devops/gcp-operations`（GCP 运维总览技能）。本技能保留作为 IP 自动更新的具体实现参考，但新变更请优先更新 gcp-operations。

- `devops/gcp-operations` — GCP VM 运维总览（含 IP 检测、DDNS、订阅更新、内存优化）
- `devops/sing-box-vps` — 代理服务管理
- `devops/system-cron-setup` — 系统 crontab 管理

## 注意

- **cf-update-dns.py 必须传 IP 参数**：`/root/.hermes/scripts/cf-update-dns.py "$CURRENT_IP"`，不传就是静默失败！**这是此前DDNS没自动更新的根因**。
- **cf-update-dns.py 要有执行权限**：`chmod +x`，否则开机启动时调不了。
- **subscription-server 必须用 systemd 管理**（带 `Restart=always`），裸进程会被 `pkill` 杀掉再起不来。已创建 `/etc/systemd/system/subscription-server.service`。
- **curl 要加超时**：开机时网络可能没完全就绪，不加 `--connect-timeout 5 --max-time 10` 可能卡死。
- **依赖检查**：调用 cf-update-dns.py 和 push-sub-to-github.py 前检查 `[ -x ]`，脚本不存在或不可执行时要有日志兜底，而不是静默失败。
- ~~**每30分钟 cron 已删除**~~（用户要求仅重启触发，GCP 临时 IP 只在停机/重启时变）
- **systemd 重启问题**：从 Hermes gateway 内部无法 `systemctl restart hermes-gateway`（gateway 会阻止）。需要在 `/etc/cron.d/` 或外部 ssh 里执行。gateway 内部的 `hermes send` 到 QQ 也会超时 — QQ bot 走 WebSocket 需要指定 `qqbot:CHANNEL_ID`，纯 `--to qqbot` 会因为没设 home channel 而失败。
- **`hermes send` 时效性**：发送到 Telegram 不超时，发送到 QQ bot 偶尔会因重连周期超时 60s 才返回，但实际消息已发出

- **token 安全问题**：`/root/.github_token.txt` 中的 PAT 涉及写入权限，注意文件权限
- **GitHub PAT auth failure** — when GitHub API returns 401 `Bad credentials` even though the token was correctly generated, the most common causes (in order): (1) token was created for a different GitHub account, (2) fine-grained token permissions didn't include `Contents: Read and write`, (3) token needs SSO authorization. Classic tokens (`ghp_...`) with `repo` scope are more reliable than fine-grained tokens (`github_pat_...`) for automation. To test: `curl -u "username:token" https://api.github.com/user` — if 200 but write returns 404, it's a permission issue.
- 2026-09-06 大扫除：clmi.yaml / jhsub.txt / jhdy.txt / sbox.json / vl_reality.txt / an.txt / hy2.txt / tuic5.txt / vm_ws_tls.txt 及各自 .bak 已归档至 /root/net-tune/legacy-backup/。原因：8-29 旧 Reality 钥（pbk=DO1zSn.../sid=0d682811）和过期凭据，真值以 sb.json 为准（pbk=UHnerZD.../sid=e03f8182，由私钥 X25519 推导验证）
- 当前节点全部用 DDNS 域名（google.cloud.eosphor.dpdns.org），订阅里不嵌裸 IP
- cron 每 30 分钟已删除，仅开机触发；IP 不变时完全静默
- 服务端口 443 = HTTPS(TLS 前端)，80 = 明文，`?key=` 鉴权，无 key 一律 401；探测/监控必须用 `https -k`（或接受 401），用明文 http 打 443 会被 RST —— QQG 的 gcp-monitor.sh 就因此误报过"GCP 失联"

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
