# BBR + fq + Large TCP Buffers — Tuning Run Log (2026-09-05)

Real run on a 2GB Debian 11 VPS (50.114.172.17, US-West, AS213840/FASTNET).
Motivating artifact: a 2026 viral Chinese VPS-tuning infographic (64MB stack + BBR+FQ + Reality/Hysteria2/AnyTLS + subscription 404-hiding + rollback SOP). This log separates its valid kernel advice from its marketing numbers.

## Before state (factory)
```
tcp_congestion_control = cubic      default_qdisc = pfifo_fast
rmem_max = wmem_max = 212992        rmem_default = wmem_default = 212992
tcp_rmem = 4096 131072 6291456      tcp_wmem = 4096 16384 4194304
tcp_fastopen = 1  tcp_mtu_probing = 0  tcp_slow_start_after_idle = 1
somaxconn = 4096  netdev_max_backlog = 1000  tcp_notsent_lowat = 4294967295
tcp_tw_reuse = 2  tcp_fin_timeout = 60
eth0: qdisc pfifo_fast
```

## Files deployed

**/etc/sysctl.d/99-vps-opt.conf** — see SKILL.md section for full content (32MB variant; 64MB = 67108864 if RAM/links allow).

**/etc/systemd/system/set-fq-qdisc.service** (the anti-"假生效" persistence):
```ini
[Unit]
Description=Set FQ qdisc for eth0 at startup
After=network.target network-online.target
Wants=network-online.target

[Service]
Type=oneshot
ExecStart=/sbin/tc qdisc replace dev eth0 root fq
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
```
Enable: `systemctl daemon-reload && systemctl enable --now set-fq-qdisc.service`

**/root/rollback_tune.sh** (one-shot factory restore; all values = the Before block above):
```bash
#!/bin/bash
set -e
rm -f /etc/sysctl.d/99-vps-opt.conf
systemctl disable --now set-fq-qdisc.service 2>/dev/null || true
rm -f /etc/systemd/system/set-fq-qdisc.service
systemctl daemon-reload
/sbin/tc qdisc replace dev eth0 root pfifo_fast
sysctl -w net.ipv4.tcp_congestion_control=cubic
sysctl -w net.core.default_qdisc=pfifo_fast
sysctl -w net.core.rmem_max=212992
sysctl -w net.core.wmem_max=212992
sysctl -w net.core.rmem_default=212992
sysctl -w net.core.wmem_default=212992
sysctl -w net.ipv4.tcp_rmem="4096 131072 6291456"
sysctl -w net.ipv4.tcp_wmem="4096 16384 4194304"
sysctl -w net.ipv4.tcp_fastopen=1
sysctl -w net.ipv4.tcp_mtu_probing=0
sysctl -w net.ipv4.tcp_slow_start_after_idle=1
sysctl -w net.core.somaxconn=4096
sysctl -w net.core.netdev_max_backlog=1000
sysctl -w net.ipv4.tcp_notsent_lowat=4294967295
sysctl -w net.ipv4.tcp_tw_reuse=2
sysctl -w net.ipv4.tcp_fin_timeout=60
echo restored:; tc qdisc show dev eth0 | head -1; sysctl net.ipv4.tcp_congestion_control
```

## A/B results (the honest part)

| Target (RTT) | OLD cubic+208KB/6MB | NEW bbr+fq+32MB | Verdict |
|---|---|---|---|
| OVH proof.ovh.net France (154ms), 3 runs each | 17.75 / 16.98 / 18.50 MB/s | 17.37 / 17.37 / 19.84 MB/s | FLAT — OVH caps ~150 Mbps per flow; remote bottleneck, kernel not exercised |
| Tele2 speedtest Sweden (182ms), 1GB.zip | 0.41–0.44 MB/s | 0.39–0.46 MB/s | FLAT — transatlantic path congestion; remote bottleneck |
| gcp1 peer RTT | 38.79 ms | 38.45 ms | no regression |
| RAM used | 559 MB | 562 MB | ceiling-not-reservation confirmed |

**Key math for the real use case (China↔US, measured RTT ≈ 200–244 ms via baidu/USTC handshakes):**
- BDP at 1 Gbps / 200ms ≈ 25 MB → old 6MB cap locks single flow ≈ 240 Mbps; new 32MB cap allows ≈ 1.28 Gbps. This is the value proposition; per-flow caps of public speedtest servers can't demonstrate it.
- BBR additionally resists the 1–2% loss typical on CN↔US routes where cubic halves throughput; `tcp_slow_start_after_idle=0` avoids re-slow-start after idle (video pause/resume).

## Test-target graveyard (check http_code before trusting ANY number)
- speedtest.tokyo.linode.com/100MB-tokyo.bin → 404 (file gone)
- speed.hetzner.de/1GB.bin → connection reset (service decommissioned)
- mirror.leaseweb.com/speedtest/1000mb.bin → 404
- speed.cloudflare.com/__down → works but intermittently 403s from datacenter IPs; always record %{http_code}
- proof.ovh.net/files/1Gb.dat → reliable but ~150 Mbps/flow cap
- Lesson: `curl -sI` the test file first; record http_code in every run line.

## Infra notes
- 1.9GB box: sing-box + hermes unaffected after tuning; `net.ipv4.tcp_mem` left untouched (global fuse ≈178MB hard).
- Cleanup discipline after lo/netem experiments: `tc qdisc del dev lo root` (verify `noqueue`), pkill test daemons.
