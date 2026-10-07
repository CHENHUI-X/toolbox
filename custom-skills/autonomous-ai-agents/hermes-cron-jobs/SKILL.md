---
name: hermes-cron-jobs
description: "Use when Hermes cron jobs need model or run verification."
version: 1.0.0
author: Hermes Agent
license: MIT
tags: [hermes, cron, scheduler, model, verification, jobs]
metadata:
  hermes:
    tags: [hermes, cron, scheduler, model, verification, jobs]
    related_skills: [system-cron-setup, hermes-peer-networking]
---

# Hermes Internal Cron Jobs

The scheduler that lives inside the gateway — NOT system crontab (that is `system-cron-setup`). Use this when a job's model or behaviour is wrong, when asked "what model do the scheduled jobs run on", or before reporting that a change to a job took effect.

## When to Use

- A cron job's model, schedule or output looks wrong, or the user asks which model the scheduled jobs run on
- You are about to change something a job depends on (model, config, credentials) and must show the change actually reached the run
- A job must keep running while the gateway is down → that is `system-cron-setup`, not this skill

## Where Things Are

| Path | What |
|---|---|
| `~/.hermes/cron/jobs.json` | Job definitions: `model`, `provider`, `script`, `no_agent`, `deliver`, `origin`, `enabled`, `schedule`, `next_run_at`, `reasoning_effort`, `enabled_toolsets` |
| `~/.hermes/cron/executions.db` | Durable attempt records (`executions`, `cron_incidents`) — status/timing only, no model |
| `~/.hermes/cron/deliveries.db`, `~/.hermes/cron/output/` | What each run delivered |
| `~/.hermes/cron/usage_audit.jsonl` | Per-run `model` actually used |
| `~/.hermes/state.db` → `sessions` | The run's session row: `model`, `model_config`, `message_count`, `started_at` (`source='cron'`) |

CLI: `hermes cron {list,create,add,edit,pause,resume,run,status,runs,incidents,notepad,doctor,tick}`. `edit` takes `--model <name> [--pin|--unpin] --provider <p> --reasoning-effort <lvl>`; `doctor` reports common job health problems.

## Which Model a Run Uses

Resolution order, re-read on **every scheduler tick** (nothing is cached):

```
per-job pin (job.model)  >  HERMES_MODEL (env of the gateway process)  >  cron.model (fleet default in config.yaml)  >  model.default
```

- `hermes config set cron.model <name>` moves every unpinned job **from the next run on — no gateway restart**.
- A job with `model: None` silently follows whatever the main model is **that day**. A session row or `usage_audit.jsonl` line showing another model is history, not evidence of a pin — check `jobs.json` for the actual pin before explaining it.
- Set `cron.model` (or a per-job `--model`) when cron must not drift with the main model; leave it unset when cron should track the main model.
- Jobs with `no_agent: true` + `script: <file>.py` never touch a model at all — they deliver the script's stdout. Check these two fields before saying anything about a job's model.

## Verifying a Job Actually Runs as Intended

Never report a config write as "done, it will use X" without a run you can point at. Trigger one and read the row:

```bash
hermes cron run <job_id>          # schedules it for the next tick
sleep 150                         # one scheduler tick + session start
python3 -c "import sqlite3,datetime; c=sqlite3.connect('/root/.hermes/state.db'); [print(datetime.datetime.fromtimestamp(float(s)), m, i) for i,m,s in c.execute(\"select id,model,started_at from sessions where source='cron' order by started_at desc limit 3\")]"
```

The session row is written **at session start** with the resolved model, so the model is confirmed without waiting for the whole run (a long agent job keeps running and delivers on its own).

Caveats before trusting a row: `~/.hermes/sessions.db` is empty — the session store is `state.db`; and a job's `next_run_at` offset shows which timezone the schedule is interpreted in (do not assume UTC).

## Pitfalls

- **`model: None` is not "no model"** — it means "follow the main model at run time". Audit rows from days ago reflect the model of those days.
- **Changing a job's model needs no gateway restart; changing the gateway's own config may.** The scheduler re-reads `config.yaml` per tick, so `cron.model` lands immediately, while `HERMES_MODEL` comes from the gateway process env and only changes with a gateway restart. Because `HERMES_MODEL` outranks `cron.model`, check `tr '\0' '\n' < /proc/$(pgrep -f 'hermes_cli.main gateway run' | head -1)/environ | grep HERMES_MODEL` before promising a fleet-wide change.
- **Config writes only through the CLI.** `patch`/`write_file` refuse `~/.hermes/config.yaml` and `/etc/*`. Use `hermes config set <key> <value>`, read back with `hermes config get <section>` (one section per call, bare `a.b c.d` errors), and confirm no duplicated top-level key: `config set` has appended into the wrong section before.
- **A job that shells out to the gateway's own lifecycle is blocked** while the gateway supervises it (the outside-the-tree executor workaround lives in `hermes-peer-networking`).
- **Manual runs deliver.** `hermes cron run` is a real run: it spends tokens, does its web searches and posts its output to the job's `deliver` target. Warn the user that an out-of-schedule message is coming, or expect them to ask what it was.
- **Paused jobs keep a stale `next_run_at`** in the past; that is not a fault.

## Related Skills

- `system-cron-setup` — system crontab / `/etc/cron.d` for jobs that must outlive the gateway
- `hermes-peer-networking` — restarting a gateway from inside a supervised gateway
