#!/usr/bin/env bash
set -euo pipefail
script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
repo_root=/unused
eval "$(sed -n '/^remote_git()/,/^}/p' "$script_dir/backup.sh")"

# Mock only transport: no files, network requests, or repository writes.
git() {
  case "$3" in
    config) printf '%s' "$test_proxy" ;;
    remote) printf '%s' 'git@github.com:CHENHUI-X/toolbox.git' ;;
    pull)
      attempts=$((attempts + 1))
      last_transport=$GIT_SSH_COMMAND
      if [[ $attempts == 1 ]]; then return "$direct_rc"; fi
      return 0 ;;
    *) return 1 ;;
  esac
}

attempts=0 direct_rc=0 test_proxy=127.0.0.1:7897
remote_git pull --ff-only
[[ $attempts == 1 && "$last_transport" == *ProxyCommand=none* ]]

attempts=0 direct_rc=255
remote_git pull --ff-only
[[ $attempts == 2 && "$last_transport" == *'Hostname=ssh.github.com'* && "$last_transport" == *'nc -X connect -x 127.0.0.1:7897'* ]]

attempts=0 test_proxy=''
if remote_git pull --ff-only; then exit 1; else [[ $? == 255 ]]; fi
[[ $attempts == 1 ]]
echo 'Transport checks passed.'
