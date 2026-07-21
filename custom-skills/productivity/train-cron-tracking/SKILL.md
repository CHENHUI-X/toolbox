---
name: train-cron-tracking
description: Set up Hermes cron jobs to proactively report high-speed train station arrivals to the user (e.g., "每到一个站给我报个信")
version: 1.0.0
author: Hermes Agent
tags: [train, tracking, cron, monitoring, transit, schedule, reporting]
---

# Train Cron Tracking

Proactively track a train journey by setting up one-shot Hermes cron jobs at each station's scheduled arrival time. When a family member/friend is on a train and the user wants "每到一个站给我报个信" (notify me at every station), use this pattern.

## Workflow

### 1. Look Up the Train Schedule

Use `web_search` or `web_extract` to find the schedule:

```python
# Search for the train
web_search(query="G3541 高铁 时刻表 途经站点")
web_extract(urls=["https://shike.gaotie.cn/checi.asp?checi=G3541"])
```

Extract: train number, departure→destination, full list of stations with arrival/departure times.

### 2. Check Current Time First

Always check the current system time with `date` BEFORE creating cron jobs — there may be stations that have already passed:

```bash
date '+%Y-%m-%d %H:%M:%S %Z'
```

### 3. Create One-Shot Cron Jobs Per Station

For each upcoming station, create a cron job with `schedule` set to the exact arrival time (ISO format) and `deliver: origin` so the notification comes back to the current chat:

```python
cronjob(
    action='create',
    name='G3541-承德南报站',
    schedule='2026-07-20T14:11:00',  # ISO format, CST
    prompt='妈妈！G3541到承德南站啦～（14:11-14:13）妹妹平安到达承德南！🚄❤️🐮',
    enabled_toolsets=[],  # no tools needed, just deliver the prompt text
)
```

**Key parameters:**
- `schedule`: ISO timestamp in CST (e.g., `'2026-07-20T14:11:00'`)
- `name`: Human-readable, e.g. `TrainNumber-StationToReport`
- `prompt`: Self-contained message that will be delivered verbatim to the user
- `enabled_toolsets: []` — no tools needed for pure text delivery; saves tokens
- No `skills` needed — cron is self-contained with the prompt text
- `repeat` omitted = one-shot (fires once and done)
- `deliver` omitted = auto-deliver to origin chat (the conversation where the cron was created)

### 4. Report Already-Passed Stations

If the current time has already passed one or more stations, report them immediately in the conversation before setting up future cron jobs.

### 5. Handle End-of-Journey

Create a final cron job at the arrival/destination station with a celebratory message to let the user know the trip is complete.

## Pitfalls

- **Time zone must be CST.** The system runs Asia/Shanghai (CST, UTC+8). Cron schedules are interpreted in the system timezone. Always verify with `date` before scheduling.
- **Don't use stale schedule data.** If the user says "现在都13:50了" when you reported 11:45 data, you messed up. Always re-check `date` before reporting status.
- **Schedules are estimates, not real-time.** Train schedules from public websites are planned times, not GPS-tracking. The cron fires at the scheduled time, not when the train actually arrives. If the user wants true real-time tracking, tell them this is schedule-based.
- **One cron per station** — don't batch multiple stations into one cron. Each cron fires independently, so if the train is delayed, the next cron still fires on schedule.
- **Cron prompt must be self-contained.** The cron runs in a fresh session with no conversation context. The prompt text IS the entire message. Write it as a complete message for the user.
- **Passed stations first.** Don't leave the user wondering about stations that already passed while you set up future ones. Report the current location immediately, then set up the remaining stations.
- **Train number confusion.** When a user says "查一下G3541", check the direction. G3541 is Beijing→Hunchun (southbound/northeast-bound). The return schedule will have a different number (e.g., G3542). Double-check before scheduling.
- **Family relationship matters for the message.** "[妈妈的妹妹]" vs "[小姨子]" vs "妹妹" — use the relationship label the user uses. Mom says "妹妹" → use "妹妹". Dad says "小姨子" → use "小姨子". The cron prompt should match the user's terminology.

## Variations

- **Whole-family tracking**: Set up cron jobs AND also relay arrival notifications to the other parent via QQ/Telegram
- **Weather-based delay alerts**: Add a web_search for weather/delays at each station (requires `enabled_toolsets: ["web"]`)
