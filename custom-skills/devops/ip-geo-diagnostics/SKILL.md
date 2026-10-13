---
name: ip-geo-diagnostics
description: "Use when IP labels look wrong: pin truth via RTT, RIPE, CF."
---

# IP Geo Diagnostics & Geo-Identity

Answer two recurring questions for multi-VPS / multi-cloud setups:
1. "What country does this machine *appear* to be in, and why do scanners/sites disagree?"
2. "How do I make services (AI tools, GDPR-aware sites, region-locked apps) see a different country?"

## Core principle
Geo databases are guesses; **latency physics is not**. Three layers exist and can legitimately disagree:
1. **Physical/routing reality** — what RTT + traceroute prove
2. **Registration record** — RIPE/ARIN whois (where the block was *allocated*)
3. **Geo-DB labels** — what websites actually see (MaxMind, Cloudflare, DB-IP, ipinfo, ip-api…)

Work bottom-up: pin the physical location first, then explain the label split.

## Step 1 — Physical location by RTT (trust no DB)
- Best landmark: **any endpoint whose location you already know** (e.g. a known US peer box). US-West→Oregon ≈ 25–35 ms; Europe→Oregon ≈ 120–180 ms — one ping discriminates continents instantly.
- Cross-check with fixed hosts: LA→Frankfurt ≈ 150–165 ms; Warsaw→Frankfurt ≈ 20–30 ms; LA→Fremont CA should be ≈ 10–20 ms (an outlier here hints at ICMP deprioritization — re-check with a different host).
- **Anycast IPs (8.8.8.8, 9.9.9.9, 1.1.1.1) are near-useless**: sub-ms RTT just means an on-net cache node.
- traceroute: reverse-DNS the first external hops for city codes (lax/waw/fra). Private hops (10.x / 192.168.x) inside hops 2–5 = provider internal fabric, normal on VPSes.
- Cloud metadata probes (169.254.169.254 for GCP/AWS, 100.100.100.200 for Alibaba): no response ⇒ not on that cloud.

## Step 2 — Multi-source geo sweep
Query MANY DBs; never conclude from one. Endpoints + fields: `references/provider-cheatsheet.md`. Expect three-way splits — that is the NORM for leased RIPE legacy space: latency-based (ip-api) says the real location, MaxMind-derived (ipinfo/GeoJS) and Cloudflare say the legacy country, registry says EU.

## Step 3 — Registration forensics (explains the split)
No whois client needed: python socket to `whois.ripe.net:43`, or RDAP `https://rdap.db.ripe.net/ip/<ip>`. Markers of a **leased IPv4 block** (root cause of most label chaos):
- `netname: IPXO-*` → block leased through the IPXO marketplace
- `status: SUB-ALLOCATED PA`, org "Private Customer / Private Residence", `country: EU`
- `descr:` naming a transit provider (GTT etc.) that has nothing to do with the original allocation
- Parent allocation in an RIR whose region differs from the ASN's country (e.g. 195.x = RIPE NCC legacy space announced by a US ASN) — geo DBs then split between legacy registration country and actual announcing location.

## Step 4 — What do services ACTUALLY see (the practical question)
- **Cloudflare view** (a huge fraction of the web, incl. most AI tools): `curl https://www.cloudflare.com/cdn-cgi/trace` → `ip` / `loc` (country CF sends as `CF-IPCountry` to origins) / `colo` (PoP) / `warp`.
- Which AI sites read your CF-IPCountry: `curl -sI https://site | grep -i '^server'` → `server: cloudflare` means yes (chatgpt.com, api.openai.com, claude.ai, api.anthropic.com, x.ai are all CF-fronted; gemini.google.com is not).
- **AI region-wall probing**: hit the API unauthenticated and read the error. OpenAI blocked ⇒ code `unsupported_country_region_territory`; plain "Missing bearer authentication" ⇒ NOT blocked. Same pattern for Anthropic (x-api-key required vs region error) and Gemini (permission vs location error).
- **Per-site edge check (strongest signal)**: CF-fronted AI sites expose the trace endpoint on their own zone — `curl -s https://chatgpt.com/cdn-cgi/trace | grep -E '^ip=|^loc=|^colo='` (also works on claude.ai and api.openai.com). This is the exact `loc`/PoP that site's edge assigns you, i.e. the CF-IPCountry their origin receives — more direct than probing cloudflare.com. gemini.google.com is not CF-fronted (no trace).
- If a site treats you as EU when you expect US, your CF PoP's `loc` is usually the cause.

## Step 5 — Changing geo-identity (egress options, cleanest first)
1. **Real US datacenter egress** — route outbound via an existing US box (e.g. GCP us-west peer). Genuine Google/US IPs are labeled US by every DB with clean reputation. Needs reachability + login from the local box (check `~/.ssh` first — it may be empty; then arrange key authorization with the peer's owner).
2. **Cloudflare WARP — does NOT wash a geo label**: the egress IP pool is chosen from the *client IP's* GeoIP country, so a PL-labeled client gets a PL-labeled egress (e.g. 104.28.x.x marked Bydgoszcz PL in every DB). It can also *hurt*: shared WARP egress IPs carry pooled abuse reputation that AI services flag (CAPTCHAs, rate limits, blocks). Fine for hiding origin / cheap egress; useless for country washing.
3. Residential/ISP proxy — only when a site blocks ALL datacenter IPs; the heavy hammer, costs money.

## Pitfalls
- **Never run WARP full-tunnel on a box with inbound connections** (SSH reverse tunnels, bot gateways): replies egress via WARP → asymmetric routing → TCP breaks, and you can sever your own remote session or peer tunnels. Use `warp-cli mode proxy` (SOCKS5 at 127.0.0.1:40000) and point only chosen apps at it.
- warp-cli ≥2025: `--accept-tos` is a **global flag — place it BEFORE the subcommand** (`warp-cli --accept-tos registration new`); older versions took it after. Subcommand usage will error "unexpected argument".
- Never report a single DB's answer as "the" location — quote the split and explain it via registration + routing.
- Forcing a WARP endpoint (`warp-cli tunnel endpoint set <ip:port>`) does not change the egress pool; reset with `warp-cli tunnel endpoint reset` if a chosen IP is unreachable (status will hang on "happy eyeballs").
- Cloudflare's `loc` for its own WARP egress IPs is intentional per-country pooling, not a DB error.
- Verify inbound tunnels/health (e.g. `ss -tnp`, peer `/health`) right after any egress experiment — before declaring success.

## Support files
- `references/provider-cheatsheet.md` — geo-DB endpoints + response fields, whois/RDAP snippets, RTT calibration table, WARP CLI sequence.
