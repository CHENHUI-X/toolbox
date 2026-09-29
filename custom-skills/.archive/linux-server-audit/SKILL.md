---
name: linux-server-audit
description: Systematically audit a Linux server to identify resource hogs, unnecessary services, cache bloat, and apply low-memory kernel optimizations. Covers process/service inventory, disk analysis, package cleanup, and performance tuning.
tags: [audit, optimization, performance, troubleshooting, cleanup, linux, devops]
related_skills: [sing-box-vps]
---

# Linux Server Audit & Optimization

Systematic approach to auditing what's on a Linux server, identifying what's consuming resources, cleaning up unnecessary services/packages, and optimizing for specific workloads.

## When to Use

- User says "server feels slow" or "why is it so laggy"
- User asks "look at what's installed" or "audit the server"
- Before deploying a new service on an existing server (clean slate)
- After inheriting a pre-configured VPS with unknown installed software

## Audit Workflow

### 1. Quick Triage — what's eating resources

```bash
# Processes by memory (biggest offenders first)
ps aux --sort=-%mem | head -20

# Processes by CPU
ps aux --sort=-%cpu | head -20

# Memory overview
free -h

# Disk usage
df -h /
```

### 2. Service Inventory

```bash
# Running services
systemctl list-units --type=service --state=running

# All enabled services (start at boot)
systemctl list-unit-files --type=service --state=enabled

# Check for Docker containers (if Docker is installed)
docker ps -a --format "table {{.Names}}\t{{.Image}}\t{{.Status}}"
```

### 3. Disk Deep-Dive

```bash
# Per-top-level-directory (quick)
du -sh /* 2>/dev/null | sort -rh | head -20

# Common bloat locations
du -sh /var/log /var/cache/apt /root/.cache /root/.npm /root/.local /snap /opt /www 2>/dev/null
```

### 4. Network & Ports

```bash
# Listening ports (excluding localhost-only)
ss -tlnp | grep -v "127.0.0.1"
```

## Common Bloat to Remove

| Service | Symptoms | Removal |
|---------|----------|---------|
| **BT Panel (宝塔面板)** | `/www/server/panel/` process, port 23884 | `rm -rf /www` |
| **Docker** | `dockerd` process but `docker ps` shows no containers | `apt-get purge -y docker-ce docker-ce-cli containerd.io` |
| **Snapd** | 10%+ CPU even idle, process always running | `apt-get purge -y snapd && rm -rf /snap /var/snap /var/lib/snapd` |
| **Google Cloud Ops Agent** | fluent-bit + otelopscol processes | `systemctl mask <service> --now && dpkg --purge google-cloud-ops-agent` |
| **Google Guest/OSConfig Agent** | GCP default agents | Disable if not using GCP features |

**IMPORTANT — The Mask Pattern:** Some services (notably `google-cloud-ops-agent`) respawn even after `systemctl stop && disable` because systemd unit aliases or dependencies pull them back. Use `systemctl mask <service> --now` to symlink the unit to `/dev/null` — this blocks every activation path including dependency-driven starts.

### Cache Cleanup Targets

| Cache | Typical Size | Command |
|-------|-------------|---------|
| APT | 100-250MB | `apt-get clean && apt-get autoclean` |
| Journald logs | 200-500MB | `journalctl --vacuum-time=3d` |
| npm cache | 100-200MB | `rm -rf /root/.npm/_cacache` |
| pip cache | 50-200MB | `pip cache purge && rm -rf /root/.cache/pip` |
| uv cache | 100-300MB | `uv cache clean` |
| Old log files | varies | `find /var/log -name "*.gz" -o -name "*.old" -o -name "*.1" ... -delete` |
| apt archives | 100-200MB | `rm -rf /var/cache/apt/archives/*.deb` |

**⚠️ CRITICAL PITFALL — Do NOT delete `~/.local/share/uv/python/`**

If any venv on this server was created via `uv` (e.g. Hermes Agent's venv), its Python interpreter is a symlink into `~/.local/share/uv/python/cpython-3.XX-.../bin/python3.XX`. Running `rm -rf ~/.local/share/uv/` or `rm -rf ~/.local/share/uv/python` will **break every venv that uses uv-managed Python** — they become dangling symlinks with `No such file or directory`.

**Safe uv cleanup:** Only clean `~/.cache/uv/` (the download cache), which contains compiled wheels and won't break venvs:
```bash
uv cache clean           # this cleans ~/.cache/uv  — SAFE
rm -rf ~/.cache/uv       # equivalent — SAFE
```

**UNSAFE — will break venvs:**
```bash
rm -rf ~/.local/share/uv/python    # DESTROYS PYTHON BINARIES — venvs break
rm -rf ~/.local/share/uv           # DESTROYS EVERYTHING — venvs break
```

**If you already broke a venv this way**, recreate it with the system Python:
```bash
apt-get install -y python3-venv
cd /path/to/project
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install -e .
```

Disable the OOM-style crash reporter too if present:
```bash
systemctl disable --now apport.service  # crash reporting
systemctl disable --now pollinate.service  # entropy gathering
```

### dpkg State Recovery

After bulk package removal, check for interrupted dpkg state:

```bash
export PATH=$PATH:/usr/sbin:/sbin
dpkg --configure -a
```

On GCP VMs, `/usr/sbin` and `/sbin` are often missing from PATH in non-interactive shells, causing spurious `'ldconfig' not found in PATH or not executable` errors during dpkg operations.

## Low-Memory Kernel Tuning (≤1GB RAM)

After stripping bloat, apply sysctl tweaks:

```bash
cat > /etc/sysctl.d/99-server-optimize.conf << 'EOF'
vm.vfs_cache_pressure = 200
vm.dirty_ratio = 10
vm.dirty_background_ratio = 5
net.ipv4.tcp_fastopen = 3
net.ipv4.tcp_slow_start_after_idle = 0
EOF
sysctl -p /etc/sysctl.d/99-server-optimize.conf
```

| Parameter | Default | Optimized | Effect |
|-----------|---------|-----------|--------|
| `vfs_cache_pressure` | 100 | 200 | Reclaim inode/dentry cache faster under memory pressure |
| `dirty_ratio` | 20 | 10 | Less dirty page accumulation before flush |
| `dirty_background_ratio` | 10 | 5 | Start write-back earlier |
| `tcp_fastopen` | 1 | 3 | Enable TFO for both directions |
| `tcp_slow_start_after_idle` | 1 | 0 | Don't reset cwnd after idle |

### 1GB VM: Swap & Hermes OOM Prevention

On a ≤1GB VM running Hermes gateway + sing-box + cron jobs, the gateway alone uses ~250-350MB. Without swap, a memory spike (multiple concurrent model calls) can trigger OOM killer.

**Swap sizing:**
```bash
# 4GB swap for 1GB RAM VM — gives ample headroom
swapoff /swapfile 2>/dev/null || true
dd if=/dev/zero of=/swapfile bs=1M count=4096
chmod 600 /swapfile
mkswap /swapfile
swapon /swapfile
echo "/swapfile none swap sw 0 0" >> /etc/fstab
```

**swappiness tuning:**
```bash
echo "vm.swappiness=30" > /etc/sysctl.d/99-oom-protect.conf
sysctl -p /etc/sysctl.d/99-oom-protect.conf
```
Value 30 keeps active processes in RAM longer than default 60 but starts swapping before OOM hits. On a 1GB VM, don't go below 20.

**Hermes gateway memory limit (systemd drop-in):**
```bash
mkdir -p /etc/systemd/system/hermes-gateway.service.d/
cat > /etc/systemd/system/hermes-gateway.service.d/99-memory.conf << 'EOF'
[Service]
MemoryMax=400M
MemoryHigh=350M
OOMPolicy=continue
EOF
systemctl daemon-reload
```
- `MemoryMax=400M` — hard cap, gateway process killed if exceeded
- `MemoryHigh=350M` — soft throttle, slows allocator at 350M
- `OOMPolicy=continue` — don't kill other services if Hermes OOMs

**Verify:**
```bash
systemctl show hermes-gateway | grep -E "Memory(Max|High|Current|Peak|SwapCurrent|Available)"
free -h
swapon --show
```

## Verification

After cleanup, verify:

```bash
# Process check — should see only what you need
ps aux --sort=-%mem | head -5

# No unwanted services
ps aux | grep -cE "snapd|docker|containerd|BT-Panel|BT-Task|fluent-bit|otelopscol"

# Resource check
free -h
df -h /
systemctl is-active hermes-gateway.service sing-box.service  # or your target services

### Proxy Server Context

This audit is often run before deploying proxy services like **sing-box** on the same VPS. For the full sing-box setup, protocol options, subscription output, and troubleshooting guide, see the [sing-box-vps](../sing-box-vps/) skill.
```

## Post-Optimization: Auto-Maintenance Cron Jobs

After cleaning and tuning, set up scheduled maintenance scripts. Use the **`system-cron-setup` skill** for detailed guidance on system crontab patterns, the `no_agent=True` silent-on-success watchdog pattern, and cron state files for retry support.

Two common post-audit scripts to set up as system crontabs:

| Script | Schedule | Silent-on-success? |
|--------|----------|-------------------|
| `~/.hermes/scripts/hermes-update.sh` | Daily 09:00 | ✅ No new commits → silent |
| `~/.hermes/scripts/sing-box-check.sh` | Daily 08:00 | ✅ Everything healthy → silent |

See the [system-cron-setup](../system-cron-setup/) skill for: Telegram notification from cron when gateway is down, version release monitoring via git tags, and server health report templates.

## Pitfalls

- **`patch` tool won't write to `/etc/`** — the `patch` tool refuses system paths. Use `sed -i` via terminal instead for config files under `/etc/`.
- **dpkg + PATH on GCP** — `dpkg --configure -a` fails with `'ldconfig' not found` unless PATH includes `/usr/sbin:/sbin`. Always export PATH first when running dpkg/apt in non-interactive Hermes terminal sessions.
- **Swap files in `/www/`** — BT Panel creates a 1GB swap file at `/www/swap`. After removing `/www`, run `swapoff /www/swap && rm -f /www/swap` to reclaim the space. The `swapoff` binary is in `/sbin/` (PATH issue again).
- **Service respawning** — `systemctl stop` + `disable` is not sufficient for services with alias/dependency chains. Always `mask` services you want permanently gone.
- **`apt-mark hold` can block removal** — If you previously ran `apt-mark hold <package>`, purge will fail with `Held packages were changed and -y was used without --allow-change-held-packages`. Run `apt-mark unhold <package>` first, or add `--allow-change-held-packages`.
- **`kill` vs `pkill -9`** — Processes in D state (uninterruptible sleep) resist SIGTERM. Use `pkill -9 -f <pattern>` for stubborn processes.

## References

- `references/server-audit-example.md` — Full session transcript with exact commands, error messages, and before/after metrics from a 1GB GCP VM audit.
