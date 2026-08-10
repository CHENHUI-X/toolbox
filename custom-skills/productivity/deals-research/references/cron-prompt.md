# Daily Deals Digest — Verified Cron Prompt

Used by Hermes cron job `6d6f9537521d` (every day 09:00 CST, enabled_toolsets=["web"], deliver=origin). This prompt was iterated with the user after real failures: stale Black-Friday articles and the giffgaff mass-ban being recommended as new. Do not simplify the verification rules.

## Prompt body (copy verbatim when updating the job)

```
你今天的工作是搜索全网，整理一份每日特惠/羊毛信息汇总发给我。搜索内容包括：

1. **便宜VPS** — 搜索全球各大VPS商家的促销活动、限量套餐、折扣码。重点关注性价比高的、原生IP的、便宜年付的（RackNerd、InterServer、搬瓦工、丽萨主机、荫云、CloudCone、Netcup等）。也要看看 LowEndBox、hostloc、nodeseek 上有啥新帖。每条信息必须附上**购买/活动链接**，如果有**教程链接**也一起附上。

2. **国外低成本保号手机卡** — 搜索性价比高的国外SIM卡/ESIM，特别是**低成本保号卡**（充值一次保号很久、接码免费、月费极低或零月费）。关注 YouTube 博主和论坛（hostloc、nodeseek、V2EX、奶昔论坛、小红书）最近推荐的：香港卡（游惠宝、haha sim、3HK）、英国卡（VOXI、CTExcel UK、Lycamobile）、美国卡（Ultra Mobile PayGo、Red Pocket）、其他冷门保号卡等。每条必须附上**购买/申请链接**和**教程链接**（教怎么买、怎么激活、怎么保号）。

3. **薅羊毛** — 搜索各类限时活动/免费福利：签到领京豆、免费领会员、云服务免费额度、新用户优惠、限时免费服务、GitHub学生包等。每一条必须写清楚：
   - 📅 **活动时间**（开始/截止）
   - ✅ **参与资格**（新用户/老用户/地区限制等）
   - 📍 **去哪参与**（链接）
   - 📖 **教程链接**（如果有）

⚠️⚠️ **【最重要：多源交叉验证！】**
信息真假和时效性是第一位的，宁可少报、不能错报。每条准备写进报告的信息，都必须经过以下验证流程：

1. **时效性验证**：
   - 今天是 {today}。只收录近7天内发布/更新的信息。
   - 打开页面检查发布日期，超过7天的一律丢弃（黑五/圣诞/春节促销老文章是重灾区）。
   - 商家官网价格页不算过期，但要核对当前在售价格。

2. **多源交叉验证（必须至少2个独立来源）**：
   - 同一个优惠/活动/推荐，必须找到**至少2个互相独立的来源**印证（比如：商家官网 + 论坛帖子 + 博客文章，且论坛/博客不是转载官网同一个文案的）。
   - 只有1个来源、无法交叉印证的，标注"⚠️ 仅单源信息"或直接丢弃。
   - **特别注意搜负面信息**：推荐任何卡/商家前，额外搜一下"XX 封号/风控/翻车/跑路"，发现有近期大规模封号、跑路、维权风波的，直接标记风险或丢弃。

3. **常识校验**：
   - 价格离谱低（明显低于市场价的50%以上）要警惕，可能是钓鱼或过期信息
   - 优惠码没有官方出处的不收
   - 内容看起来像营销软文的（尤其小红书/百家号那种），要有独立来源佐证才收

格式要求：
- 按分类分块：📡 VPS / 📱 保号卡 / 🦙 羊毛
- 每条信息：名称 → 价格/折扣 → 参与方式 → 链接（购买链接+教程链接）
- 每条标注：信息来源发布日期 + 是否多源验证通过
- 验证没通过的别放进来，宁可少而精
- 简洁明了，重点是链接要全、信息要新鲜可靠

搜完后直接把整理好的内容发出来。
```

## Historical evolution (why it looks like this)

1. **v1** — no verification rules. User: "这些内容很多都过期了，你怎么验证？比如那个服务器什么黑5优惠，早他妈没了" → added 7-day freshness + publish-date checks.
2. **v2** — added giffgaff-specific ban note. User: "Giffgaff 都被封了，你看啥呢" → added negative-risk search.
3. **v3 (current)** — user clarified the principle: "不是不再推他了，而是你在搜索的时候，要多方面信息交叉验证" → replaced the giffgaff-only ban note with the general multi-source cross-verification protocol (≥2 independent sources, negative-info search, sanity checks, 宁可少而精).
