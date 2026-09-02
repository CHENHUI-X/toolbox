#!/usr/bin/env python3
"""盘点 Agent 资料并给出运行框架线索；结果只供后续人工探索确认。"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any


SKIP_DIRS = {
    ".git", ".idea", ".mypy_cache", ".pytest_cache", ".ruff_cache",
    ".venv", "__pycache__", "dist", "build", "node_modules", "vendor",
    "logs", "results", "output", "outputs",
}
TEXT_EXTENSIONS = {".py", ".md", ".json", ".yaml", ".yml", ".toml", ".txt"}
CATEGORY_HINTS = {
    "Prompt与业务规则": ("prompt", "rule", "policy", "instruction", "system"),
    "工具与接口": ("tool", "function", "api", "schema", "contract"),
    "运行与路由": ("agent", "router", "route", "workflow", "state", "session", "memory"),
    "知识库与检索": ("rag", "retriev", "search", "knowledge", "document"),
    "测试与已有样本": ("test", "case", "benchmark", "eval", "trace", "example"),
}
FRAMEWORK_CUES = {
    "工具调用": ("tool_calls", "function_call", "execute_", '"type": "function"'),
    "RAG或检索": ("retrieval", "retriever", "vector", "rerank", "rag"),
    "工作流或状态机": ("workflow", "state_machine", "transition", "next_state", "node"),
    "路由或多Agent": ("router", "route", "handoff", "delegate", "registry"),
}


def _classify_path(relative_path: Path) -> set[str]:
    name = relative_path.as_posix().lower()
    return {
        category
        for category, tokens in CATEGORY_HINTS.items()
        if any(token in name for token in tokens)
    }


def _read_text(path: Path) -> str:
    if path.suffix.lower() not in TEXT_EXTENSIONS or path.stat().st_size > 262_144:
        return ""
    try:
        return path.read_text(encoding="utf-8", errors="ignore").lower()
    except OSError:
        return ""


def inspect(root: Path, max_files: int) -> dict[str, Any]:
    files: list[Path] = []
    for path in root.rglob("*"):
        if any(part in SKIP_DIRS for part in path.relative_to(root).parts):
            continue
        if path.is_file():
            files.append(path)
    files.sort(key=lambda path: path.as_posix())

    by_category: dict[str, list[str]] = defaultdict(list)
    framework_evidence: dict[str, list[str]] = defaultdict(list)
    selected: list[dict[str, Any]] = []
    for path in files:
        relative = path.relative_to(root)
        categories = _classify_path(relative)
        text = _read_text(path)
        for framework, cues in FRAMEWORK_CUES.items():
            if any(cue in text for cue in cues):
                framework_evidence[framework].append(relative.as_posix())
        for category in categories:
            by_category[category].append(relative.as_posix())
        if categories and len(selected) < max_files:
            selected.append(
                {
                    "文件": relative.as_posix(),
                    "类别": sorted(categories),
                    "字节数": path.stat().st_size,
                }
            )

    return {
        "根目录": str(root),
        "文件总数": len(files),
        "建议优先阅读的文件": selected,
        "按资料类别汇总": {
            category: values[:max_files]
            for category, values in sorted(by_category.items())
        },
        "运行框架线索": [
            {
                "可能的框架": framework,
                "证据文件": sorted(set(paths))[:max_files],
                "说明": "仅是文本线索，必须结合代码、Prompt和测试确认。",
            }
            for framework, paths in sorted(framework_evidence.items())
        ],
        "下一步": [
            "阅读优先文件，梳理 Agent 的目标、边界、状态和执行证据。",
            "不要把本报告的框架线索直接当作结论。",
            "确认哪些历史关系、噪声形式和失败场景对该 Agent 真实适用。",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="盘点 Agent 的 Prompt、规则、代码和测试资料")
    parser.add_argument("--root", required=True, help="目标 Agent 或项目目录")
    parser.add_argument("--output", help="可选：写入 JSON 审计报告")
    parser.add_argument("--max-files", type=int, default=80, help="每类最多展示的文件数")
    args = parser.parse_args()

    root = Path(args.root).expanduser().resolve()
    if not root.is_dir():
        parser.error(f"--root 不是目录：{root}")
    if args.max_files < 1:
        parser.error("--max-files 必须大于 0")

    report = inspect(root, args.max_files)
    text = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        output = Path(args.output).expanduser().resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text + "\n", encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
