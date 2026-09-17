---
name: deals-research
description: "Find current deals/promos with freshness + verification."
version: 1.0.0
author: Hermes Agent
metadata:
  hermes:
    tags: [deals, promos, vps, sim-card, verification, timeliness, cron]
---

# Deals & Promo Research

Trigger: user asks for current deals/promos — cheap VPS, overseas SIM / 保号卡, 薅羊毛 — either one-shot ("帮我找找XX优惠") or as the recurring daily digest cron (`6590a0a5570f`, every 9:00 CST).

## Core principles (user-mandated, non-negotiable)

1. **时效性第一 (timeliness)** — Only include items published/updated in the **last ~7 days**. Open the page and check its publish date. Black-Friday / Christmas / CNY promo articles linger in search results for months and are the #1 trap. Vendor official price pages (e.g. `racknerd.com/specials`) are acceptable if they show current pricing.
2. **多源交叉验证 (multi-source cross-verification)** — Every item needs **≥2 INDEPENDENT sources** (vendor official + forum post + independent blog — NOT the same press release re-published). Single-source items: mark "⚠️ 仅单源" or drop.
3. **负面排查 (negative-risk check)** — Before recommending a card/vendor, search `<name> 封号/风控/翻车/跑路`. Recent mass-ban / exit-scam / refund-less wave → mark risk or drop. (Worked case: giffgaff mass-ban 2026 — see `references/sim-card-alternatives.md`.)
4. **不因一次失效就永久拉黑** — a provider that failed once is NOT blacklisted forever; re-verify every cycle. The principle is cross-verification, not permanent exclusion. (User: "不是不再推他了，而是多方面信息交叉验证".)
5. **常识校验 (sanity)** — Absurdly-low prices (50%+ below market) are red flags; coupon codes without official provenance are dropped; marketing-fluff pieces (小红书/百家号 style) need independent corroboration.
6. **宁可少而精** — 3 fresh verified items beat 10 stale ones.
7. **可购性验证 (purchasability)** — A listed price is not a buyable plan. WHMCS-style storefronts render an "Order Now" button on every card even when the product is Out of Stock — the list page shows no stock status at all. Before recommending any plan, open that plan's own detail/cart URL and confirm no "out of stock" marker and that the page reaches the configure/checkout step. Verify per-plan; never trust the list page or secondhand "still available" claims. See `references/restock-monitoring.md`.

## Output format

- Sections: 📡 VPS / 📱 保号卡 / 🦙 羊毛
- Each item: 名称 → 价格/折扣 → 参与方式 → **购买链接 + 教程链接** (how to buy/activate/keep-alive) → 信息发布日期 → 多源验证状态
- User hates stale promos with no links. Every claim ships with its link.

## Implementation

- Daily digest = Hermes cron job **`6590a0a5570f`** (`0 9 * * *` CST, enabled_toolsets=[web], deliver=origin). Full verified prompt in `references/cron-prompt.md`.
- To change behavior, **update the cron prompt** (cronjob action=update) — never recreate the job blindly.
- One-shot requests: follow the same verification protocol inline.

## Pitfalls

- SERP snippets look "recent" even when the article is months old — ALWAYS open and check the publish date.
- Overseas SIM risk profiles change fast (giffgaff ban was sudden, 12万+ accounts). Re-check for bans before every recommendation cycle; don't trust last month's knowledge.
- Don't call a deal "verified" on a single aggregator post — two independent sources minimum.
- 保号卡 requests mean giffgaff-**style** low-cost keep-alive cards (cheap annual hold, free SMS receive, zero/low monthly) — not necessarily giffgaff itself.
- **溯源自证是第一反应，不是辩解**：用户质问"你哪看到的"/"链接不存在"时，先查自己的推送记录（session_search），找到原帖/原链后立刻自测可达性，再把**具体帖子内容直接贴给用户**——链接可能被 TG 吃掉、要登录或地区墙，依赖用户自己打开链接必翻车。同时检查推送缺陷（如只给了论坛首页链接没锚定到帖子）并当场改掉生成规则。
- **对自己的历史输出零记忆≠没发生过**：用户引用几天前推送里的数字（如"$6.99/年"）时，先假设他说的是真的、去查记录，别开口就说"你记岔了"——错误在自己推送里时先认领再修正。

## References

- `references/cron-prompt.md` — the exact verified cron prompt (freshness + cross-validation + negative checks + purchasability checks) used by the daily digest
- `references/restock-monitoring.md` — VPS 库存监控工具（hostmonit / VPSKnow / 自建 RackNerd watcher）+ WHMCS 商家库存实测步骤
- `references/sim-card-alternatives.md` — giffgaff 2026 mass-ban case study + verified low-cost keep-alive SIM alternatives (HK/US/UK)
- `references/saily-keepalive.md` — Saily eSIM 保号价格实况（年套餐仅 APP 内购、$X/年=码后价须注明条件）
- `references/vps-by-region.md` — 分地区 VPS 选品笔记（UK/SG/TR/JP 已验证商家+价格锚点+Offers/WTB 区分）
