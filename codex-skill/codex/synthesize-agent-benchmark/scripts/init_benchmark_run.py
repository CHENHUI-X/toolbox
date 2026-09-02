#!/usr/bin/env python3
"""创建 benchmark 审计目录；只记录已确认的计划，不生成 case。"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path


def _write_json_new(path: Path, payload: dict) -> None:
    if path.exists():
        raise FileExistsError(f"文件已存在，拒绝覆盖：{path}")
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _create_empty_file(path: Path) -> None:
    if not path.exists():
        path.touch()


def main() -> None:
    parser = argparse.ArgumentParser(description="创建 sample/formal JSONL 的审计目录")
    parser.add_argument("--output-dir", required=True, help="本次 benchmark 的输出目录")
    parser.add_argument("--agent", required=True, help="用户确认的 Agent 名称")
    parser.add_argument("--scope", required=True, help="用户确认的 Agent 或场景范围")
    parser.add_argument("--sample-count", required=True, type=int, help="探索后计算并确认的 sample 数量")
    parser.add_argument("--formal-count", type=int, help="可选：仅在本次已计划 formal 时传入数量")
    args = parser.parse_args()

    if args.sample_count < 1:
        parser.error("sample 数量必须大于 0")
    if args.formal_count is not None and args.formal_count < 1:
        parser.error("formal 数量必须大于 0")

    root = Path(args.output_dir).expanduser().resolve()
    if root.exists() and not root.is_dir():
        parser.error(f"输出路径不是目录：{root}")
    if root.exists() and any(root.iterdir()):
        parser.error(f"输出目录非空，拒绝混入旧产物：{root}")
    root.mkdir(parents=True, exist_ok=True)
    audit_dir = root / "审计"
    audit_dir.mkdir()
    sample_dir = root / "sample"
    rejected_dir = root / "拒绝样本"
    for directory in (sample_dir, rejected_dir):
        directory.mkdir()
    _create_empty_file(sample_dir / "cases.jsonl")
    _create_empty_file(rejected_dir / "rejected.jsonl")
    formal_path: Path | None = None
    if args.formal_count is not None:
        formal_dir = root / "formal"
        formal_dir.mkdir()
        formal_path = formal_dir / "cases.jsonl"
        _create_empty_file(formal_path)

    manifest = {
        "Agent": args.agent,
        "范围": args.scope,
        "sample计划条数": args.sample_count,
        "formal计划条数": args.formal_count,
        "当前阶段": "待生成sample",
        "formal生成条件": (
            "sample 已由用户审阅并明确确认"
            if args.formal_count is not None
            else "本次仅生成 sample，尚未计划 formal"
        ),
        "创建时间": datetime.now().isoformat(timespec="seconds"),
        "产物": {
            "sample": str(sample_dir / "cases.jsonl"),
            "拒绝样本": str(rejected_dir / "rejected.jsonl"),
        },
    }
    if formal_path is not None:
        manifest["产物"]["formal"] = str(formal_path)
    _write_json_new(audit_dir / "运行清单.json", manifest)
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
