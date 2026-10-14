---
name: clash-sync-config
description: Sync an updated Clash/mihomo subscription config from a local Mac to a team's shared NFS path via scp, then import + enable it on a remote server through clashctl. Use when the user says things like "同步一下 clash 配置"、"更新订阅"、"把新配置传到服务器"、"切换 clash 配置", mentions scp-ing a clash .yaml file to a shared clash directory, or asks how to make a locally-updated Clash config take effect on a server that can't reach GitHub/the subscription URL directly (e.g. clash-for-linux-install on a restricted internal server).
---

# Sync Clash config from Mac to server (offline / NFS workflow)

Workflow for teams running `clash-for-linux-install` on internal servers with restricted outbound network access, where the config can't just be `curl`'d from a subscription URL on the server. Instead: export the config from the local Mac Clash client, scp it to a shared path (e.g. team NFS), then use `clashctl sub add file://... -u` on the server to import and switch to it.

**Every environment detail below is per-user/per-team — always ask rather than assume.** Don't reuse values from a previous run of this skill in a different conversation; ask fresh each time unless the current conversation already stated them.

## Step 0: collect the required info

Ask the user (skip any they've already given in this conversation):

1. **Local config file path** on their Mac — e.g. what their Clash client (ClashX / Clash Verge / mihomo party) exported via "编辑配置" / "打开配置文件夹". If unclear, ask them to confirm the exact path (commonly under `~/Downloads/`).
2. **SSH target for scp** — host, port, and user, e.g. `user@1.2.3.4 -p 2222`. If they only give one server but the shared path is mounted on multiple machines, confirm whether scp-ing once is enough (it is, if it's a shared mount) or whether they need separate scp's per host.
3. **Remote destination path** — the shared directory (NFS or otherwise) the config should live in, and what filename to use there. If they don't have a preference, suggest keeping the filename stable (e.g. `sub.yaml`) across updates so the `clashctl sub add` command doesn't need to change each time.
4. **Which server(s) should actually switch to the new config** — this may differ from the scp target in step 2 if the shared path is mounted cluster-wide. `clashctl sub add ... -u` must be run on each server whose running clash kernel should pick up the change; scp-ing to the shared path alone does not restart anyone's kernel.

## Step 1: scp the updated config to the shared path

```bash
scp -P <port> <local-file-path> <user>@<host>:<remote-shared-path>/<filename>.yaml
```

Note: scp uses **uppercase** `-P` for the port, unlike ssh's lowercase `-p`.

## Step 2: on each server that should use the new config, import + enable it

SSH into the target server, then:

```bash
clashctl sub add file://<remote-shared-path>/<filename>.yaml -u
```

- `file://` must be followed by an **absolute path** — no `~` shorthand.
- `-u` imports and immediately switches the running kernel to the new config in one step.
- Repeat this command on every server that should pick up the change — it's per-server, even when the underlying file is on a shared mount.
- If the install was done without sudo (recommended for containerized/k8s environments — installing as root writes config to root's shell rc instead of the actual user's), `clashctl` should already be on PATH after `source ~/.bashrc`.

## Step 3: verify

```bash
clashctl status
```

Or check the node list / connectivity in the Web panel (`clashui` prints the panel URL). Day-to-day node switching and latency checks should go through the Web panel, not the CLI.
