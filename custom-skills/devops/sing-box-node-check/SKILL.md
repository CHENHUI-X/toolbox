---
name: sing-box-node-check
description: "Run checks after any node config change (port/UUID/cert)."
version: 1.0.0
author: Agent
tags: [sing-box, proxy, verification, firewall, udp, gcp]
---

# Sing-box 节点变更后检查钩子（必做清单）

> 每次改节点配置（换端口/换UUID/换密码/换证书/重启服务）后，**必须**跑完整套检查，否则会出现"某个节点静默失效"。

## 触发条件

- 换端口（VLESS/VMess/Hy2/TUIC/AnyTLS 任一）
- 换 UUID / 密码 / Reality 密钥对 / short-id
- 证书续期 / 更换
- 重启 sing-box 或订阅服务
- 订阅文件更新

## 检查清单（按顺序）

### 1. 配置一致性（5 项全对齐）

```bash
# 订阅输出 vs sb.json 对比
SUB=$(curl -s -m 5 "http://127.0.0.1:443/nx4hspzb?key=xch2422")
echo "$SUB" | grep -oE '[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}' | sort -u   # 订阅 UUID
grep -oE '[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}' /etc/s-box/sb.json | sort -u  # 服务器 UUID
```

| 参数 | 位置（订阅文件） | 位置（sb.json） |
|------|-----------------|-----------------|
| VLESS UUID | proxies[0].uuid | inbounds vless users[].uuid |
| VMESS UUID | proxies[1].uuid | inbounds vmess users[].uuid |
| VMESS ws path | `ws-opts.path` | `transport.path` — **⚠️ path 里嵌着 UUID**，换 UUID 必须同步换 path！ |
| TUIC UUID | tuic 块 uuid | inbounds tuic users[].uuid |
| TUIC token | tuic 块 token | inbounds tuic users[].password |
| REALITY public-key | reality-opts.public-key | tls.reality.private_key（用 x25519 推导，见 gcp-operations 技能） |
| REALITY short-id | reality-opts.short-id | tls.reality.short_id[0] |
| hy2 密码 | hysteria2 块 password | inbounds hy2 users[].password |
| anytls 密码 | anytls 块 password | inbounds anytls users[].password |

**坑**：TUIC 同时有 uuid 和 password 两个字段，**两个都要换**！hy2/anytls 只有 password。

### 2. 端口放行检查（换端口后必查！）

三层都要过：

```bash
# ① sing-box 是否在监听
ss -tlnp | grep sing-box   # TCP 节点
ss -ulnp | grep sing-box   # UDP 节点 (hy2/tuic)

# ② UFW 是否放行
ufw status | grep -E "新端口"

# ③ GCP 防火墙是否放行（从外部实测！本机测自己的公网IP不可靠）
# GCP 只放行了特定端口：22/443/2096/33741/29624/9900 (TCP)
# UDP 端口（65083/53900）原本没放行，2026-08-29 用户已创建 allow-udp-proxy 规则
```

**GCP 防火墙规则**（用户侧维护，本机无 compute 权限）：
```powershell
# PowerShell 用户侧执行（注意：逗号加引号，PowerShell 逗号是数组分隔符！）
gcloud compute firewall-rules create allow-udp-proxy --allow "udp:65083,udp:53900" --target-tags http-server
```

**⚠️ Telegram 打码坑**：给用户发含 `0.0.0.0/0` 的命令会被 Telegram 自动打码成 `[IP]/0`！解决方案：
- 不写 `--source-ranges`（gcloud 默认就是 0.0.0.0/0）
- 或让用户用 Cloud Shell / 网页控制台

**⚠️ 换端口流程**：换端口 → sing-box 监听新端口 → `ufw allow 新端口` → **GCP 防火墙也要放行新端口**（用户侧 gcloud 命令）→ 更新订阅 → 重启订阅服务。GCP 防火墙不放行 = 从公网连不上，本机测却通（假象）！

### 3. 证书有效期检查（VMess 必须！）

VMess 用域名 TLS 真证书，**过期就静默失效**（客户端校验失败），VLESS/AnyTLS 不受影响（Reality/自签不校验）：

```bash
openssl x509 -in /root/ygkkkca/cert.crt -noout -dates
# 到期日前 7 天主动续期
cd /root/.acme.sh && ./acme.sh --renew -d google.cloud.eosphor.dpdns.org --force
# 续完必须重启 sing-box 加载新证书！
systemctl restart sing-box
```

### 4. 外部可达性实测（终极验证）

```bash
# TCP 端口：socket connect 到公网 IP
# UDP 端口：发 QUIC 探测包 + 查 conntrack 是否出现外部IP的 [ASSURED] 双向记录
cat /proc/net/nf_conntrack | grep -E "65083|53900"
# [ASSURED] = 双向通信建立 = 真通了！
```

### 5. 订阅服务验证

```bash
systemctl restart subscription-server.service
curl -s "http://127.0.0.1:443/nx4hspzb?key=xch2422" | head -5
# 无密码访问必须 401，带密码必须 200
```

## 已知坑汇总

1. **VMess transport.path 嵌 UUID**：换 UUID 时 path 里的 UUID 不会自动变，必须手动同步（否则 VMess 静默失效）
2. **TUIC 双凭据**：uuid + password 都要换
3. **GCP 防火墙 TCP/UDP 分开**：放行 TCP 不代表 UDP 通
4. **本机测公网IP不可靠**：GCP 不支持 hairpin，本机测自己公网 IP 的结果可能不准；看 conntrack 外部 IP 记录最准
5. **Telegram 打码**：`0.0.0.0/0` → `[IP]/0`，命令里避免裸 IP
6. **PowerShell 逗号**：`--allow "udp:65083,udp:53900"` 必须加引号
7. **证书过期静默**：VMess 独有坑，其他节点不受影响，容易忽略
8. **给用户命令必须单行**：多行会被终端自动执行（用户原话"一行给我 不要换行"）

## 相关技能

- `sing-box-vps` — 节点管理主技能
- `gcp-operations` — GCP 防火墙/凭证操作
- `gcp-subscription-auto-ip-update` — IP 变更自动更新
