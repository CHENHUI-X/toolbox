# IP 地理位置纠错指南（GEO 数据库修正）

场景：VPS 商家广播（Announce）了一个注册地与实际机房不符的 IP 段，导致各大网站/客户端把节点识别成错误国家。用户在意节点显示的国旗/地区，或解锁行为异常。

## 先判断是哪种问题

1. **GEO 数据库记录错误**（本会话案例）：IP 注册国/主流库识别国 ≠ 实际物理机房位置。症状：不同网站/库显示不同国家（ipinfo=PL，ip-api=US，Stash 显示又不同）。
2. **IP 真跳变**：GCP ephemeral IP 停机重启后更换。症状：域名解析结果变了。先 dig 多次确认解析稳定再排除。
3. **Stash fake-ip 显示**：连接记录里 198.18.x.x 是 fake-ip 假地址，每条连接都不同，不是服务器 IP 在跳。

### 实测物理位置（不要信商家宣传）

从已知位置机器测 TCP 握手延迟：俄勒冈→目标 36ms = 美西（波兰应 180ms+）。延迟是唯一不可伪造的证据。

案例：195.72.189.146（AS8796 FASTNET DATA）商家宣传波兰，实测美西洛杉矶。IP 段转运（BGP announce 到异地机房）是行业常见操作。

## 自助纠错渠道（按覆盖面排序）

| 数据库 | 入口 | 门槛 | 生效 |
|--------|------|------|------|
| **MaxMind**（最重要，Stash/大多数服务参考） | https://www.maxmind.com/en/geoip-location-correction | 免费注册+验证邮箱后审核 | 通过后约 1 周 |
| IPLocate | https://www.iplocate.io/corrections | 网页手填（有 reCAPTCHA，程序提交不了） | 数天 |
| IPGeolocation | https://ipgeolocation.io/corrections.html | 纯 JS 表单/或发邮件 support@ipgeolocation.io | 数天 |
| ipinfo | 需企业账号 | 个人提交不了 | — |
| ip-api | http://ip-api.com#contact 邮件 | 慢 | — |

程序提交 MaxMind 的要点（服务端渲染表单，可直接 curl/requests）：
1. GET 页面拿 `csrf_token`（`name="csrf_token"`）+ cookie jar，UA 带真实浏览器头
2. POST 字段：`ip_address, country(US), city(Los Angeles), postal_code, email_address, csrf_token, certification=1, other(理由)`
   - ⚠️ `certification` 复选框的值必须是 **`1`**（表单 HTML 里的 value），传 `on` 会 400
   - ⚠️ `region` 必须留空——它是 JS 联动下拉，初始无选项，硬传 `CA` 会 400
   - 400 时解析响应页里带 `is-invalid` 的字段名定位错误项
3. **成功判定（严格）**：HTTP **201** + 正文含 "Thank you for submitting a geoip location correction. Your request has been submitted"。⚠️ 不要拿页面静态说明文字（如 "verify your email..."）当提交成功证据——表单还在 = 没提交成功；没收到验证邮件 = 基本可断定提交失败，先复查再向用户报告
4. 提交后 MaxMind 发验证邮件到所填邮箱，**必须点验证链接才进审核队列**（邮件可能延迟几分钟到几小时）
5. 洛杉矶参考值：Region California (CA)、City Los Angeles、ZIP 90189、lat 34.0479、lon -118.256、TZ America/Los_Angeles

## 工单文案要素（找商家处理时）

- 说明购买时宣传的国家 vs 实际 GEO 库记录（列具体库名+各自显示）
- 强调"严重影响使用"并列 3-4 条实际影响（AI 服务风控、流媒体分区、注册验证失败）
- 给两个方案：①商家向 GEO 库提交修正 + 更新 WHOIS/RDAP country 字段；②换原生 IP
- 主动提出可提供 traceroute/购买凭证
- 话术：此类问题业内供应商通常 3-5 个工作日修正

## MaxMind 提交后的验证

等 3-7 天后抽查：`curl https://ipinfo.io/<IP>/json`、Stash 节点详情、ip-api.com。多数库跟随 MaxMind 更新。

本会话案例：2026-09-02 为 195.72.189.146 提交 MaxMind（第一次因 certification=on 被 400 拒收却误报成功，用户指出没收到验证邮件后复查发现，修正 certification=1 + region 留空后 201 真正提交成功）+ 需手填 IPLocate；同时给商家发了工单。后续商家直接迁移了 IP 段（195.72.189.146 → 50.114.172.17，上 DDoS 防护线路），新 IP 各库一致判 US（洛杉矶/拉斯维加斯），旧 IP 的 GEO 污染自然消失——工单+迁移双管齐下后问题根治。

教训：向用户报告"提交成功"前必须验证明确成功信号（状态码/官方确认语），否则会被用户用"没收到邮件"当场戳穿。