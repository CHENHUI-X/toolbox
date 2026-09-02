#!/usr/bin/env python3
"""统计 JSONL 中已构造的具体场景和处理方式，供 sample/formal 审阅。"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


def _first(item: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in item:
            return item[key]
    return None


def _mode(item: dict[str, Any]) -> str:
    action = item.get("预期动作")
    if isinstance(action, dict) and action.get("处理方式"):
        return str(action["处理方式"])
    tools = item.get("expected_tools")
    if isinstance(tools, list):
        return "调用工具" if tools else "不调用工具"
    return "未标注"


def _load_capability_map(path_text: str) -> tuple[set[str], set[str]]:
    path = Path(path_text).expanduser().resolve()
    if not path.is_file():
        raise FileNotFoundError(f"找不到能力地图：{path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("能力地图必须是 JSON 对象")
    capabilities = {
        str(item.get("名称") or "").strip()
        for item in payload.get("能力") or []
        if isinstance(item, dict) and str(item.get("名称") or "").strip()
    }
    scenarios = {
        str(item.get("名称") or "").strip()
        for item in payload.get("场景") or []
        if isinstance(item, dict) and str(item.get("名称") or "").strip()
    }
    return capabilities, scenarios


def main() -> None:
    parser = argparse.ArgumentParser(description="输出中文的 JSONL 覆盖统计")
    parser.add_argument("input", help="JSONL 文件")
    parser.add_argument("--capability-map", help="可选：对照已确认能力地图检查遗漏")
    parser.add_argument("--output", help="可选：写入 JSON 覆盖报告")
    args = parser.parse_args()

    path = Path(args.input).expanduser().resolve()
    if not path.is_file():
        parser.error(f"找不到输入文件：{path}")
    counters = {
        "Agent": Counter(),
        "能力": Counter(),
        "场景": Counter(),
        "处理方式": Counter(),
        "语言风格": Counter(),
        "历史消息数": Counter(),
    }
    total = 0
    with path.open(encoding="utf-8") as source:
        for line in source:
            if not line.strip():
                continue
            item = json.loads(line)
            if not isinstance(item, dict):
                continue
            total += 1
            counters["Agent"][str(_first(item, "Agent", "agent") or "未标注")] += 1
            counters["能力"][str(_first(item, "能力", "capability") or "未标注")] += 1
            counters["场景"][str(_first(item, "场景", "case_category") or "未标注")] += 1
            counters["处理方式"][_mode(item)] += 1
            counters["语言风格"][str(_first(item, "语言风格", "linguistic_style") or "未标注")] += 1
            history = _first(item, "历史对话", "history")
            counters["历史消息数"][str(len(history) if isinstance(history, list) else 0)] += 1
    planned_capabilities: set[str] = set()
    planned_scenarios: set[str] = set()
    if args.capability_map:
        try:
            planned_capabilities, planned_scenarios = _load_capability_map(args.capability_map)
        except (FileNotFoundError, ValueError, json.JSONDecodeError) as exc:
            parser.error(str(exc))

    actual_capabilities = set(counters["能力"]) - {"未标注"}
    actual_scenarios = set(counters["场景"]) - {"未标注"}
    report = {
        "输入文件": str(path),
        "总条数": total,
        "覆盖统计": {name: dict(counter.most_common()) for name, counter in counters.items()},
        "能力地图对照": (
            {
                "计划能力": sorted(planned_capabilities),
                "未覆盖能力": sorted(planned_capabilities - actual_capabilities),
                "计划场景": sorted(planned_scenarios),
                "未覆盖场景": sorted(planned_scenarios - actual_scenarios),
            }
            if args.capability_map
            else None
        ),
        "说明": "场景名称应直接描述具体用户情况和应有表现；发现‘未标注’或场景过于笼统时，应在 formal 前修订 case plan。",
    }
    text = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        output = Path(args.output).expanduser().resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text + "\n", encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
