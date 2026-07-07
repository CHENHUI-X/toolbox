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
  → cron: gcp-ip-check.sh（每30分钟）
  → cf-update-dns.py 更新 Cloudflare DNS A 记录
  → 更新本地 clmi.yaml / jhsub.txt / jhdy.txt
  → push-sub-to-github.py 生成 override 格式 YAML
      ├── 推送到 GitHub（私有仓库备份/版本管理）
      └── 保存到 /etc/s-box/custom-sub.yaml（本地副本）
          └── subscription-server.service（端口 8888）
              └── Stash 通过域名拉取
```

**核心原则**：Stash 不碰 GitHub，只从本机 HTTP 服务拉取。GitHub 仓库可以设为 private。

## 关键文件

| 文件 | 用途 |
|------|------|
| `/root/.hermes/scripts/gcp-ip-check.sh` | IP 检测入口，cron 每30分钟触发 |
| `/root/.hermes/scripts/push-sub-to-github.py` | 生成 YAML → 推送 GitHub + 写本地副本 |
| `/root/.hermes/scripts/subscription-server.py` | 本机 HTTP 服务，serve custom-sub.yaml |
| `/etc/systemd/system/subscription-server.service` | HTTP 服务的 systemd 单元 |
| `/root/.github_token.txt` | GitHub PAT（推私有仓库用） |
| `/etc/s-box/custom-sub.yaml` | Stash 实际拉取的订阅文件（override 格式） |
| `/etc/s-box/clmi.yaml` | 完整 Clash Meta 配置 |
| `/etc/s-box/jhsub.txt` | V2Ray share link 格式订阅 |
| `/etc/cron.d/gcp-ip-check` | 30分钟定时器 |

## IP 变更时的完整流程

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

    # 推送 GitHub + 更新本地副本
    export GH_TOKEN=$(cat /root/.github_token.txt | tr -d '\n')
    python3 /root/.hermes/scripts/push-sub-to-github.py
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

- **token 安全问题**：`/root/.github_token.txt` 中的 PAT 涉及写入权限，注意文件权限
- clmi.yaml 只有 VLESS 节点的 server 是动态 IP，其他 4 个节点用 DDNS 域名（google.cloud.eosphor.dpdns.org）固定不变
- jhsub.txt 中只有 vless:// 链接包含实际 IP，其他协议用域名
- cron 每 30 分钟跑一次，IP 不变时完全静默
- 服务端口 8888 不对外暴露敏感信息，只有 YAML 文件可下载

## 参考脚本

- `scripts/subscription-server.py` — HTTP 服务完整实现
