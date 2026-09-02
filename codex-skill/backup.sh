#!/bin/sh
set -eu

script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
repo_root=$(git -C "$script_dir" rev-parse --show-toplevel)
codex_source=${CODEX_SKILLS_DIR:-"$HOME/.codex/skills"}
agent_source=${AGENT_SKILLS_DIR:-"$HOME/.agents/skills"}

git -C "$repo_root" pull --ff-only

mkdir -p "$script_dir/codex" "$script_dir/agents"
rsync -a --delete --exclude-from="$script_dir/backup-exclude.txt" \
  "$codex_source/" "$script_dir/codex/"
rsync -a --delete --exclude-from="$script_dir/backup-exclude.txt" \
  "$agent_source/" "$script_dir/agents/"
cp "$HOME/.codex/AGENTS.md" "$script_dir/AGENTS.md"

if rg -l --hidden \
  --glob '!backup.sh' \
  '(-----BEGIN (RSA |OPENSSH |EC )?PRIVATE KEY-----|AKIA[0-9A-Z]{16}|gh[pousr]_[A-Za-z0-9_]{20,}|sk-(proj|svcacct)-[A-Za-z0-9_-]{20,}|xox[baprs]-[A-Za-z0-9-]{10,}|AIza[0-9A-Za-z_-]{30,})' \
  "$script_dir"; then
  echo 'Backup stopped: possible credential found in the files listed above.' >&2
  exit 1
fi

git -C "$repo_root" add -- codex-skill
if git -C "$repo_root" diff --cached --quiet -- codex-skill; then
  echo 'No Codex skill changes to back up.'
  exit 0
fi

git -C "$repo_root" commit -m "chore(codex-skill): back up local skills"

if [ "${1:-}" = "--push" ]; then
  git -C "$repo_root" push origin HEAD
fi
