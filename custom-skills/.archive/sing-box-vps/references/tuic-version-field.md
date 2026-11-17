# Tuic Version Field — Sing-box 1.13.x Compatibility

## Error

Sing-box fails to start with:

```
FATAL[0000] decode config at /etc/s-box/sb.json: inbounds[3].version: json: unknown field "version"
```

The journal shows repeated restart attempts:

```
May 26 07:25:10 systemd[1]: sing-box.service: Scheduled restart job, restart counter is at 56.
May 26 07:25:10 systemd[1]: Started sing-box.service.
May 26 07:25:19 sing-box[3681]: FATAL[0000] decode config at /etc/s-box/sb.json: inbounds[3].version: json: unknown field "version"
May 26 07:25:19 systemd[1]: sing-box.service: Main process exited, code=exited, status=1/FAILURE
```

## Root Cause

Sing-box ≥1.13.x removed the `"version"` field from the tuic inbound configuration block. In older versions, tuic config looked like:

```json
{
    "type": "tuic",
    "version": 4,
    "tag": "tuic5-sb",
    "listen": "::",
    "listen_port": 53900,
    "users": [ ... ],
    "congestion_control": "bbr",
    "tls": { ... }
}
```

In 1.13.x, the `"version": 4` field is no longer recognized. The protocol version is auto-detected.

## Fix

Remove the `"version"` line:

```bash
sed -i '/"version": 4,/d' /etc/s-box/sb.json
```

Then validate and restart:

```bash
/etc/s-box/sing-box check -c /etc/s-box/sb.json
systemctl restart sing-box.service
```

## Notes

- The backup file `/etc/s-box/sb.json.bak` may already be a clean version without the `version` field — check before editing.
- This affects any sing-box installation where sb.sh auto-updated the binary but not the config, or where a user manually added `"version": 4` to the tuic block.
- The same `check` → `journalctl` → `sed -i` pipeline works for any sing-box config parsing error, not just tuic.

## Affected Versions

| Sing-box version | Tuic version field |
|-----------------|-------------------|
| ≤1.12.x | Supported (`"version": 4`) |
| ≥1.13.x | **Removed** — causes FATAL |
