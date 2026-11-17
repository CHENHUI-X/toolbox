---
name: linux-server-audit
description: Systematically audit a Linux server to identify resource hogs, unnecessary services, cache bloat, and apply kernel optimizations — low-memory tuning AND network throughput tuning (BBR + fq + large TCP buffers, with rollback script and A/B verification). Covers process/service inventory, disk analysis, package cleanup.
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

## Network Throughput Tuning (BBR + fq + large TCP buffers)

For VPSes serving long-haul traffic (proxy egress, big downloads). Classic use case: China↔US links (RTT 150–250ms) where Debian defaults lock a single TCP flow to ~200–350 Mbps. Full run log + file templates: `references/bbr-tuning-2026-09.md`.

### Apply (32MB "small-RAM safe" stack)
```bash
cat > /etc/sysctl.d/99-vps-opt.conf <<'EOF'
net.core.default_qdisc = fq
net.ipv4.tcp_congestion_control = bbr
net.core.rmem_max = 33554432
net.core.wmem_max = 33554432
net.core.rmem_default = 1048576
net.core.wmem_default = 1048576
net.ipv4.tcp_rmem = 4096 87380 33554432
net.ipv4.tcp_wmem = 4096 65536 33554432
net.ipv4.tcp_fastopen = 3
net.ipv4.tcp_mtu_probing = 1
net.ipv4.tcp_slow_start_after_idle = 0
net.core.somaxconn = 65535
net.core.netdev_max_backlog = 16384
net.ipv4.tcp_notsent_lowat = 131072
net.ipv4.tcp_tw_reuse = 1
net.ipv4.tcp_fin_timeout = 15
EOF
sysctl --system
tc qdisc replace dev eth0 root fq   # MANDATORY — see pitfall below
```

### The #1 pitfall — BBR "假生效" (fake activation)
`default_qdisc=fq` only applies to interfaces created *after* the sysctl lands. The already-up eth0 silently stays `pfifo_fast` and BBR's pacing never engages. Always: (1) run `tc qdisc replace dev <iface> root fq` immediately, (2) persist via a oneshot systemd unit (`set-fq-qdisc.service`, template in the reference file), (3) verify `tc qdisc show dev <iface>` prints `qdisc fq`.

### Memory math (answers "won't 64MB buffers eat my 1GB VPS?")
- `rmem_max`/`wmem_max` are per-connection CEILINGS (autotuned, allocated only under load), not reservations. Measured on a 2GB box: used RAM went 559→562 MB after applying the full stack.
- `net.ipv4.tcp_mem` is the global fuse across ALL connections (auto-computed from RAM; on 2GB ≈ 89/119/178 MB normal/pressure/hard). Do NOT raise it — it bounds the worst case regardless of per-connection ceilings.
- 32MB suffices for ≈1 Gbps at 250ms RTT (BDP = BW×RTT ≈ 31 MB). 64MB only for multi-Gbps ultra-long paths.

### A/B verification discipline
- Snapshot BEFORE touching anything (`sysctl -a` + `tc qdisc show` into a file).
- Compare on the SAME target; ideally toggle live with `sysctl -w` back/forth — remote paths drift between separate runs.
- **Remote speedtest endpoints often cap per-flow themselves** (proof.ovh.net ≈150 Mbps/flow; Tele2 gave ~0.4 MB/s on one path). Flat before/after there means the bottleneck is remote — don't conclude "tuning useless"; fall back to BDP math (old 6MB/0.2s ≈ 240 Mbps vs new 32MB/0.2s ≈ 1.28 Gbps).
- **User preference (2026-09, Parker): no lab experiments mid-task.** When an A/B setup starts growing (netem on lo, local python test servers), stop and deliver the real-path probe (RTT + one real download, e.g. a CN mirror for China links) + BDP theory instead. Save controlled experiments for explicitly requested deep-dives.
- `terminal` rejects shell-level backgrounding (nohup/&/disown) in foreground calls — for a test daemon use terminal(background=true), then probe in a separate call; clean up afterwards (pkill daemon, restore `tc qdisc` on lo if touched).
- Always ship `/root/rollback_tune.sh` (full factory restore: rm sysctl file, disable+rm qdisc unit, `tc qdisc replace ...`, sysctl -w each old value) and verify inbound services (peer tunnels, bot gateways) still work before declaring success.
- **Rollback must be driven by the per-machine snapshot, not a generic 'factory default' list** — factory values differ per machine/kernel (2026-09-06 real case: GCP/Ubuntu factory was `fastopen=3`, `slow_start_after_idle=0`, `tcp_rmem max=7101984`, qdisc `mq`+`fq_codel`, while Debian was `fastopen=1`, `slow_start_after_idle=1`, `tcp_rmem max=6291456`, `pfifo_fast`). The gcp1 peer found 5 mismatches in a hand-written restore list; restore from `before-snapshot.txt` and cover values the tuning file didn't touch (somaxconn, tw_reuse, fin_timeout).
- **`tc qdisc replace` on an existing `mq` root does not re-hang child qdiscs** — after replacing, children may still show the tuned qdisc; force with `tc qdisc del dev <iface> root` then `tc qdisc add dev <iface> root mq` (this del+add is now in the rollback script).
- **Lingering `bbr` connections in `ss -tin` after rollback are pre-existing connections, not failure** — they keep their negotiated algorithm until they die; new connections use the new cc. Cosmetic, decay naturally.
- **'Revert the tuning' ≠ 'revert everything from the session'** — when the user asks to roll back optimizations, keep unrelated FIXES applied during the same session (e.g. a REALITY handshake-target change) — they're repairs the nodes need regardless of kernel tuning; rolling them back re-breaks the proxy. If the user says "both servers", run the rollback on every box (peer dm task), each restoring from its own snapshot.

## Cross-machine ops (fleet discipline, 2026-09-06)

When the fleet has a second Hermes box (e.g. gcp1 peer over SSH reverse tunnel at 127.0.0.1:9902):
- **Apply the same tuning remotely via `hermes peer dm <peer> "<task>"`** (background=true + notify) instead of begging the user for SSH access — the peer is a full agent with root on its own box. Write the task as a numbered spec: snapshot → config file → iface detection (GCP = ens4, not eth0; resolve via `ip route get 8.8.8.8`; `tc` path differs Ubuntu /usr/sbin vs Debian /sbin) → rollback script → apply → verify. Warn: any step fails = stop and report raw, don't push on.
- **Peer self-reports need a second round of hard evidence** — the peer's file-mutation verifier only tracks write_file, not terminal writes; its "done" was real but initially flagged as failed. Ask for byte sizes, mtimes, and `sysctl --system` Apply lines; only then report up to the user.
- Fleet consistency: same sysctl file name, same rollback path, same snapshot location on every box — future-you doesn't remember which box got which variant.

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
- `references/bbr-tuning-2026-09.md` — Network throughput tuning run: systemd/qdisc/rollback file templates, A/B test log, per-speedtest-target quirks (per-flow caps, dead endpoints).
