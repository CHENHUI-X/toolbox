#!/usr/bin/env bash
set -euo pipefail
script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
repo_root=$(git -C "$script_dir" rev-parse --show-toplevel)
codex_source=${CODEX_SKILLS_DIR:-"$HOME/.codex/skills"}
agent_source=${AGENT_SKILLS_DIR:-"$HOME/.agents/skills"}
device=${BACKUP_DEVICE:-$(git -C "$repo_root" config --get codex-skill.device || true)}
snapshot=$script_dir
if [[ -n "$device" ]]; then
  [[ "$device" =~ ^[a-z0-9][a-z0-9._-]{0,63}$ ]] || { echo 'Invalid backup device name.' >&2; exit 1; }
  snapshot="$script_dir/devices/$device"
fi
[[ "$snapshot" == "$script_dir" || ! -L "$script_dir/devices" ]] || { echo 'Snapshot parent must not be a symbolic link.' >&2; exit 1; }
[[ ! -L "$snapshot" && ! -L "$snapshot/codex" && ! -L "$snapshot/agents" ]] || { echo 'Snapshot paths must not be symbolic links.' >&2; exit 1; }
[[ -d "$codex_source" && -d "$agent_source" && -f "$HOME/.codex/AGENTS.md" ]] || { echo 'Missing skills directory or AGENTS.md.' >&2; exit 1; }
[[ $(git -C "$repo_root" branch --show-current) == main ]] || { echo 'Backup requires main.' >&2; exit 1; }
git -C "$repo_root" diff --cached --quiet || { echo 'Backup stopped: existing staged changes must be reviewed first.' >&2; exit 1; }
git -C "$repo_root" pull --ff-only

mkdir -p "$snapshot/codex" "$snapshot/agents"
rsync -a --no-links --delete --delete-excluded --exclude-from="$script_dir/backup-exclude.txt" "$codex_source/" "$snapshot/codex/"
rsync -a --no-links --delete --delete-excluded --exclude-from="$script_dir/backup-exclude.txt" "$agent_source/" "$snapshot/agents/"
cp "$HOME/.codex/AGENTS.md" "$snapshot/AGENTS.md"

credential_re='(-----BEGIN (RSA |OPENSSH |EC |DSA |ENCRYPTED )?PRIVATE KEY-----|(?:AKIA|ASIA)[0-9A-Z]{16}|gh[pousr]_[A-Za-z0-9_]{20,}|github_pat_[A-Za-z0-9_]{20,}|sk-[A-Za-z0-9_-]{40,}|xox[baprs]-[A-Za-z0-9-]{10,}|AIza[0-9A-Za-z_-]{30,}|didichuxing\.com|xiaojukeji\.com)'
scan() {
  if rg --quiet --text --hidden "$credential_re" "$@"; then
    echo 'Backup stopped: possible credential or internal endpoint found; matching content withheld.' >&2
    git -C "$repo_root" reset --quiet HEAD -- codex-skill/
    exit 1
  else
    rc=$?
    [[ $rc == 1 ]] || { echo 'Backup stopped: sensitive-information scan failed.' >&2; exit 1; }
  fi
}
scan "$snapshot/codex" "$snapshot/agents" "$snapshot/AGENTS.md"
git -C "$repo_root" add -- codex-skill/
git_dir=$(git -C "$repo_root" rev-parse --absolute-git-dir)
scan_file=$(mktemp "$git_dir/codex-skill-scan.XXXXXX")
trap 'rm -f "$scan_file"' EXIT
while IFS= read -r -d '' file; do
  [[ "$file" == codex-skill/* ]] || { echo 'Commit stopped: staged files outside codex-skill/.' >&2; exit 1; }
  git -C "$repo_root" show ":$file" >> "$scan_file"
  printf '\n' >> "$scan_file"
done < <(git -C "$repo_root" diff --cached --name-only --diff-filter=ACMRTUXB -z)
scan "$scan_file"

created=no
if ! git -C "$repo_root" diff --cached --quiet -- codex-skill/; then
  git -C "$repo_root" -c core.hooksPath=/dev/null commit -m "chore(codex-skill): back up ${device:-local} skills"
  created=yes
fi
echo "Commit created: $created; HEAD: $(git -C "$repo_root" rev-parse HEAD)"
if [[ ${1:-} == --push ]]; then
  git -C "$repo_root" pull --ff-only
  for revision in $(git -C "$repo_root" rev-list origin/main..HEAD); do
    while IFS= read -r -d '' file; do
      [[ "$file" == codex-skill/* ]] || { echo 'Push stopped: an unpushed commit changes another directory.' >&2; exit 1; }
    done < <(git -C "$repo_root" diff-tree --root --no-commit-id --name-only -r -z "$revision")
  done
  git -C "$repo_root" push origin HEAD:refs/heads/main
  echo 'Push result: success.'
fi
