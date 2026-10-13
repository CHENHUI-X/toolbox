# REALITY invalid — client-side stale params (2026-09-19/20 QQG case)

Third distinct cause of mass REALITY rejects (after stale-client-keys-after-rotation and handshake-target-blocked): **the client runs a stale node even though server and subscription params are in perfect sync**.

## Symptom
- Parker: "几个端口全失败/全部超时" — all nodes failing from his view.
- Server journal: arrivals + instant `TLS handshake: REALITY: processed invalid connection`, 0 completions.
- One window: 123.124.194.215 = 401 arrivals / 130 rejects / 0 success; 124.126.141.113 = 13 rejects; 61.148.244.244 = 6 rejects.

## Server-side exonerations (all verified before concluding client-side)
1. **Params sync check**: sb.json truth vs merged-sub.yaml distribution — pbk `UHnerZDTLUX-v1EvAxm8nPQBQeZKCWJAzFTaqBpG4Ds`, sid `e03f8182`, sni `itunes.apple.com`, port 54132, uuid `b1d51f25-…` — verbatim identical.
2. **Rotation theory dead**: key mtimes private.key Sep 3 / public.key Sep 6 / sb.json Sep 6 — nothing rotated since 9/6 sweep, so "stale pbk after recent rotation" cannot explain it.
3. **End-to-end 5-protocol test** (client configs generated from sb.json truth, loopback via public IP): ALL five protocols 204 (vless 3.8s = loopback artifact; others ~0.45s). Server fully healthy — including REALITY itself.

⇒ If server passes end-to-end and distributed params are verbatim-correct, **there is nothing to fix server-side**. Every additional server restart/tweak is wasted motion; go straight to client cleanup.

## Likely stale-param sources on the client
- Old subscription entries still in Stash's list (e.g. the former single-QQG entry `/nx4hspzb` — file deleted, route 404s, but the cached node lives on in the client).
- Manually-added nodes from before a credential sweep.
- Stash having updated some other subscription but not this one (non-forced update used cache).

## Fix delivered (client-side, one step)
1. Delete ALL old subscriptions in Stash; add only `http://aws.eosphor.dpdns.org/merged9k2m?key=…` (verify the URL against subscription-server.py PATH_MAP + curl 200 first).
2. Force update, then airplane-mode toggle.
3. **2-second self-check for the user**: open the [AWS] VLESS node detail in Stash — `public-key` must be `UHner…G4Ds`, `short-id` `e03f8182`. Mismatch = stale client params confirmed without further server digging.

## Diagnosis pitfalls hit this session
- **Grepping logs for ONE remembered user IP gave a false "no connections in 2h"** — Parker's home broadband exit IP rotates constantly (218.12.29.95 → 218.12.27.55 → 123.124.194.215 → 124.126.141.113 → 61.148.244.244 within ~5 days). Always enumerate:
  ```bash
  journalctl -u sing-box --no-pager | grep 'connection from' | grep -oE 'from [0-9.]+' | sort | uniq -c | sort -rn
  ```
- **Per-user success counting reads 0 even while traffic flows**: arrival lines carry `connection from <ip>` but proxy-completion lines say `inbound connection to <dst>` with NO client IP. `grep <ip> | grep 'connection to'` therefore always returns 0. Correlate completion lines to a user via the `[reqid]` bracket token shared by both lines.
- **tcpdump for the user's ClientHello SNI is a lottery** (25s window came up empty — Stash had stopped retrying). Don't block the diagnosis on catching a packet; the log + param-compare path is deterministic.

## Fourth form — mixed accept/reject after port migration = partial stale nodes (2026-09-24 QQG)

After migrating all protocol ports (vless→443 etc.), Parker reported "网络又不好了". Journal showed **vmess on the new port working fine (successes, median 237ms completions) while vless got 99 REALITY rejects / 0 completions in 15min** — interleaved arrival lines, same exit IP.

- **Why vmess passes but vless fails**: vmess completed because the client pulled the new subscription (new port in use); vless still rejecting with verbatim-synced server params = the client's vless node is a **locally-cached old node** — Stash updates nodes lazily when a node is renamed/has changed params inside an updated subscription.
- **Server exonerations to run (fast)**: sb.json≡subscription verbatim check; loopback client with truth params → 204 on the new port; then STOP touching the server.
- **Fix given**: delete + re-add the subscription in Stash (or manually verify the node's public-key/short-id/port in node detail), not another server round.
- **Diagnostic speed tip**: time-bucket the rejects (`journalctl … | grep <ip> | grep REALITY | awk '{print substr($3,1,5)}' | uniq -c`) to see persistent-vs-decaying before deciding it's client-side.

## Fifth form — INVALID bursts interleaved with REAL successes from the same IP = Stash speed-test validator sends a broken handshake (2026-09-25 QQG)

After the GCP-distributed subscription went live, Parker: "Vless qqg 的太慢了！！！不可用！" then "还是不行". Deep-dive (delegate 2 agents) found the decisive signature:

- **Same exit IP produces BOTH `REALITY: processed invalid` bursts AND fully successful handshakes+completions in adjacent minutes** (e.g. 8 invalids 12:01:36–12:02:15, then 5+ successes 12:02:16–12:03:03 including google/apple/WeChat domains, post-restart same pid). Historically 489 invalids vs ~4099 vless attempts from that IP since 9/23, bursty (276 in one 10-min Stash speed-test window).
- **Interpretation**: Stash's node-test/speed-test path constructs a mis-parameterized REALITY handshake (its validator mishandles pbk/sid/utls for vision flow) → every speed test sprays invalids and shows the node as dead, while **actual traffic through the selected node works**.
- **Server-side exonerations to run (same fast set)**: sb.json≡subscription verbatim; loopback 204; GCP-side external TLS probe of 443 (`s_client -servername itunes.apple.com` returns the Apple cert chain, Verification OK) — all passed; also iptables/nft NAT empty, 443 held solely by sing-box, sing-box 1.14.0 (no known REALITY bug for it; bug #4290 Akamai-dest theory disproven by observed successes through the same dest).
- **Fix = tell the user to ignore the speed-test number**: select the node, open a real page. WeChat domains (sgshort.wechat.com) were observed flowing through vless successfully. Restarting sing-box "to clear TLS caches" did nothing (expected in hindsight — server was never the problem).

**Meta-lesson**: before concluding "vless is unusable", grep for SUCCESS lines from the same IP in the same window as the invalids. Interleaved success+invalid = client validator artifact, not a dead node. Also: when user says "还是不行" after the first fix, re-pull fresh logs — the state may have changed (successes had already started).

## Related
- `references/protocol-benchmark-same-host.md` — the 5-protocol loopback test methodology + client config field quirks (hy2/anytls `password`, tuic `alpn: [h3]`, 2082 vmess has NO server TLS, vless sid lives in a list).
- `references/reality-handshake-target-blocked.md` — the ~5m30s-hang variant (vs instant-reject here).
- `references/reality-asymmetric-sni-rule.md` — sni consistency rule for the server-side fix variant.
