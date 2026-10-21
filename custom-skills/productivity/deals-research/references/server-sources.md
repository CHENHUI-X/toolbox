# 服务器/VPS 信息优先源（用户 2026-10-21 指定）

找服务器、VPS、网络、软路由相关信息时，**优先从这些站找**，不要先泛泛搜全网。

## 源清单与可用抓取方式

| 站点 | 定位 | 可用方式（实测） |
|---|---|---|
| v2ex.com | 程序员社区；VPS/服务器/支付/路由 | `curl -A "Mozilla/5.0…" https://www.v2ex.com/go/vps` 、`/go/server`、`/go/cloud`、`/go/router`、`/go/homelab`（HTML 可直抓；`/api/nodes/all.json` 可列节点） |
| nodeseek.com | 主机圈 VPS/独服讨论 + 优惠 | **curl 直拉 403（Cloudflare 人机验证 "Just a moment"）**，需要真浏览器/登录 cookie；浏览器 provider 没 CDP 时抓不到 |
| hostloc.com | 老牌主机论坛，测评+交易 | HTML 可抓，但搜索常被限；DDG `site:hostloc.com` 多为旧帖，需按时间筛 |
| lowendtalk.com | 英文 VPS 促销第一手 | **RSS 最好用**：`https://lowendtalk.com/discussions/feed.rss`（或 `/categories/offers/feed.rss`） |
| linux.do | AI/技术社区，「福利羊毛」区 | **RSS 可用**：`https://linux.do/latest.rss`；`/categories.json`、`/c/<id>.rss` 会 403/301 |
| right.com.cn（恩山） | 路由/软路由/OpenWrt | HTML 直抓但要 **gb18030 解码**（否则乱码）；`/forum/forum-72-1.html` 是固件区 |
| uscardforum.com | 美卡/羊毛 | 需按具体话题再探 |
| 1point3acres.com | 留美华人 DP | 需按具体话题再探 |
| reddit.com/r/churning | 美卡英文源头 | JSON 接口：`https://www.reddit.com/r/churning/top.json?t=week`（带 UA） |
| news.ycombinator.com | 英文科技/AI 新闻源头 | `https://hn.algolia.com/api/v1/search_by_date?tags=story` 或首页 HTML |

## 抓取铁律

1. **先 RSS/JSON，再 HTML，最后才用搜索引擎** —— DDG 后端不稳定（常报 "No results found"），别把失败当"没有信息"。
2. 中文站的 HTML 注意编码（恩山 gb18030）。
3. 报信息必须带**日期 + 链接**；超过 7 天的促销要标注"旧的"。
4. 站点抓不到要**明确说抓不到**（如 NodeSeek 的 CF 验证），不要用别处的二手信息冒充该站内容。

## 2026-10-21 首跑样例（可作格式参考）

- LET：OrangeVPS 10.10 年付 5 折 + 送 vCPU/RAM（10-08）；servers.guru 荷兰 10Gbps 循环 7 折 €38/年、10 月底截止；HostDare 优惠券（10-06）；RackNerd×AdminBolt 抽 100 台免费一年；Netfront AS4658 抽 25 台 $1/年
- V2EX：/go/vps 有 locvps XNNET 香港原生 IP 二手出、vps.gripe 测评档案馆、CloudStorm 云账号；/go/server 讨论甲骨文免费 4+24 停、Vultr Block Storage 扣费坑
- linux.do：10-03 BEROHOST 十周年 €49/年 EPYC 9275F 4C/12GB/120GB NVMe（码 DISCORD10）
- 恩山：11.11 配 AP 特价、BeeconMini SEED AC5S、XG-040G-MD / Cudy TR3600 OpenWrt 固件
