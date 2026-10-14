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

`com.chenhui.toolbox-claude-skill-backup.plist` runs this daily through
launchd. Install it with:

```bash
cp launchd/com.chenhui.toolbox-claude-skill-backup.plist ~/Library/LaunchAgents/
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.chenhui.toolbox-claude-skill-backup.plist
```

Logs land in `~/Library/Logs/toolbox-claude-skill-backup.log`.

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
