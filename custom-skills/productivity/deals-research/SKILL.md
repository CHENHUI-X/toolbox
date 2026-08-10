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

Trigger: user asks for current deals/promos — cheap VPS, overseas SIM / 保号卡, 薅羊毛 — either one-shot ("帮我找找XX优惠") or as the recurring daily digest cron (`6d6f9537521d`, every 9:00 CST).

## Core principles (user-mandated, non-negotiable)

1. **时效性第一 (timeliness)** — Only include items published/updated in the **last ~7 days**. Open the page and check its publish date. Black-Friday / Christmas / CNY promo articles linger in search results for months and are the #1 trap. Vendor official price pages (e.g. `racknerd.com/specials`) are acceptable if they show current pricing.
2. **多源交叉验证 (multi-source cross-verification)** — Every item needs **≥2 INDEPENDENT sources** (vendor official + forum post + independent blog — NOT the same press release re-published). Single-source items: mark "⚠️ 仅单源" or drop.
3. **负面排查 (negative-risk check)** — Before recommending a card/vendor, search `<name> 封号/风控/翻车/跑路`. Recent mass-ban / exit-scam / refund-less wave → mark risk or drop. (Worked case: giffgaff mass-ban 2026 — see `references/sim-card-alternatives.md`.)
4. **不因一次失效就永久拉黑** — a provider that failed once is NOT blacklisted forever; re-verify every cycle. The principle is cross-verification, not permanent exclusion. (User: "不是不再推他了，而是多方面信息交叉验证".)
5. **常识校验 (sanity)** — Absurdly-low prices (50%+ below market) are red flags; coupon codes without official provenance are dropped; marketing-fluff pieces (小红书/百家号 style) need independent corroboration.
6. **宁可少而精** — 3 fresh verified items beat 10 stale ones.

## Output format

- Sections: 📡 VPS / 📱 保号卡 / 🦙 羊毛
- Each item: 名称 → 价格/折扣 → 参与方式 → **购买链接 + 教程链接** (how to buy/activate/keep-alive) → 信息发布日期 → 多源验证状态
- User hates stale promos with no links. Every claim ships with its link.

## Implementation

- Daily digest = Hermes cron job **`6d6f9537521d`** (`0 9 * * *` CST, enabled_toolsets=[web], deliver=origin). Full verified prompt in `references/cron-prompt.md`.
- To change behavior, **update the cron prompt** (cronjob action=update) — never recreate the job blindly.
- One-shot requests: follow the same verification protocol inline.

## Pitfalls

- SERP snippets look "recent" even when the article is months old — ALWAYS open and check the publish date.
- Overseas SIM risk profiles change fast (giffgaff ban was sudden, 12万+ accounts). Re-check for bans before every recommendation cycle; don't trust last month's knowledge.
- Don't call a deal "verified" on a single aggregator post — two independent sources minimum.
- 保号卡 requests mean giffgaff-**style** low-cost keep-alive cards (cheap annual hold, free SMS receive, zero/low monthly) — not necessarily giffgaff itself.

## References

- `references/cron-prompt.md` — the exact verified cron prompt (freshness + cross-validation + negative checks) used by the daily digest
- `references/sim-card-alternatives.md` — giffgaff 2026 mass-ban case study + verified low-cost keep-alive SIM alternatives (HK/US/UK)
