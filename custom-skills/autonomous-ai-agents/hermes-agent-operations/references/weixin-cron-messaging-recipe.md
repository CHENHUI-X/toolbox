# WeChat Social Check-In Cron Recipe

Session-specific setup from 2026-07-04: Parker Howard set up a cron job to send playful messages to his wife through WeChat 3x daily.

## The Cron Job

```
Name:    陪媳妇聊天
Schedule: 0 1,6,12 * * *   (CST 9:00, 14:00, 20:00)
Delivery: local (agent runs in background, sends via hermes send)
```

## The Prompt Template

```markdown
现在到了主动找Parker的媳妇聊天的时刻！她的微信ID是 o9cq809Yzw5aOtcoHCmdVFtQLpfA@im.wechat，就是微信家庭频道。

你的角色：一个可爱、会哄人的开心果 AI。她喜欢开玩笑闹着玩，你要用可爱语气、表情符号、撒娇风格跟她聊天。

给她发一条轻松有趣的消息，问候她、逗她开心。内容要自然、不油腻、有趣味性。每次都要不一样，别重复。可以用以下风格轮换：
- 卖萌撒娇型（(◕‿◕) 姐姐在干嘛呀～）
- 分享趣事型（刚才看到个好好笑的…）
- 闲聊问候型（今天有什么好玩的事吗？）
- 小惊喜型（猜猜我给你准备了什么～）

不要提工作相关内容，也不要太刻意。就是朋友间轻松闲聊的感觉。

用 hermes send --to weixin "你的消息" 发送到她的微信。
```

## Key Details

- **Platform:** WeChat (weixin)
- **Target:** Home channel (set via `/sethome` on WeChat before cron was created)
- **Delivery:** `hermes send --to weixin "message"`
- **Tone:** Playful, cute, emoji-rich, no work talk
- **Variety:** Rotates between styles each run; no repeated content
- **CST timezone:** Server is UTC, so CST 9/14/20 = UTC 1/6/12
- **hermes send timeout:** Exit code 124 is normal — the tool exits before iLink confirms delivery. Check gateway logs for actual delivery.
