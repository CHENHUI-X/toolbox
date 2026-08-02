---
name: wechat-moments-copywriting
description: Write humorous 段子-style WeChat Moments promo copy.
version: 1.0.0
author: Hermes Agent
tags: [copywriting, wechat, moments, marketing, chinese, 朋友圈, 文案]
---

# WeChat Moments (朋友圈) Promo Copywriting

The user (妈妈) frequently asks for 朋友圈宣传文案 for products/services (e.g. 易盘点固定资产管理系统). This skill captures the recurring style preferences and format expectations so a fresh session starts already knowing the house style.

## User Style Preferences (non-negotiable, repeated 3× in one session)

1. **诙谐幽默 / 段子类型 (joke/story format)** — the copy MUST be funny, story-driven, playful. Plain feature-lists or sales-speak get rejected.
2. **不要太功利化 (low sales pressure)** — do NOT lead with pricing, "立即购买", "限时优惠", or hard-selling. The humor IS the hook; the product mention lands softly at the end.
3. **Story/skit structure works best** — a short office scenario with dialogue (行政小妹/财务大姐/领导 + 主角), a twist ("扫一下 → 全部真相"), and a punchline. 段子 = mini-skit with a payoff.
4. **Tech products should feel like a reveal** — the pattern "同事质疑 → 掏出手机扫码 → 系统秒出答案 → 对方沉默/震惊" is the proven winner for 易盘点.
5. **Emoji usage is expected and welcome** (📱✅📋😂🔥 etc.), woven into the story, not tacked on.
6. **Hashtags at the end** (#易盘点 #固定资产管理 #打工人必备 etc.) — 2-4 relevant tags, keep them light.

## Proven Format Template (story/skit style)

```
[Opening hook — a colleague/leader says something skeptical or funny]
[主角's deadpan response / action]
[Twist — scan/quick action reveals the answer]
[Beat — the other person's reaction (silence, shock, "？？？")]
[Punchline — soft product mention + why it matters]
[1-2 closing emoji lines]

#tag1 #tag2 #tag3
```

## Deliverable Conventions

- Offer **2+ variants** per request (e.g. a longer story-skit + a short/snappy version). The user picks.
- After they pick, offer to 润色 (polish) and optionally generate a matching image (square 1:1 for 朋友圈).
- **Image delivery caveat:** WeChat cannot render image URLs or `MEDIA:` paths inline — if a配图 is requested, upload to a host and send a direct link (see `cross-platform-relay` skill, `references/wechat-file-delivery.md`). Confirm receipt before assuming success.
- Keep the product name intact (易盘点) and never invent features the product doesn't have.

## Pitfalls

- **Do NOT make it salesy.** "性价比高", "限时折扣", "买它" style copy is the #1 rejection reason. If unsure, lean MORE humorous, LESS promotional.
- **Do NOT skip the humor for "professional" tone.** 专业腔 = flat = rejected. The user explicitly wants 诙谐/段子 every time.
- **Variant count matters.** Delivering only one option invites a "再来一个" follow-up; deliver 2-3 upfront.
- **Subject consistency**: in dialogue skits, keep speaker names/roles straight (财务部小姐姐, 行政部小妹, 领导). Mismatches break the joke.
