# Skills Backup Workflow (GitHub)

Automatically backup Hermes skills to a GitHub repository, split into two directories:
- `custom-skills/` — agent-created or user-created skills (not in `.bundled_manifest`)
- `official-skills/` — bundled Hermes skills (listed in `.bundled_manifest`)

## When to Set This Up

When the user says: "把 skill 都备份到 GitHub", "起一个任务定期把 skill 推上去", or wants version history of skills.

## Implementation

### Scripts

| File | Role |
|------|------|
| `/root/.hermes/scripts/hermes-skills-backup.py` | Python logic: clone repo, classify skills, copy to `custom-skills/` + `official-skills/`, commit, push |
| `/root/.hermes/scripts/hermes-skills-backup.sh` | Shell wrapper (for cron) |

### Cron

```
/etc/cron.d/hermes-skills-backup
→ 0 2 * * * root /root/.hermes/scripts/hermes-skills-backup.sh
```

Runs daily at **02:00 UTC** (10:00 CST). Silent when no changes — only commits + pushes when skills actually changed.

### How Classification Works

1. Reads `~/.hermes/skills/.bundled_manifest` — a hash list of all Hermes-shipped skill names
2. Iterates all `SKILL.md` files under `~/.hermes/skills/`
3. If skill name is in manifest → `official-skills/`; otherwise → `custom-skills/`
4. Preserves category directories (e.g., `devops/`, `creative/`)

### GitHub Auth

Token stored at `/root/.github_token.txt`. Must be a Classic PAT (`ghp_...`) with `repo` scope for the target repo. Fine-grained PATs may also work but require `Contents: Read and write` on the specific repo.

### Repo Layout After Setup

```
toolbox/
├── custom-skills/
│   ├── devops/gcp-subscription-auto-ip-update/
│   ├── productivity/cross-platform-relay/
│   └── ... (38 skills)
├── official-skills/
│   ├── creative/architecture-diagram/
│   ├── github/github-auth/
│   └── ... (69 skills)
├── AI/
└── README.md
```

## Pitfalls

- **Token auth fails** — Classic PAT (`ghp_`) works; fine-grained PATs need `Contents: Read and write` on the target repo. If Git push says "Invalid username or token" but the token is correct, check repo visibility changes (e.g., switching to private makes `raw.githubusercontent.com` return 404, but API pushes still work).
- **First push is big** — Expect ~500+ files for all skills. Use the API PUT method (not sequential commits) for the initial bulk upload.
- **Script must handle git identity** — Set `git config user.name` and `git config user.email` inside each run; cron runs as root with no default git identity.
- **Rebase vs merge** — Use `git pull --rebase` before push to avoid conflicts when the repo was updated externally.
- **No change → silent exit** — Script checks `git status --porcelain` and exits 0 without committing if nothing changed.
