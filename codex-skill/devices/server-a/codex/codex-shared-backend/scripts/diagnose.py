#!/usr/bin/env python3
"""Read-only, bounded shared-server diagnostics; never print request bodies."""
import collections
import datetime
import json
import os
from pathlib import Path
import shutil
import socket
import sqlite3
import subprocess
import time


def cli(*args):
    try:
        result = subprocess.run(["codex", *args], capture_output=True, text=True, timeout=12)
        if result.returncode:
            return {"ok": False, "exit_code": result.returncode}
        return {"ok": True, "stdout": result.stdout}
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"ok": False, "error_type": type(exc).__name__}


def main():
    home = Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex")))
    report = {"checked_at": datetime.datetime.now().astimezone().isoformat()}
    report["free_disk_bytes"] = shutil.disk_usage(home if home.exists() else home.parent).free
    version = cli("app-server", "daemon", "version")
    report["daemon_control_available"] = version["ok"]
    if version["ok"]:
        try:
            data = json.loads(version["stdout"])
            report["versions"] = {k: data[k] for k in ("cliVersion", "appServerVersion") if k in data}
        except json.JSONDecodeError:
            report["version_response_parse_error"] = True
    features = cli("features", "list")
    for line in features.get("stdout", "").splitlines():
        if line.split()[:1] == ["daemon_auto_start"]:
            report["daemon_auto_start"] = line.split()[-1] == "true"
    pid = None
    try:
        state = json.loads((home / "app-server-daemon/daemon.pid").read_text())
        pid = int(state["pid"])
        process = Path("/proc") / str(pid)
        report["daemon_process_state"] = next(
            line.split(":", 1)[1].strip()
            for line in (process / "status").read_text().splitlines() if line.startswith("State:")
        )
    except (OSError, ValueError, KeyError, StopIteration, json.JSONDecodeError):
        report["daemon_process_state"] = "unavailable"
    control = home / "app-server-control/app-server-control.sock"
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
            connection.settimeout(2)
            connection.connect(str(control))
        report["control_socket_accepts_connections"] = True
    except OSError as exc:
        report["control_socket_accepts_connections"] = False
        report["control_socket_error_type"] = type(exc).__name__
    db = home / "logs_2.sqlite"
    if pid and db.exists():
        try:
            con = sqlite3.connect(db.resolve().as_uri() + "?mode=ro", uri=True, timeout=3)
            cutoff = int(time.time()) - 900
            prefix = f"pid:{pid}:%"
            counts = collections.Counter()
            evidence = collections.Counter()
            query = """SELECT target,feedback_log_body FROM logs
                WHERE process_uuid LIKE ? AND ts>=? AND
                (target='codex_app_server::message_processor' OR
                 target LIKE 'codex_app_server::request_processors::%' OR
                 (level='ERROR' AND target LIKE 'codex_core::session%'))
                ORDER BY id DESC LIMIT 2000"""
            for target, body in con.execute(query, (prefix, cutoff)):
                if target == "codex_app_server::message_processor" and "app-server request: " in body:
                    method = body.split("app-server request: ", 1)[1].split()[0]
                    counts[method] += 1
                if "codex_chatgpt_ios_remote" in body:
                    evidence["ios_request_log_entries"] += 1
                if 'app_server.client_name="Codex Desktop"' in body:
                    evidence["desktop_request_log_entries"] += 1
                if "already has an active writer" in body:
                    evidence["conversation_ownership_errors"] += 1
            con.close()
            report["recent_request_counts"] = dict(counts)
            report["recent_client_evidence"] = dict(evidence)
            report["log_window_minutes"] = 15
        except sqlite3.Error as exc:
            report["log_read_error_type"] = type(exc).__name__
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
