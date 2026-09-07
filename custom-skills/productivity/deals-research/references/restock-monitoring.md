# VPS 库存监控与补货提醒工具

> 用户要"薅羊毛脚本/监控"时的推荐清单 + 商家库存实测方法。第三方服务可能消失，每次推荐前先自测链接可达。

## 现成服务（零部署）

| 服务 | 覆盖 | 通知渠道 |
|---|---|---|
| stock.hostmonit.com | 全球商家库存监控（含 RackNerd 各机房年付款） | TG @hostmonit / QQ群 / Bot @hostmaid_bot |
| stock.vpsknow.com | 商家库存 + LowEndTalk offers 聚合 | TG 频道 t.me/restock_alerts |

## 自建 watcher（抢秒没的特价货）

- **QIN2DIM/racknerd-stock-monitor**（Python, GPL-3.0）：轮询指定 RackNerd 套餐库存，发现补货推 Telegram/Bark/微信。跑在常驻 VPS 上，cron 或 systemd 常驻。
- 与每日人工精选推送互补：监控脚本管**时效**（补货即推），digest 管**筛选**（值不值/有坑没）。

## WHMCS 商家库存实测步骤（推荐前必做）

1. 拉商店列表页，提取产品直链与价格：`href="/index.php?rp=/store/<category>/<slug>"` + `<span class="price">$X USD</span>`。
2. **列表页的 Order Now 按钮不代表有货**——WHMCS 列表页对售罄产品照样渲染下单按钮，且列表页 HTML 里可以 0 个 "out of stock"。
3. 逐款 GET 详情页/直购页（`cart.php?a=add&pid=XX`），grep `out of stock|currently unavailable`：无标记且进入配置/结账步骤 = 真可买；详情页含 Out of Stock = 售罄（即使列表页显示价格 + Order Now）。
4. curl 加 `-L` 跟随重定向；售罄详情页往往仍返回 200 + 完整页面——**看内容，不看状态码**。
5. 价格/规格常为 JS 渲染，静态抓不到时以购物车页能进到配置步骤为准。

## 与每日 digest 的分工

- 每日 9 点 digest（cron 6590a0a5570f）：新鲜 + 多源 + 可购性验证后的精选。
- 监控工具：7×24 补货触发，抢限时秒杀。
