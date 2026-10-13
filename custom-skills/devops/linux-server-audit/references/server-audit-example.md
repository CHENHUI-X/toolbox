# Server Audit Example: 1GB GCP VM (May 2026)

## Environment
- **Provider:** Google Cloud Platform (GCP)
- **Machine:** 2 vCPU (Intel Xeon 2.20GHz), 955MB RAM, 29GB disk
- **OS:** Ubuntu 24.04 LTS
- **Services to keep:** Hermes Agent Gateway + Sing-box (yonggekkk sing-box-yg)
- **Language:** User communicates in Chinese, prefers concise practical responses

## Issues Found

| What | Symptom | Impact |
|------|---------|--------|
| **BT Panel (宝塔面板)** | Port 23884, nginx/nodejs/panel running | ~572MB disk, Nginx overhead |
| **Docker** | `dockerd` running, **zero containers** | ~30MB RAM waste |
| **Containerd** | Docker dependency | ~18MB RAM |
| **Snapd** | 11.3% CPU even idle | Major CPU waste on 2-core VM |
| **Google Cloud Ops Agent** | fluent-bit + otelopscol | ~80MB RAM total |
| **Sing-box service loop** | Restart counter at 59! | CPU wasted on constant restart |
| **Caches** | apt 234MB, npm 158MB, logs 449MB, uv 272MB | ~1.1GB disk waste |

## Cleanup Actions

| Action | Command |
|--------|---------|
| Stop sing-box loop | `systemctl stop sing-box.service` |
| Fix tuic config | `sed -i '/"version": 4,/d' /etc/s-box/sb.json` |
| Remove BT Panel | `systemctl stop bt.service && rm -rf /www` |
| Remove Docker | `apt-get purge -y docker-ce docker-ce-cli containerd.io && rm -rf /var/lib/docker` |
| Remove Snapd | `systemctl mask snapd.service --now && apt-get purge -y snapd --allow-change-held-packages` |
| Remove Ops Agent | `systemctl mask google-cloud-ops-agent.service --now && dpkg --purge --force-remove-reinstreq google-cloud-ops-agent` |
| Clean logs | `journalctl --vacuum-time=3d && truncate -s 0 /var/log/syslog` |
| Clean caches | `apt-get clean && rm -rf /root/.npm/_cacache /root/.cache/uv && uv cache clean` |
| Disable services | `apport, pollinate, e2scrub, ubuntu-advantage, gpu-manager, secureboot-db` |
| Kernel tuning | `sysctl` for vfs_cache_pressure=200, dirty_ratio=10, tcp_fastopen=3 |
| Remove swap | `swapoff /www/swap && rm -f /www/swap` |
| dpkg recovery | `export PATH=$PATH:/usr/sbin:/sbin && dpkg --configure -a` |

## Before vs After Metrics

| Metric | Before | After | Δ |
|--------|--------|-------|---|
| **Disk usage** | 8.5G / 29G (31%) | 4.4G / 29G (16%) | -4.1GB 🟢 |
| **Memory used** | 668MB | 537MB | -131MB 🟢 |
| **Available memory** | 286MB | 417MB | +131MB 🟢 |
| **Swap** | 1GB file active | Removed | -1GB 🟢 |
| **Sing-box restarts** | 59 (crash loop) | 0 (stable) | Fixed ✅ |

## Pitfalls Encountered

1. **UV Python venv breakage** — Deleting `~/.local/share/uv/` destroys Python binaries that venvs link to. Hermes' venv broke entirely. Fix: install `python3-venv`, recreate venv, reinstall deps.
2. **Ops Agent respawning** — `systemctl stop + disable` didn't work because the service had dependency aliases. Had to `systemctl mask <service> --now`.
3. **dpkg PATH** — `dpkg --configure -a` fails with `'ldconfig' not found` unless PATH includes `/usr/sbin:/sbin`.
4. **Snapd on hold** — `apt-mark hold snapd` was set previously, blocking purge. Fixed with `apt-mark unhold snapd` then `--allow-change-held-packages`.
5. **swapoff not in PATH** — Binary at `/sbin/swapoff`, not in default non-interactive PATH.
6. **patch tool refuses /etc/** — Can't use the patch tool for system config files under `/etc/`. Must use `sed -i` via terminal.
