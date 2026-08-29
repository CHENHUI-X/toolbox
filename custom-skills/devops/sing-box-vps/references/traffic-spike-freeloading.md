# 检测节点被蹭流量（订阅泄露诊断）

**症状：** 用户问"今天流量怎么这么高"，vnstat 显示当天流量是平时的 10-30 倍，且入站≈出站（典型的代理转发特征）。

## 诊断步骤

```bash
# 1. 看日流量，确认异常
vnstat -d | tail -5
# 平时 ~200MB/天，异常日可能 5GB+（28倍）

# 2. 看小时分布，定位爆发时段（关键线索：凌晨/深夜大流量 = 别人在用）
vnstat -h --limit 30
# 例：02:00 单小时 5.10 GiB（入2.47G+出2.63G）→ 不是用户自己翻墙

# 3. 确认不是网关/备份脚本干的（先排除自身）
# 查网关日志该时段：grep "2026-08-29 0[12]:" ~/.hermes/logs/gateway.log
# 查 cron：cat /etc/cron.d/* （备份脚本都是小文件，不可能产生 GB 级流量）

# 4. 🔑 查 sing-box 的 inbound 连接来源 —— 蹭流量的铁证
# ⚠️ journalctl -u sing-box 可能为空或卡死（journal 2.9G 时 --since 查询超时）
#     sing-box 日志实际写到 /var/log/syslog！
grep "2026-08-29T0[12]:" /var/log/syslog | grep sing-box
```

```python
# 5. 提取 inbound 连接来源 IP，统计分布
import subprocess, re
from collections import Counter
r = subprocess.run(["grep", "-E", "2026-08-29T0[0-3]:", "/var/log/syslog"],
    capture_output=True, text=True, timeout=25)
lines = [l for l in r.stdout.split('\n') if 'sing-box' in l]
ips = Counter()
for l in lines:
    if 'inbound/vless' in l or 'inbound/vmess' in l:
        for ip in re.findall(r'(\d+\.\d+\.\d+\.\d+)', l):
            if not ip.startswith(('10.138', '127.', '169.254')):
                ips[ip] += 1
print(f"共 {sum(ips.values())} 条连接，来自 {len(ips)} 个不同IP")
for ip, cnt in ips.most_common(10):
    print(f"  {ip}: {cnt}次")
```

## 判定标准

| 证据 | 结论 |
|------|------|
| 深夜（0-3点）大流量 + 入≈出 | 代理转发特征，不是用户自己 |
| **多个不同来源 IP**（13+ 个，分布各省） | **订阅链接被分享/泄露**，别人拿节点当免费代理 |
| 单一 IP 大量连接 | 可能是个别用户（朋友）或攻击者 |

## 后果与处理

- 蹭流流量全算在 VPS 账单上（GCP 中国方向 $0.23/GB Premium），一天可烧 $1+，一个月 $30+
- 处理选项：① 换 UUID/凭据（最彻底，见 SKILL.md「凭据轮换」节）；② 换订阅链接路径/加鉴权；③ 先观察是否一次性
- ⚠️ 用户对改 UUID 敏感（"悠悠ID别动"）——先报告证据和选项，**经确认后再动手**
- 蹭流会复发（实测 7 月被蹭 1100GB，8 月又来）——发现一次就建议彻底轮换

## 实测案例（2026-08-29）

- 当天流量 5.76 GiB（平时 ~200MB，28 倍）
- 凌晨 02:00 单小时 5.10 GiB（入 2.47G + 出 2.63G）
- syslog 提取到凌晨 0-3 点 13 个不同来源 IP、376 条代理连接
- 来源分布河南/山东/湖北/吉林等多省 → 判定订阅链接泄露
- 网关日志（QQBot 每 30 分钟正常重连）和备份 cron（git 小文件）均可排除
