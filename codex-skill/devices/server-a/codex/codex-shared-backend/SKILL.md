---
name: codex-shared-backend
description: Configure and troubleshoot a shared Codex background server so terminal windows and desktop/mobile remote clients can use the same conversations. Use for remote pairing, OpenHandshake timeouts, or conversation ownership conflicts.
---

# Codex shared background server

Preserve the user's goal of using the native Codex or ChatGPT apps with server-side conversations. Start with local CLI capabilities and actual connection logs; consult current official documentation when a capability or client requirement is unclear.

## Establish what is working

Run `python3 scripts/diagnose.py` from this skill directory for a bounded, read-only summary. It reports configuration, daemon process state, and recent client activity without reading authentication files or printing request bodies.

- `codex app-server daemon version` proves local control-socket availability; a PID file alone does not prove the process is alive. A zombie process can leave a stale socket that refuses connections.
- Remote-control status `connected` describes the server's connection to the service. It does not prove that a phone or desktop has completed secure setup.
- A claimed PIN proves pairing registration. Subsequent requests from a named mobile client, such as `thread/list` or `fs/readFile`, are stronger evidence that the mobile connection can carry application traffic.
- Match logs to the current daemon PID, client identity, transport, and retry time. Do not infer that a request never arrived merely because the exact UI label is absent from server logs.
- `OpenHandshake timeout`, MCP initialization failures, and `thread-store conflict: already has an active writer` are separate findings until evidence connects them. Plugin-sync success does not prove secure-handshake success.

## Default new terminal windows to the shared server

Inspect `codex --help`, `codex features list`, and the installed version before changing configuration. Versions with the `daemon_auto_start` feature support:

```bash
codex features enable daemon_auto_start
codex app-server daemon start
codex app-server daemon version
```

Verify the effective feature is enabled and the daemon's control socket responds. For ordinary new terminal sessions under the same user and configuration, this enables launching with `codex`; resume existing conversations with `codex resume`.

If explicit attachment is needed, supported CLI versions accept:

```bash
codex --remote unix://
codex resume --remote unix://
```

The default socket is normally below `${CODEX_HOME:-$HOME/.codex}/app-server-control/`. `--remote unix://PATH` can select a known custom socket. `--no-daemon`, custom profiles, executor selection, or incompatible command-line overrides may select a different startup mode; verify actual behavior before promising that those invocations also share the server.

Enabling a feature does not migrate already-running embedded CLI processes. When an app cannot resume a conversation owned by an old CLI process, explain the ownership conflict and wait for ongoing work to finish before closing and reopening that conversation against the shared server. Never delete writer locks or kill unrelated sessions to force ownership. Existing history survives an ordinary exit and resume, but ongoing work can be interrupted.

## Recover a failed connection

If the daemon is absent, crashed, or a zombie, restoring the dedicated daemon is appropriate within an authorized connection-repair task. For a responsive daemon, first determine whether it owns active work; a restart can interrupt that work. Use supported daemon commands rather than editing its database or PID files.

After recovery, verify the process state and control socket, then verify real client requests. Distinguish server recovery from end-to-end recovery in the report.

Use `codex remote-control pair` only when the relevant remote-control flow is supported. PINs are short-lived; request a fresh one after an expired or missing pairing session. Treat a pairing reset as a targeted diagnostic action, not a proven fix: it disconnects that device and requires setup again. Identify the exact paired device before revoking it, preserve other devices, and tell the user about the required reconnection.

Do not expose app-server ports publicly or copy private keys between devices. SSH authentication to a development host is separate from app device pairing. Use the desktop app's SSH connection workflow when required by the supported client setup.

## Report the practical result

State which client and connection were verified, what was changed, and what remains unverified. An enabled setting alone is not an end-to-end synchronization test. If a local disk or quota error prevents configuration writes, report the actual failure and reclaim only reproducible, unused caches or use an authorized storage location; preserve conversations, models, credentials, and active executable versions.

Official references: [remote connections](https://learn.chatgpt.com/docs/remote-connections), [app-server and remote terminal UI](https://learn.chatgpt.com/docs/app-server), [configuration](https://learn.chatgpt.com/docs/config).
