# Provider Cheat Sheet — geo DBs, registry, landmarks, WARP

## Multi-DB geo sweep endpoints (curl)
| Source | Command | Read fields | Basis |
|---|---|---|---|
| ip-api | `curl -s http://ip-api.com/json/<ip>` | country, city, isp, as | latency/route-based — usually the real location |
| ipinfo.io | `curl -s https://ipinfo.io/<ip>/json` | country, city, org | MaxMind-derived |
| GeoJS | `curl -s "https://get.geojs.io/v1/ip/geo.json?ip=<ip>"` | country_code, city, organization | MaxMind GeoLite2 (AI industry favorite) |
| DB-IP | `curl -s https://api.db-ip.com/v2/free/<ip>` | countryCode, stateProv, city | own data |
| ipwho.is | `curl -s https://ipwho.is/<ip>` | country, city, connection.domain | own data |
| RIPEstat | `curl -s "https://stat.ripe.net/data/geoloc/data.json?resource=<ip>"` | located_resources[].locations[].country | routing/registry view |
| Cloudflare | `curl -s https://www.cloudflare.com/cdn-cgi/trace` | ip, loc (→CF-IPCountry), colo, warp | CF's own DB |

Rate-limit notes: ipapi.co needs a key/rate-limits hard; freegeoip.app redirects (add `-L`); always batch 5–8 sources in one go and quote the SPLIT, never one winner.

## Registry forensics (no whois client needed)
RIPE whois over python socket (port 43, `whois.ripe.net`):
```python
import socket
s=socket.create_connection(('whois.ripe.net',43),timeout=10)
s.sendall(b'<ip>\r\n')   # or b'-l <ip>' for less-specific parents, b'-L -T inetnum <prefix>'
data=b''
while True:
    c=s.recv(4096)
    if not c: break
    data+=c
print(data.decode('utf-8','replace'))
```
RDAP: `curl -s https://rdap.db.ripe.net/ip/<ip>` (fields: name, type, country, entities[].vcardArray).

Leased-block markers to grep: `netname: IPXO-`, `status: SUB-ALLOCATED PA`, `org-name: Private Customer`, `address: Private Residence`, `country: EU`, `descr:` naming a foreign transit. 195.x/185.x/etc. parented to RIPE NCC + announced by a non-EU ASN = legacy space leased and re-homed; expect geo-DB chaos.

## RTT calibration (measured Sept 2026, LA-hosted box)
| Landmark | RTT | Meaning |
|---|---|---|
| Known Oregon peer | 31.7 ms | ⇒ US West. Europe would be 120–180 ms → instant continent discrimination |
| Frankfurt host (www.denic.de) | 165 ms | ⇒ from US West ✓; from Warsaw it would be ~25 ms → rules Europe OUT |
| Warsaw host | filtered | ICMP blocked ≠ conclusion; switch landmarks |
| Google/Quad9 anycast | 0.5 ms | on-net cache — NOT a location signal |
| Fremont CA (216.218.221.6) | 145 ms | anomaly for a US-West box — ICMP deprioritized; re-test with another host before trusting |

Any two consistent landmarks beat any one DB.

## WARP CLI sequence (Debian, warp-cli 2026.x)
```bash
# install (Debian/Ubuntu): Cloudflare apt repo
mkdir -p --mode=0755 /usr/share/keyrings
curl -fsSL https://pkg.cloudflareclient.com/pubkey.gpg | gpg --dearmor -o /usr/share/keyrings/cloudflare-warp-archive-keyring.gpg
echo "deb [signed-by=/usr/share/keyrings/cloudflare-warp-archive-keyring.gpg] https://pkg.cloudflareclient.com/ $(lsb_release -cs) main" > /etc/apt/sources.list.d/cloudflare-client.list
apt-get update && apt-get install -y cloudflare-warp

# NEW CLI: --accept-tos is GLOBAL, BEFORE the subcommand
warp-cli --accept-tos registration new
warp-cli --accept-tos mode proxy          # SOCKS5 127.0.0.1:40000 — NEVER full-tunnel on a box with inbound conns
warp-cli --accept-tos connect
warp-cli --accept-tos status
# verify: curl --socks5-hostname 127.0.0.1:40000 https://www.cloudflare.com/cdn-cgi/trace

# egress experiments (usually futile for geo):
warp-cli --accept-tos tunnel endpoint set <edge-ip>:2408   # force PoP; does NOT change egress geo pool
warp-cli --accept-tos tunnel endpoint reset                # if status hangs on "happy eyeballs", reset
```

## Verdict to report to the user
WARP does not change an IP's country label — CF assigns the egress pool from the client IP's GeoIP (PL client ⇒ 104.28.x.x egress geolocated Bydgoszcz PL by ip-api/ipinfo/MaxMind/DB-IP alike). WARP shared egress also carries pooled abuse reputation that AI services flag. To appear as a clean US identity, egress through a genuine US datacenter IP (e.g. GCP us-west peer) instead.

## AI-service geo-wall quick probes (unauthenticated)
- OpenAI: `curl -s https://api.openai.com/v1/models` → auth error = NOT geo-blocked; `unsupported_country_region_territory` = blocked.
- Anthropic: `curl -s https://api.anthropic.com/v1/messages -X POST -d '{}'` → `authentication_error` = fine.
- Gemini: `curl -s https://generativelanguage.googleapis.com/v1/models` → permission error = fine.
- CF-fronted check: `curl -sI https://site | grep -i '^server'` → cloudflare ⇒ site sees CF-IPCountry. chatgpt.com, api.openai.com, claude.ai, api.anthropic.com, x.ai: cloudflare. gemini.google.com: ESF (Google's own).
