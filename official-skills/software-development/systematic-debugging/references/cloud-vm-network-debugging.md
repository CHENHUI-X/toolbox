# Cloud VM Network Debugging

Pitfalls and techniques for debugging why ports on a cloud VM are unreachable from the internet, drawn from real debugging sessions.

## Architecture: The Three Firewall Layers

```
Client → Internet → [Cloud Firewall] → [VM iptables/ufw] → [Application]
                      GCP/AWS/Azure       inside the VM
```

A port being unreachable can fail at any layer. **Always check all three** before touching config.

## Common Pitfalls (Check These First)

### 1. Cloud Firewall ≠ VM Firewall

| Layer | What it is | How to check | How to fix |
|-------|-----------|-------------|-----------|
| Cloud firewall | GCP VPC firewall, AWS security group, Azure NSG | `gcloud compute firewall-rules list`, AWS Console / `aws ec2 describe-security-groups` | Create allow rule with correct tags/source ranges |
| VM firewall | ufw, iptables on the guest OS | `ufw status`, `iptables -L -n` | `ufw allow port/tcp` |
| App listener | Is the process actually listening? | `ss -tlnp` (TCP), `ss -ulnp` (UDP) | Fix app config |

**GCP-specific:** The default `http-server` network tag only opens TCP 80. `https-server` opens TCP 443. If your instance only has these tags, ALL other ports are blocked at the cloud firewall level regardless of ufw rules. Create new firewall rules targeting the same tag:

```bash
gcloud compute firewall-rules create allow-my-ports \
  --allow tcp:PORT1,tcp:PORT2,udp:PORT3 \
  --source-ranges 0.0.0.0/0 \
  --target-tags http-server
```

### 2. UDP vs TCP — Always Check Both

Many proxy protocols use UDP: Tuic (QUIC), Hysteria2, WireGuard.

| Command | What it shows |
|---------|-------------|
| `ss -tlnp` | TCP listening ports ONLY |
| `ss -ulnp` | UDP listening ports ONLY |
| `ss -tulnp` | BOTH TCP and UDP |

**Do not assume `ss -tlnp` shows everything.** Tuic on port 53900 and Hysteria2 on port 65083 are UDP — they will be invisible in a TCP-only check.

### 3. Internal IP vs External IP Connectivity

| Source → Dest | What happens | Reliable? |
|--------------|-------------|-----------|
| VM → localhost (127.0.0.1:PORT) | Loopback inside kernel | ✅ Proves app is listening |
| VM → internal IP (10.x.x.x:PORT) | GCP internal network | ✅ Proves app accepts connections |
| VM → own external IP (public:PORT) | Hairpinning — GCP drops this by default | ❌ Unreliable, use external checker instead |

**GCP does not support hairpinning** by default. Traffic from inside the VPC to the instance's own external IP is silently dropped. Always use an **external port checker** to test public reachability.

### 4. GCP Ephemeral IPs Change on Stop/Start

If a GCP VM is stopped and started, its **ephemeral external IP may change**. If you stored the old IP in configs or in memory, all nodes will appear down.

```bash
# Get current external IP
curl -s -H "Metadata-Flavor: Google" \
  http://metadata.google.internal/computeMetadata/v1/instance/network-interfaces/0/access-configs/0/external-ip
```

To prevent this, **reserve a static external IP** in GCP.

### 5. Don't Use curl to Test Non-HTTP Protocols

Proxy protocols (VLESS, Vmess, AnyTLS, Shadowsocks) speak their own wire format, not HTTP. curl will connect but get garbage back and report failure.

**For TCP:** Use `/dev/tcp` in bash or a Python socket test:
```bash
timeout 3 bash -c 'echo >/dev/tcp/IP/PORT' && echo "Open" || echo "Closed"
```

```python
import socket
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.settimeout(5)
result = s.connect_ex(('IP', PORT))
# 0 = open, non-zero = closed/timed out
```

**For UDP:** No simple connect check — use a protocol-specific client or leave port open and check `ss -ulnp`.

### 6. External Port Checkers

Since testing from inside GCP to own external IP is unreliable, use an external service:

- **[YouGetSignal](https://www.yougetsignal.com/tools/open-ports/)** — Web-based TCP port checker. Enter IP and port directly.
- **nmap from another machine** — `nmap -sT -p PORT IP`
- **telnet from another machine** — `telnet IP PORT`

## GCP-Specific Debugging Checklist

When a user reports "all nodes timeout" on a GCP VM:

- [ ] Is Sing-box (or the app) running? (`ps aux | grep sing-box`)
- [ ] Are ports listening? (`ss -tulnp | grep PORT`)
- [ ] Is ufw/iptables allowing the ports? (`ufw status | grep PORT`, `iptables -L -n`)
- [ ] Are GCP firewall rules allowing the ports? (check via `gcloud compute firewall-rules list` or Console)
- [ ] Do the instance's network tags match the firewall rule targets? (`curl -s -H "Metadata-Flavor: Google" http://metadata.google.internal/computeMetadata/v1/instance/tags`)
- [ ] Is the external IP correct and hasn't changed since the config was written? (check metadata vs stored IP)
- [ ] From an external port checker, are the ports actually reachable?

## Common Resolution Patterns

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| Local/internal ports work, external times out | Cloud firewall blocking | Add VPC firewall rule |
| ufw allows, iptables shows DROP policy | Default iptables DROP on INPUT chain | `iptables -A INPUT -p tcp --dport PORT -j ACCEPT` or adjust ufw |
| Ports worked yesterday, stopped today | Ephemeral IP changed on VM restart | Use static IP or update configs |
| Only TCP ports work, UDP ports "down" | Checked TCP-only (`ss -tlnp`), missed UDP | Use `ss -tulnp` |
| Single node (e.g. Tuic) fails, others work | Protocol version mismatch or config error | Check app logs, compare config versions |
