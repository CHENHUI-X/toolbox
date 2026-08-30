# 部分节点不通诊断：GCP UDP 防火墙 + TLS 证书过期（2026-08-29 实战）

**症状**：用户报"只有 vless 和 anytls 是通的，其他都不通，国内直连"（VMess/Hysteria2/TUIC 挂）。

按序排查，两大根因：

## 根因1：GCP 云防火墙只放行部分 TCP 端口，UDP 全被挡（hy2/tuic 最常见的"永远连不上"）

**关键认知：本机 UFW 放行 ≠ 公网可达。** GCP 云防火墙是独立一层，实例标签只有 `http-server,https-server` 时默认只放 80/443；实测本机放行了 `22/443/2096/33741/29624/9900`（TCP），**UDP 65083/53900 未放行** → Hysteria2/TUIC 无论 UFW 怎么开都连不上。

### 诊断方法（从 VM 内测自身公网 IP 即可）

GCP 的 hairpin 行为：从 VM 内部连自己的公网 IP，**已放行的 TCP 端口能通**（正好利用这个特性当端口探针）：

```python
import socket
pub_ip = "34.3.100.22"   # curl metadata.google.internal/.../external-ip 获取
for port in [22, 80, 443, 2096, 33741, 29624, 65083, 53900, 9900]:
    s = socket.socket(); s.settimeout(3)
    r = s.connect_ex((pub_ip, port))
    print(f"{port}: {'✅ 放行' if r == 0 else '❌ 被GCP防火墙挡'}")
    s.close()
```

TCP 端口测试精确：放行的通、没放行的拒（80/8080/8443 等没放行的一律拒）。

UDP 无法用 connect_ex 测（UDP 无响应可能是协议不回包），**改用 conntrack 确认外部 UDP 是否进来过**：

```bash
cat /proc/net/nf_conntrack | grep -E "udp.*65083"    # 0 条 = 外部 UDP 从未到达 → 云防火墙未放行
```

### 为什么改不了

- 实例默认服务账号 scope 只有 `devstorage.read_only / logging.write / monitoring.write` 等，**无 compute 权限** → VM 内 curl Compute API 加防火墙规则返回 403 insufficientAuthenticationScopes
- gcloud 未安装；`~/.config/gcloud/credentials.db` 存的也只是 GCE 默认账号（无 private_key）
- 必须：GCP Console 手工加规则，或从有权限的机器（WSL 侧 gcloud）执行

### 解法

```bash
# GCP Console / 有权限的 gcloud：
gcloud compute firewall-rules create allow-hy2-tuic-udp \
  --allow udp:65083,udp:53900 \
  --source-ranges 0.0.0.0/0 \
  --target-tags http-server
```

或务实方案：**国内直连场景直接放弃 UDP 节点**——hy2/tuic 走 QUIC/UDP，国内 ISP 本就易丢包，TCP 的 vless/vmess/anytls 已够用。先跟用户确认再决定（用户预算敏感，倾向最小改动）。

## 根因2：TLS 证书过期 → 只有走域名 TLS 校验的节点挂（VMess），Reality/AnyTLS 不受影响

**症状**：VLESS（Reality 伪装 apple.com，不校验真实证书）和 AnyTLS（skip-cert-verify）通；VMess+WS+TLS 不通。

```bash
# 1. 看证书有效期
openssl x509 -in /root/ygkkkca/cert.crt -noout -dates
# notAfter=Aug 23 ... = 已过期（本次事故：8/23 过期，8/29 才修）

# 2. 握手验证（复现客户端错误）
openssl s_client -connect google.cloud.eosphor.dpdns.org:2096 \
  -servername google.cloud.eosphor.dpdns.org -brief
# "verify error:num=10:certificate has expired" = 证书过期
```

### 修复：acme.sh 续期（自动安装到 ygkkkca）

```bash
cd /root/.acme.sh && ./acme.sh --renew -d google.cloud.eosphor.dpdns.org --force
# 输出会显示 "Installing key to: /root/ygkkkca/private.key" / "Installing full chain to: /root/ygkkkca/cert.crt"
systemctl restart sing-box    # 必须重启让 sing-box 加载新证书

# 验证
openssl s_client -connect google.cloud.eosphor.dpdns.org:2096 \
  -servername google.cloud.eosphor.dpdns.org -verify_return_error -brief -tls1_3
# 应看到 "Verification: OK" / "Verified peername: ..."
```

注意 openssl `-brief` 模式有时输出为空，用完整参数（-verify_return_error -verify_hostname -tls1_3）确认。

## 通用规律

- **"部分节点通、部分不通"优先怀疑两层**：① 端口在 GCP 云防火墙层有没有放行（TCP 精确测 / UDP 查 conntrack）；② 走域名 TLS 的节点查证书有效期
- 证书过期只影响校验证书的节点，Reality（伪装站）和不校验的节点照常——这是"部分通"的强信号
- 改完端口/证书后必须重启 sing-box 才生效
- acme.sh 有 crontab 自动续期（`crontab -l` 里 `0 0 * * * acme.sh --cron`），但本次 8/23 过期没续上——排查时如果自动续期失效，先手动 `--renew --force` 救急
