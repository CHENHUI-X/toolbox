# Cron Source Investigation — Finding Rogue Scheduled Tasks

When a service restarts unexpectedly at a predictable time but you can't find the source in `/etc/cron.d/`, the root cause may be in the **user crontab** (`crontab -l`), not the system crontab directory.

## The Two Sources of Cron Jobs

| Source | Location | View | Priority |
|--------|----------|------|----------|
| **System crontab** | `/etc/cron.d/<name>` | `ls /etc/cron.d/ && cat /etc/cron.d/*` | Default: Hermes cron migration puts scripts here |
| **User crontab** | `/var/spool/cron/crontabs/<user>` | `crontab -l` (run as that user) | VPS setup scripts (甬哥脚本, BT Panel) often write here |

**Key insight:** Entries in the user crontab do NOT appear in `/etc/cron.d/`. If you only check one, you miss the other.

## Investigation Workflow

### 1. Narrow the restart time

```bash
journalctl -u <service> --since "YYYY-MM-DD HH:MM:SS" --until "YYYY-MM-DD HH:MM:SS" --no-pager
```

### 2. Find what ran at that exact time

The cron daemon logs every command it runs, including the full CMDLINE:

```bash
journalctl -u cron --since "YYYY-MM-DD HH:MM:SS" --until "YYYY-MM-DD HH:MM:SS" --no-pager
```

Look for lines like:
```
CMD (systemctl restart sing-box;rc-service sing-box restart)
```

This alone tells you exactly what command ran — before you've found the cron file.

### 3. Check both cron sources

```bash
# System crontabs
cat /etc/cron.d/* | grep -v "^#" | grep -v "^$"

# User crontabs — run for every user that could have scheduled jobs
crontab -l                 # current user
sudo crontab -l -u root    # explicit root
```

### 4. Check systemd timers (not cron at all)

```bash
systemctl list-timers --all --no-pager
```

### 5. Check anacron (for daily/weekly/monthly jobs on non-24/7 systems)

```bash
cat /etc/anacrontab 2>/dev/null
ls -la /var/spool/anacron/ 2>/dev/null
```

### 6. Remove the rogue entry

```bash
# Remove by pattern
crontab -l | grep -v "systemctl restart sing-box" | crontab -

# Or edit interactively
crontab -e
```

## Real Example

Sing-box restarted daily at 09:00 CST (01:00 UTC).

1. `/etc/cron.d/sing-box-check` only had a health check script — not the restart
2. `journalctl -u cron` at 01:00 UTC showed: `CMD (systemctl restart sing-box;rc-service sing-box restart)`
3. `crontab -l` revealed: `0 1 * * * systemctl restart sing-box;rc-service sing-box restart`
4. Removed with: `crontab -l | grep -v "systemctl restart sing-box" | crontab -`

## Why This Dual Source Exists

- `/etc/cron.d/` — used by system packages, Hermes cron migration, and manual `tee` commands. Requires a user field (6th column).
- `crontab -e` / `crontab -l` — the old-school user-level crontab. Many VPS auto-setup scripts (甬哥 sing-box script, BT Panel, acme.sh) use `crontab -e` directly, bypassing `/etc/cron.d/`.
