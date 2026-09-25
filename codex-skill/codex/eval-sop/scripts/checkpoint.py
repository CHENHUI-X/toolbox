#!/usr/bin/env python3
"""Create, update, verify, and resume Eval SOP run checkpoints."""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import re
import tempfile
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator


SCHEMA_VERSION = "1.3"
SUPPORTED_SCHEMA_VERSIONS = {"1.0", "1.1", "1.2", SCHEMA_VERSION}
STATUSES = {"pending", "running", "completed", "failed", "skipped"}
DELIVERY_MODES = {"platform", "local-only"}
ONLINE_STRATEGIES = {"direct_output", "replay"}
PROTECTED_FIELDS = {
    "schema_version",
    "run_id",
    "mode",
    "delivery_mode",
    "online_strategy",
    "created_at",
}
SENSITIVE_KEYS = {
    "authorization",
    "cookie",
    "password",
    "api_key",
    "apikey",
    "access_token",
    "refresh_token",
    "secret",
    "credential",
    "credentials",
}

STAGE_ORDER = {
    "offline": [
        "initialized",
        "platform_preflight",
        "dataset_ready",
        "result_task_created",
        "evaluation_prepared",
        "evaluation_completed",
        "records_uploaded",
        "report_uploaded",
        "verified",
        "completed",
    ],
    "online_direct_output": [
        "initialized",
        "platform_preflight",
        "trace_acquired",
        "dataset_ready",
        "result_task_created",
        "evaluation_prepared",
        "evaluation_completed",
        "records_uploaded",
        "report_uploaded",
        "verified",
        "completed",
    ],
    "online_replay": [
        "initialized",
        "platform_preflight",
        "trace_acquired",
        "dataset_ready",
        "replay_task_created",
        "replay_completed",
        "results_exported",
        "result_task_created",
        "evaluation_prepared",
        "evaluation_completed",
        "records_uploaded",
        "report_uploaded",
        "verified",
        "completed",
    ],
}

PLATFORM_OPTIONAL_STAGES = {"offline": set(), "online": {"trace_acquired"}}

LOCAL_ONLY_REQUIRED_STAGES = {
    "offline": {"initialized", "evaluation_prepared", "evaluation_completed", "completed"},
    "online": {
        "initialized",
        "trace_acquired",
        "evaluation_prepared",
        "evaluation_completed",
        "completed",
    },
}


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def generated_run_id() -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"eval-{stamp}-{uuid.uuid4().hex[:8]}"


def validate_run_id(value: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{2,127}", value):
        raise argparse.ArgumentTypeError("run_id must use 3-128 letters, digits, dot, underscore, or hyphen")
    return value


def normalized_key(value: str) -> str:
    return value.strip().lower().replace("-", "_")


def reject_sensitive_keys(value: Any, path: str = "patch") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if normalized_key(str(key)) in SENSITIVE_KEYS:
                raise ValueError(f"refusing sensitive field at {path}.{key}")
            reject_sensitive_keys(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            reject_sensitive_keys(child, f"{path}[{index}]")


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"state or patch file does not exist: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON in {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"expected a JSON object in {path}")
    return value


def atomic_write(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        directory_descriptor = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory_descriptor)
        finally:
            os.close(directory_descriptor)
    finally:
        if temporary.exists():
            temporary.unlink()


@contextmanager
def locked(state_path: Path) -> Iterator[None]:
    lock_path = state_path.with_name(f"{state_path.name}.lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+", encoding="utf-8") as handle:
        os.chmod(lock_path, 0o600)
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def deep_merge(target: dict[str, Any], patch: dict[str, Any]) -> None:
    for key, value in patch.items():
        if key == "delivery_mode" and state_delivery_mode(target) != value:
            raise ValueError("cannot change protected field: delivery_mode")
        if key in PROTECTED_FIELDS and key in target and target[key] != value:
            raise ValueError(f"cannot change protected field: {key}")
        if isinstance(value, dict) and isinstance(target.get(key), dict):
            deep_merge(target[key], value)
        else:
            target[key] = value


def sha256_file(path: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
            size += len(chunk)
    return digest.hexdigest(), size


def fingerprint_path(path: Path) -> dict[str, Any]:
    resolved = path.expanduser().resolve()
    if resolved.is_file():
        digest, size = sha256_file(resolved)
        return {"path": str(resolved), "kind": "file", "sha256": digest, "size_bytes": size}
    if resolved.is_dir():
        digest = hashlib.sha256()
        size = 0
        files = 0
        excluded = {"run_state.json", "run_state.json.lock"}
        for child in sorted(
            item
            for item in resolved.rglob("*")
            if item.is_file() and item.name not in excluded and not item.name.startswith(".run_state.json.")
        ):
            relative = child.relative_to(resolved).as_posix()
            child_digest, child_size = sha256_file(child)
            digest.update(relative.encode("utf-8"))
            digest.update(b"\0")
            digest.update(child_digest.encode("ascii"))
            digest.update(b"\0")
            size += child_size
            files += 1
        return {
            "path": str(resolved),
            "kind": "directory",
            "sha256": digest.hexdigest(),
            "size_bytes": size,
            "file_count": files,
        }
    raise ValueError(f"artifact does not exist: {resolved}")


def state_delivery_mode(state: dict[str, Any]) -> str:
    # Runs created before schema 1.1 are intentionally upgraded to the safer
    # platform contract. They must not silently inherit local-only semantics.
    return str(state.get("delivery_mode") or "platform")


def state_online_strategy(state: dict[str, Any]) -> str | None:
    if state.get("mode") != "online":
        return None
    # Runs created before schema 1.2 used replay unconditionally. Preserve that
    # meaning during recovery instead of silently switching old runs to direct.
    return str(state.get("online_strategy") or "replay")


def stage_order(state: dict[str, Any]) -> list[str]:
    if state.get("mode") == "offline":
        return STAGE_ORDER["offline"]
    strategy = state_online_strategy(state)
    return STAGE_ORDER[f"online_{strategy}"] if strategy in ONLINE_STRATEGIES else []


def platform_required_stages(state: dict[str, Any]) -> set[str]:
    mode = str(state.get("mode"))
    return set(stage_order(state)) - PLATFORM_OPTIONAL_STAGES.get(mode, set())


def receipt_is_successful(receipt: Any) -> bool:
    if not isinstance(receipt, dict) or not receipt:
        return False
    status = str(receipt.get("status", "")).strip().lower()
    if status in {"failed", "failure", "error", "rejected"}:
        return False
    code = receipt.get("code")
    if code is not None and code not in {0, "0"}:
        return False
    return True


def has_identifier(value: Any, names: set[str]) -> bool:
    if isinstance(value, dict):
        for key, child in value.items():
            if normalized_key(str(key)) in names and child not in (None, "", 0, "0"):
                return True
            if has_identifier(child, names):
                return True
    elif isinstance(value, list):
        return any(has_identifier(child, names) for child in value)
    return False


def completion_issues(state: dict[str, Any]) -> list[str]:
    issues = validate_state(state) + verify_artifacts(state)
    mode = str(state.get("mode"))
    delivery_mode = state_delivery_mode(state)
    stages = state.get("stages", {}) if isinstance(state.get("stages"), dict) else {}

    if delivery_mode == "platform":
        required = platform_required_stages(state)
        if mode == "online" and stages.get("trace_acquired", {}).get("status") == "skipped":
            dataset = state.get("dataset") if isinstance(state.get("dataset"), dict) else {}
            if not dataset.get("id"):
                issues.append("trace_acquired may be skipped only when an existing dataset.id is recorded")
        for stage in stage_order(state):
            status = stages.get(stage, {}).get("status")
            if stage in required and status != "completed":
                issues.append(f"platform delivery requires stage {stage!r} to be completed, got {status!r}")
            elif stage not in required and status not in {"completed", "skipped"}:
                issues.append(f"stage {stage!r} must be completed or explicitly skipped, got {status!r}")

        dataset = state.get("dataset") if isinstance(state.get("dataset"), dict) else {}
        if not dataset.get("id"):
            issues.append("platform delivery requires dataset.id")
        expected_dataset_source = (
            "online" if mode == "online" and state_online_strategy(state) == "replay" else "offline"
        )
        if dataset.get("source") != expected_dataset_source:
            issues.append(
                f"platform delivery requires dataset.source == {expected_dataset_source!r} "
                f"for mode={mode!r}, online_strategy={state_online_strategy(state)!r}"
            )
        allowed_categories = {"regression", "release", "benchmark", "smoke"}
        if mode == "online":
            allowed_categories.add("online_replay")
        if dataset.get("category") not in allowed_categories:
            issues.append("platform delivery requires a valid user-selected dataset.category")

        if mode == "online" and state_online_strategy(state) == "direct_output":
            evaluation = state.get("evaluation") if isinstance(state.get("evaluation"), dict) else {}
            if evaluation.get("input_source") != "trace_output":
                issues.append("direct_output delivery requires evaluation.input_source == 'trace_output'")
        if mode == "online" and state_online_strategy(state) == "replay":
            evaluation = state.get("evaluation") if isinstance(state.get("evaluation"), dict) else {}
            if evaluation.get("input_source") != "replay_output":
                issues.append("replay delivery requires evaluation.input_source == 'replay_output'")

        dms = state.get("dms") if isinstance(state.get("dms"), dict) else {}
        if not dms.get("base_url"):
            issues.append("platform delivery requires dms.base_url")
        if not dms.get("application_id"):
            issues.append("platform delivery requires dms.application_id")
        result_task_id = dms.get("task_id")
        if not result_task_id:
            issues.append("platform delivery requires the created result-bearing dms.task_id")
        else:
            expected_report_url = f"http://dmstest.didichuxing.com/eval/tasks/{result_task_id}/report"
            if dms.get("report_url") != expected_report_url:
                issues.append(
                    "platform delivery requires dms.report_url == "
                    f"{expected_report_url!r} for the result-bearing task"
                )
        if (
            mode == "online"
            and state_online_strategy(state) == "replay"
            and not has_identifier(state.get("replay"), {"id", "task_id", "taskid"})
        ):
            issues.append("replay delivery requires a created replay task identifier")

        uploads = state.get("uploads") if isinstance(state.get("uploads"), dict) else {}
        for name in ("dataset", "task", "records", "report"):
            if not receipt_is_successful(uploads.get(name)):
                issues.append(f"platform delivery requires a successful uploads.{name} receipt")
        if not has_identifier(
            {"dms": dms, "replay": state.get("replay"), "report": uploads.get("report")},
            {"report_id", "reportid"},
        ):
            issues.append("platform delivery requires a DMS report identifier")
    else:
        for stage in LOCAL_ONLY_REQUIRED_STAGES.get(mode, set()):
            status = stages.get(stage, {}).get("status")
            if status != "completed":
                issues.append(f"local-only delivery requires stage {stage!r} to be completed, got {status!r}")
    return issues


def stage_is_terminal(state: dict[str, Any], stage: str, status: Any) -> bool:
    if status == "completed":
        return True
    if status != "skipped":
        return False
    if state_delivery_mode(state) == "local-only":
        return True
    if stage not in PLATFORM_OPTIONAL_STAGES.get(str(state.get("mode")), set()):
        return False
    if stage == "trace_acquired":
        dataset = state.get("dataset") if isinstance(state.get("dataset"), dict) else {}
        return bool(dataset.get("id"))
    return True


def initial_state(
    run_id: str, mode: str, delivery_mode: str, online_strategy: str | None
) -> dict[str, Any]:
    timestamp = now_utc()
    return {
        "schema_version": SCHEMA_VERSION,
        "run_id": run_id,
        "mode": mode,
        "delivery_mode": delivery_mode,
        "online_strategy": online_strategy,
        "status": "initialized",
        "current_stage": "initialized",
        "created_at": timestamp,
        "updated_at": timestamp,
        "dataset": {
            "id": None,
            "version": None,
            "source": None,
            "category": None,
        },
        "replay": {"tasks": [], "configuration": None},
        "dms": {
            "base_url": None,
            "application_id": None,
            "task_id": None,
            "report_id": None,
            "report_url": None,
            "url": None,
        },
        "evaluation": {"method": None, "version": None, "results": []},
        "uploads": {},
        "artifacts": {},
        "errors": [],
        "stages": {
            "initialized": {
                "status": "completed",
                "attempt": 1,
                "started_at": timestamp,
                "completed_at": timestamp,
                "updated_at": timestamp,
                "error": None,
            }
        },
        "events": [
            {"at": timestamp, "stage": "initialized", "status": "completed", "kind": "init"}
        ],
    }


def validate_state(state: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    for key in ("schema_version", "run_id", "mode", "status", "current_stage", "stages", "artifacts"):
        if key not in state:
            issues.append(f"missing required field: {key}")
    if state.get("schema_version") not in SUPPORTED_SCHEMA_VERSIONS:
        issues.append(f"unsupported schema_version: {state.get('schema_version')!r}")
    if state.get("mode") not in {"offline", "online"}:
        issues.append(f"invalid mode: {state.get('mode')!r}")
    if state.get("mode") == "online" and state_online_strategy(state) not in ONLINE_STRATEGIES:
        issues.append(f"invalid online_strategy: {state_online_strategy(state)!r}")
    if state.get("mode") == "offline" and state.get("online_strategy") not in {None, ""}:
        issues.append("offline runs must not set online_strategy")
    if state_delivery_mode(state) not in DELIVERY_MODES:
        issues.append(f"invalid delivery_mode: {state_delivery_mode(state)!r}")
    if not isinstance(state.get("stages"), dict):
        issues.append("stages must be an object")
    if not isinstance(state.get("artifacts"), dict):
        issues.append("artifacts must be an object")
    return issues


def verify_artifacts(state: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    artifacts = state.get("artifacts")
    if not isinstance(artifacts, dict):
        return ["artifacts must be an object"]
    for name, expected in artifacts.items():
        if not isinstance(expected, dict) or not expected.get("path"):
            issues.append(f"artifact {name!r} has no path")
            continue
        try:
            actual = fingerprint_path(Path(str(expected["path"])))
        except ValueError as exc:
            issues.append(f"artifact {name!r}: {exc}")
            continue
        if expected.get("sha256") and expected["sha256"] != actual["sha256"]:
            issues.append(f"artifact {name!r} checksum mismatch")
        if expected.get("kind") and expected["kind"] != actual["kind"]:
            issues.append(f"artifact {name!r} kind mismatch")
    return issues


def save_state(state_path: Path, state: dict[str, Any]) -> None:
    state["updated_at"] = now_utc()
    atomic_write(state_path, state)


def command_init(args: argparse.Namespace) -> int:
    run_dir = args.run_dir.expanduser().resolve()
    state_path = run_dir / "run_state.json"
    run_id = args.run_id or generated_run_id()
    online_strategy = args.online_strategy
    if args.mode == "online" and not online_strategy:
        online_strategy = "direct_output"
    if args.mode == "offline" and online_strategy:
        raise ValueError("--online-strategy is valid only with --mode online")
    with locked(state_path):
        if state_path.exists():
            raise ValueError(f"state already exists: {state_path}")
        run_dir.mkdir(parents=True, exist_ok=True)
        state = initial_state(run_id, args.mode, args.delivery_mode, online_strategy)
        atomic_write(state_path, state)
    print(
        json.dumps(
            {
                "run_id": run_id,
                "delivery_mode": args.delivery_mode,
                "online_strategy": online_strategy,
                "state_path": str(state_path),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def command_save(args: argparse.Namespace) -> int:
    if args.status == "failed" and not args.error:
        raise ValueError("--error is required when --status failed")
    state_path = args.state.expanduser().resolve()
    patch: dict[str, Any] = {}
    if args.patch_file:
        patch = load_json(args.patch_file.expanduser().resolve())
        reject_sensitive_keys(patch)
    with locked(state_path):
        state = load_json(state_path)
        issues = validate_state(state)
        if issues:
            raise ValueError("; ".join(issues))
        if (
            args.status == "skipped"
            and state_delivery_mode(state) == "platform"
            and args.stage in platform_required_stages(state)
        ):
            raise ValueError(
                f"cannot skip required platform stage {args.stage!r}; "
                "start a new run with --delivery-mode local-only only when the user explicitly opts out"
            )
        deep_merge(state, patch)
        timestamp = now_utc()
        stages = state.setdefault("stages", {})
        previous = stages.get(args.stage, {})
        attempt = int(previous.get("attempt", 0))
        if args.status == "running" and previous.get("status") != "running":
            attempt += 1
        if attempt == 0:
            attempt = 1
        stage = dict(previous)
        stage.update({"status": args.status, "attempt": attempt, "updated_at": timestamp})
        if args.status == "running":
            stage["started_at"] = timestamp
            stage["completed_at"] = None
            stage["error"] = None
        elif args.status in {"completed", "skipped"}:
            stage["completed_at"] = timestamp
            stage["error"] = None
        elif args.status == "failed":
            stage["error"] = args.error
        stages[args.stage] = stage
        state["current_stage"] = args.stage
        if args.status == "failed":
            state["status"] = "failed"
        elif args.stage == "completed" and args.status == "completed":
            state["status"] = "completed"
        else:
            state["status"] = "running"
        if args.error:
            state.setdefault("errors", []).append({"at": timestamp, "stage": args.stage, "message": args.error})
        state.setdefault("events", []).append(
            {
                "at": timestamp,
                "stage": args.stage,
                "status": args.status,
                "kind": "checkpoint",
                "patch_fields": sorted(patch.keys()),
            }
        )
        if args.stage == "completed" and args.status == "completed":
            gate_issues = completion_issues(state)
            if gate_issues:
                raise ValueError("completion gate failed: " + "; ".join(gate_issues))
        save_state(state_path, state)
    print(json.dumps({"run_id": state["run_id"], "stage": args.stage, "status": args.status}, ensure_ascii=False, indent=2))
    return 0


def command_artifact(args: argparse.Namespace) -> int:
    state_path = args.state.expanduser().resolve()
    artifact = fingerprint_path(args.path)
    artifact["recorded_at"] = now_utc()
    if args.stage:
        artifact["stage"] = args.stage
    with locked(state_path):
        state = load_json(state_path)
        issues = validate_state(state)
        if issues:
            raise ValueError("; ".join(issues))
        state.setdefault("artifacts", {})[args.name] = artifact
        state.setdefault("events", []).append(
            {"at": now_utc(), "stage": args.stage, "kind": "artifact", "name": args.name}
        )
        save_state(state_path, state)
    print(json.dumps({"name": args.name, **artifact}, ensure_ascii=False, indent=2))
    return 0


def command_verify(args: argparse.Namespace) -> int:
    state_path = args.state.expanduser().resolve()
    state = load_json(state_path)
    issues = validate_state(state) + verify_artifacts(state)
    result = {"run_id": state.get("run_id"), "valid": not issues, "issues": issues}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not issues else 2


def command_resume(args: argparse.Namespace) -> int:
    state_path = args.state.expanduser().resolve()
    state = load_json(state_path)
    issues = validate_state(state) + verify_artifacts(state)
    order = stage_order(state)
    stages = state.get("stages", {}) if isinstance(state.get("stages"), dict) else {}
    next_stage = None
    for candidate in order:
        candidate_status = stages.get(candidate, {}).get("status")
        if not stage_is_terminal(state, candidate, candidate_status):
            next_stage = candidate
            break
    current_status = stages.get(state.get("current_stage"), {}).get("status")
    action = "continue"
    if current_status in {"running", "failed"}:
        action = "verify_external_state_before_retry"
    if issues:
        action = "repair_checkpoint_before_resume"
    result = {
        "run_id": state.get("run_id"),
        "mode": state.get("mode"),
        "delivery_mode": state_delivery_mode(state),
        "online_strategy": state_online_strategy(state),
        "run_status": state.get("status"),
        "current_stage": state.get("current_stage"),
        "current_stage_status": current_status,
        "next_stage": next_stage,
        "action": action,
        "issues": issues,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not issues else 2


def command_gate(args: argparse.Namespace) -> int:
    state = load_json(args.state.expanduser().resolve())
    issues = completion_issues(state)
    result = {
        "run_id": state.get("run_id"),
        "mode": state.get("mode"),
        "delivery_mode": state_delivery_mode(state),
        "online_strategy": state_online_strategy(state),
        "ready": not issues,
        "issues": issues,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not issues else 2


def command_show(args: argparse.Namespace) -> int:
    print(json.dumps(load_json(args.state.expanduser().resolve()), ensure_ascii=False, indent=2, sort_keys=True))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Persist and resume Eval SOP runs")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init", help="Create a new run_state.json")
    init_parser.add_argument("--run-dir", type=Path, required=True)
    init_parser.add_argument("--mode", choices=["offline", "online"], required=True)
    init_parser.add_argument("--delivery-mode", choices=sorted(DELIVERY_MODES), default="platform")
    init_parser.add_argument("--online-strategy", choices=sorted(ONLINE_STRATEGIES))
    init_parser.add_argument("--run-id", type=validate_run_id)
    init_parser.set_defaults(handler=command_init)

    save_parser = subparsers.add_parser("save", help="Atomically save a stage checkpoint")
    save_parser.add_argument("--state", type=Path, required=True)
    save_parser.add_argument("--stage", required=True)
    save_parser.add_argument("--status", choices=sorted(STATUSES), required=True)
    save_parser.add_argument("--patch-file", type=Path)
    save_parser.add_argument("--error")
    save_parser.set_defaults(handler=command_save)

    artifact_parser = subparsers.add_parser("artifact", help="Record a file or directory fingerprint")
    artifact_parser.add_argument("--state", type=Path, required=True)
    artifact_parser.add_argument("--name", required=True)
    artifact_parser.add_argument("--path", type=Path, required=True)
    artifact_parser.add_argument("--stage")
    artifact_parser.set_defaults(handler=command_artifact)

    verify_parser = subparsers.add_parser("verify", help="Validate state and artifact fingerprints")
    verify_parser.add_argument("--state", type=Path, required=True)
    verify_parser.set_defaults(handler=command_verify)

    resume_parser = subparsers.add_parser("resume", help="Locate the next safe stage")
    resume_parser.add_argument("--state", type=Path, required=True)
    resume_parser.set_defaults(handler=command_resume)

    gate_parser = subparsers.add_parser("gate", help="Enforce the delivery completion contract")
    gate_parser.add_argument("--state", type=Path, required=True)
    gate_parser.set_defaults(handler=command_gate)

    show_parser = subparsers.add_parser("show", help="Print the complete checkpoint")
    show_parser.add_argument("--state", type=Path, required=True)
    show_parser.set_defaults(handler=command_show)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        return int(args.handler(args))
    except ValueError as exc:
        parser.error(str(exc))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
