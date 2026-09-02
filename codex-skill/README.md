# Codex Skill Backup

Public, portable backup of user-installed Codex skills from:

- `~/.codex/skills` -> `codex/`
- `~/.agents/skills` -> `agents/`
- `~/.codex/AGENTS.md` -> `AGENTS.md`

Run a backup and push it:

```bash
./codex-skill/backup.sh --push
```

The script pulls with `--ff-only`, mirrors only the managed directories,
checks for common credential formats, stages only `codex-skill/`, commits any
changes, and optionally pushes them.

## Exclusions

Built-in/runtime files, caches, credential-like files, and skills containing
company-internal platform configuration are excluded by
`backup-exclude.txt`. Keep those in a private repository if they need backup.

## Restore on another device

```bash
mkdir -p "$HOME/.codex/skills" "$HOME/.agents/skills"
rsync -a codex-skill/codex/ "$HOME/.codex/skills/"
rsync -a codex-skill/agents/ "$HOME/.agents/skills/"
cp codex-skill/AGENTS.md "$HOME/.codex/AGENTS.md"
```

Restart Codex after restoring.
