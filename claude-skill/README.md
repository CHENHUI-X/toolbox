# Claude Skill Backup

Public, portable backup of user-installed Claude Code skills from:

- `~/.claude/skills` -> `skills/`

Run a backup and push it:

```bash
./claude-skill/backup.sh --push
```

The script pulls with `--ff-only`, mirrors the skills directory, checks for
common credential formats and internal endpoints, stages only `claude-skill/`,
commits any changes, and optionally pushes them.

Directories listed in `backup-exclude.txt` — including skills that only make
sense against company-internal endpoints — stay out of this public repo. Keep
those in a private repository if they need backup. Symbolic links are skipped.

Network operations try SSH directly with a connection timeout. To enable a
fallback through a local HTTP proxy, configure it once in this clone:

```bash
git config --local claude-skill.proxy 127.0.0.1:7897
```

After a failed direct connection, the script retries GitHub SSH on port 443
through that proxy using `nc` HTTP CONNECT. The proxy setting stays in local
Git configuration and is not backed up. Without it, only direct SSH is used.

## Restore on another device

```bash
mkdir -p "$HOME/.claude/skills"
rsync -a claude-skill/skills/ "$HOME/.claude/skills/"
```

Restart Claude Code after restoring.

## Scheduled backup on macOS

A launchd agent can run this daily. Save the block below as
`~/Library/LaunchAgents/com.chenhui.toolbox-claude-skill-backup.plist`,
replacing `__REPO__` with the absolute path of this clone and `__HOME__`
with your home directory, then load it:

```bash
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.chenhui.toolbox-claude-skill-backup.plist
```

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.chenhui.toolbox-claude-skill-backup</string>
    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>__REPO__/claude-skill/backup.sh</string>
        <string>--push</string>
    </array>
    <key>WorkingDirectory</key>
    <string>__REPO__</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>HOME</key>
        <string>__HOME__</string>
        <key>PATH</key>
        <string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
    </dict>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>10</integer>
        <key>Minute</key>
        <integer>23</integer>
    </dict>
    <key>RunAtLoad</key>
    <false/>
    <key>StandardOutPath</key>
    <string>__HOME__/Library/Logs/toolbox-claude-skill-backup.log</string>
    <key>StandardErrorPath</key>
    <string>__HOME__/Library/Logs/toolbox-claude-skill-backup.log</string>
</dict>
</plist>
```

The explicit `PATH` matters: `rg` is not in launchd's default environment, and
the script refuses to run when its sensitive-information scan cannot execute.

To run it immediately instead of waiting for the schedule:

```bash
launchctl kickstart -p gui/$(id -u)/com.chenhui.toolbox-claude-skill-backup
```

## Multiple devices

Configure the device name once per clone:

```bash
git config --local claude-skill.device mac
# On another machine, use its own device name.
```

Snapshots then use `claude-skill/devices/<device>/skills/`. A device only
mirrors its own snapshot. Clones without a device setting use the top-level
`claude-skill/skills/` layout. The exclusion file remains authoritative, and
the snapshot and exact staged content are scanned. Existing staged changes and
unpushed commits outside `claude-skill/` stop the backup.
