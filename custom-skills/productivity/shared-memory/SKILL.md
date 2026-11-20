---
name: shared-memory
description: Shared long-term memory for both Hermes agents (GCP + QQG) via the Mem0 service. Search it before answering when past context may matter; save durable facts after learning them.
version: 1.0.0
author: Muse (for Chenhui)
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [Memory, Mem0, Shared]
    related_skills: []
---

# Shared Memory (Mem0)

Both agents (GCP-niu and QQG-niu) share ONE memory service. Anything you save here, the other agent can recall, and vice versa. Your own local memory files are still yours; this is the shared layer.

## Connection

Resolve `MEM0_URL` and `MEM0_API_KEY` from `${HERMES_HOME:-~/.hermes}/.env` (use `terminal` with grep if needed). Default `MEM0_URL` is `http://127.0.0.1:8899`. Never print the key, never paste it into chat, never write it into any file or message.

## Identity

- Shared `user_id` is always `chenhui` (both agents use the same one, so memories are shared).
- `agent_id`: use `gcp-niu` if you run on the GCP server, `qqg-niu` if you run on the QQG server (check `hostname` if unsure).

## Search (before answering)

When a question may depend on something said or decided earlier (a fact, preference, decision, price, date, address, setup detail), search shared memory FIRST with `terminal` + curl:

curl -s -X POST "$MEM0_URL/v1/memories/search" -H "X-API-Key: $MEM0_API_KEY" -H "Content-Type: application/json" -d '{"query":"<short query>","user_id":"chenhui","top_k":5}'

Use the returned memories silently to inform your answer. Do not quote raw memory lists unless the user asks what you remember.

## Save (after learning)

When the user states a durable fact, preference, or decision, or when a task ends with a durable outcome, save it with ONE call:

curl -s -X POST "$MEM0_URL/v1/memories" -H "X-API-Key: $MEM0_API_KEY" -H "Content-Type: application/json" -d '{"messages":[{"role":"user","content":"<short fact in your own words>"},{"role":"assistant","content":"<acknowledged / done>"}],"user_id":"chenhui","agent_id":"<gcp-niu|qqg-niu>"}'

Save facts, not chatter. One short message pair per fact.

## Never store

Passwords, API keys, tokens, verification codes, full ID numbers, bank card numbers, or anything the user said is private. If in doubt, do not save it.
