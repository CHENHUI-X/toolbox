---
name: cross-platform-relay
description: Operate Hermes as a bidirectional message relay between two messaging platforms (e.g., WeChat ↔ Telegram) with platform-specific behavior modes, roleplay tagging, and proactive cron check-ins.
version: 1.2.0
author: Hermes Agent
tags: [relay, gateway, wechat, telegram, family, messaging, cross-platform]
---

# Cross-Platform Message Relay

Use Hermes as a **pure relay** between two messaging platforms — forward messages between them verbatim without auto-responding to relay content. Supports per-platform behavior modes (work vs. play), roleplay identity tagging, and scheduled proactive check-ins.

## Setup

### Platform Requirements
- Both platforms must be configured and connected via `hermes gateway setup`
- Verify both show as connected: `grep "connected" ~/.hermes/logs/gateway.log`
- Channel directory must be populated: `cat ~/.hermes/channel_directory.json`

### Verify Relay Capability
```bash
# Test send to each platform (use -q for faster delivery)
hermes send -q --to weixin "test message"
hermes send -q --to telegram "test message"
```

## Relay Mechanics

### Core Rule
When user A says something directed at user B — whether as an explicit instruction ("告诉对方xxx", "去给爸爸发条消息") or as a conversational relay ("和妈妈说xxx", "问妈妈xxx", "跟爸爸说xxx") — relay the message to the target platform. **Do not** auto-respond to the relay target or add your own commentary. **Do not** reply to the sender confirming delivery.

### Relay Can Be Initiated From Either Side
Relay is bidirectional — either platform user can initiate:

- **Play platform → Work platform**: "去骂一下你爸爸" → forward to Telegram as 【妈妈传话】
- **Work platform → Play platform**: "和妈妈说爸爸回来了" → forward to WeChat as 【爸爸传话】

Both directions follow the same relay cycle — pure conduit, no agent insertion. The relay pattern is the same regardless of which side initiated.

### Message Tagging
Prefix relayed messages with a clear direction label so recipients know who the message is from:

| Direction | Label |
|-----------|-------|
| Platform A → Platform B | **【A传话】** natural message 😄 |
| Platform B → Platform A | **【B传话】** natural message 😄 |

Example labels: 【妈妈传话】, 【爸爸传话】, 【A传话】, 【B传话】

### Paraphrasing & Flair
Messages do **not** need to be forwarded word-for-word. The user expects natural rephrasing:

- **Rephrase naturally** — "跟妈妈说爸爸回来了" → "妈妈，爸爸说他回来了"
- **Add emojis** to match the tone (😄❤️🍦🎯 etc.)
- **Add flair/戏** — playful embellishment is welcome
- **Do NOT add meta-commentary** — never explain the relay ("he asked me to tell you…", "I'm relaying this from…"), never frame it, never add your own opinion
- **Keep it natural** — relay should read like a normal chat message from the sender, not like a bot report

### Relay Initiation Detection
Relay can be initiated from EITHER platform. These patterns signal a relay request, not casual chat:

- Explicit instructions: "去给爸爸/妈妈/对方发条消息", "告诉爸爸/妈妈/对方xxx", "让爸爸/妈妈/对方去xxx"
- Conversational relays (most common — natural language): "和妈妈说xxx", "跟爸爸说xxx", "问妈妈xxx", "跟妈妈说xxx"
- Any message explicitly mentioning the other party with an action verb (说/告诉/问/发/让)

**Key recognition rule**: When the user on one platform mentions the other platform's person (妈妈/爸爸/对方) with an action verb, it is a relay — even when phrased as casual conversation like "和妈妈说爸爸想她了". Relay immediately. Do NOT reply to the sender first.

### Roleplay Identity Tags

For family roleplay setups, use natural identity labels:

| Direction | Tag Example | Description |
|-----------|-------------|-------------|
| Wife (play) → Husband (work) | 【妈妈传话】natural message | Wife sends to husband |
| Husband (work) → Wife (play) | 【爸爸传话】natural message | Husband sends to wife |

These tags let each side know the message came from the other person, not from the agent. Customize labels to match the family roles (妈妈/爸爸/奶奶/爷爷 etc.). Tag is the first thing in the message so it is immediately visible.

### The Bidirectional Relay Cycle

```plaintext
[Platform A] User: "tell B [message]"
    → Agent: hermes send -q --to B "【A传话】[rephrased message]"
[Platform B] User: replies in their normal chat session with agent
    → Agent: hermes send -q --to A "【B传话】[reply]"
⇄ Repeat — pure conduit, no insertion
```

### The Full 4-Step Cycle (WeChat ↔ Telegram Example)

```plaintext
Step 1: [WeChat 媳妇] "去骂一下你爸爸"
    → Agent forwards to Telegram: hermes send -q --to telegram "【妈妈传话】去骂一下你爸爸"

Step 2: [Telegram Parker] reads it, replies to agent
    → Agent waits for Parker's response message

Step 3: [Telegram Parker] "告诉妈妈我错了，马上去道歉"
    → Agent forwards to WeChat: hermes send -q --to weixin "【爸爸传话】妈妈，我错了，马上去道歉"

Step 4: [WeChat 媳妇] replies → back to Step 1
```

### Relay Direction Detection (Sender → Receiver)

| Sender's phrase pattern | Means | Forward to |
|-------------------------|-------|-----------|
| "和妈妈说xxx", "跟妈妈说xxx", "告诉妈妈xxx" | User wants something said to wife | **Wife's platform** as 【妈妈传话】 |
| "问妈妈xxx" | User asking a question to wife on his behalf | **Wife's platform** as 【妈妈传话】 |
| Wife: "去骂一下爸爸", "去跟爸爸说xxx", "给爸爸发消息" | Wife sending to husband | **Husband's platform** as 【爸爸传话】 |
| "回复他说xxx" | User giving you the response to relay to the other person | **Other person's platform** with their tag |

### Critical: "回复他说xxx" Is a Relay Message, Not a Meta-Instruction

When Parker says "想你回复他说收到了" — this IS the message content to relay. "回复他" means "relay this to the other person." Do NOT interpret it as "I describe what you should do." Forward "收到了" to the wife immediately with the appropriate tag.

Similarly, "就和他说xxx" / "和他说xxx" — relay to the other person with the appropriate tag. The "和他说" / "告诉他" / "回复他" prefix is describing the relay direction, not meta-instruction about your behavior.

### Asking Questions on Behalf of the Sender

"问妈妈xxx" means: pose the question to the wife as if from Parker. Forward as:
- 【妈妈传话】XXX？（加上表情）

## Platform-Specific Behavior Modes

Each platform can have a different personality/behavior mode:

| Mode | Behavior | Use Case |
|------|----------|----------|
| **Work** | Professional, task-focused, minimal banter | Productivity, coding, admin |
| **Play** | Playful, affectionate, jokes, roleplay | Family chat, entertainment |

When a message comes in **that does not involve relay** (e.g., casual chat on the play platform), respond in that platform's mode naturally. Only relay when the user explicitly asks to pass a message to the other side.

## Proactive Check-In (Cron)

For regular proactive messages to a platform (e.g., daily greetings to family), create a cron job:

```bash
# Example: 3x daily at 9am/2pm/8pm CST (UTC+8 → 1/6/12 UTC)
hermes cron create \
  --name "family-checkin" \
  --schedule "0 1,6,12 * * *" \
  --prompt "Send a playful greeting to [platform/recipient]" \
  --deliver local
```

Job prompt should be self-contained: specify platform, recipient ID, tone/style, and to use `hermes send -q` for delivery.

## Security & Approvals

For relay-only traffic (repetitive `hermes send` commands between trusted family channels), disable command approval prompts to avoid friction:

```bash
hermes config set approvals.mode off     # Skip all approval prompts
hermes config set approvals.mode smart   # AI-judged, low-risk auto-approved
```

## Performance

- Use `hermes send -q` (quiet mode) instead of default — returns in ~3s instead of timing out at 15-20s
- Approvals mode `off` eliminates all confirmation dialogs for relay messages
- For maximum speed, disable both approvals and verbose output

## Pitfalls

- **Do NOT auto-reply to relay targets.** When user A says something directed at user B, relay to B. Do not also reply to A about having forwarded it — that pollutes the relay flow.
- **Paraphrase naturally, but don't add commentary.** Rephrase the message in natural language with appropriate emojis. Do not add meta-commentary like "he asked me to tell you" or explanatory framing.
- **Relay mode vs casual mode are separate.** Casual chat on the play platform is fine to respond to naturally. But when the user mentions the other person (妈妈/爸爸) with an action verb, switch to relay mode.
- **Message tagging is critical.** Without labels, recipients cannot tell whether a message is from the agent or relayed from the other person.
- **Conversational relays are easy to miss.** This is the #1 new-user mistake. When the play-platform user says "去骂一下你爸爸" or "能帮妈妈去骂一下爸爸吗", these are relay requests — the agent should forward to the work platform, NOT reply to the sender. The natural instinct is to respond conversationally ("好的妈妈！牛牛去收拾他！"), which is wrong. Recognize the "去+对方/爸爸/妈妈" pattern as a relay signal.
- **iLink Bot accounts** (WeChat iLink) typically cannot join ordinary WeChat groups — group relay may not work regardless of config. This is a Tencent-side limitation.
- **`hermes send` may timeout** waiting for delivery confirmation. The message is usually still delivered — check gateway logs or retry. The `-q` flag reduces timeouts but does not eliminate them entirely. On timeout, simply retry once.
- **Relay detection misses happen.** When learning a new relay setup, the agent may initially treat relay requests as casual chat and respond to the sender instead of forwarding. If the user corrects this, recognize the correction immediately — it is a relay initiation signal, not a conversation.
- **Direction mistakes in relay.** When Parker says "跟妈妈说xxx", the message goes to **WeChat** (wife's platform), NOT back to Parker on Telegram. When the wife says "去骂爸爸", it goes to **Telegram** (Parker's platform). If you send a relayed message to the wrong platform, the recipient is confused and the sender never receives it. Double-check which platform the target person uses before sending.
- **Parker's relay instruction ≠ message to Parker.** When Parker says "告诉妈妈xxx", he is NOT sending a message to YOU — he's telling you to relay to the wife. Your response should be sending to WeChat, not replying to Parker. Similarly, "回复他说收到了" = relay "收到了" to the other person, not report back to Parker.
- **Correction tolerance is zero.** The relay setup pattern confuses most agents on first contact. Expect at least one correction from the user before the pattern sticks. When corrected, acknowledge briefly and update behavior — do not apologize profusely or explain the mistake in detail.
