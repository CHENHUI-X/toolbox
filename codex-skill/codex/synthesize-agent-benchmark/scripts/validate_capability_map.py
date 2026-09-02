#!/usr/bin/env python3
"""校验能力地图的结构、证据和场景判别信息。"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any


CAPABILITY_FIELDS = (
    "名称",
    "用户目标",
    "触发与前提",
    "可见信息与依赖",
    "处理与预期行为",
    "相邻能力边界",
    "规则来源",
)
SCENARIO_FIELDS = (
    "名称",
    "能力",
    "用户情况",
    "关键条件",
    "预期行为",
    "与相邻场景的判别点",
    "规则来源",
)
CONSTRAINT_FIELDS = ("名称", "适用能力", "规则", "规则来源")


def _nonempty_text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _nonempty_text_list(value: Any) -> bool:
    return isinstance(value, list) and bool(value) and all(_nonempty_text(item) for item in value)


def validate_capability_map(data: Any, stage: str) -> list[str]:
    if not isinstance(data, dict):
        return ["能力地图必须是 JSON 对象"]

    issues: list[str] = []
    for field in ("Agent", "评测边界"):
        if not _nonempty_text(data.get(field)):
            issues.append(f"缺少或为空：{field}")
    if not _nonempty_text_list(data.get("证据")):
        issues.append("证据必须是非空文本数组")

    capabilities = data.get("能力")
    if not isinstance(capabilities, list) or not capabilities:
        return issues + ["能力必须是非空数组"]

    capability_names: set[str] = set()
    for index, capability in enumerate(capabilities, start=1):
        prefix = f"能力第{index}项"
        if not isinstance(capability, dict):
            issues.append(f"{prefix}必须是对象")
            continue
        for field in CAPABILITY_FIELDS:
            value = capability.get(field)
            valid = _nonempty_text_list(value) if field in {"可见信息与依赖", "规则来源"} else _nonempty_text(value)
            if not valid:
                issues.append(f"{prefix}缺少或为空：{field}")
        name = capability.get("名称")
        if _nonempty_text(name):
            if name in capability_names:
                issues.append(f"能力名称重复：{name}")
            capability_names.add(name)

    constraints = data.get("通用约束", [])
    if not isinstance(constraints, list):
        issues.append("通用约束必须是数组")
    else:
        for index, constraint in enumerate(constraints, start=1):
            prefix = f"通用约束第{index}项"
            if not isinstance(constraint, dict):
                issues.append(f"{prefix}必须是对象")
                continue
            for field in CONSTRAINT_FIELDS:
                value = constraint.get(field)
                valid = _nonempty_text_list(value) if field in {"适用能力", "规则来源"} else _nonempty_text(value)
                if not valid:
                    issues.append(f"{prefix}缺少或为空：{field}")
            for capability in constraint.get("适用能力") or []:
                if _nonempty_text(capability) and capability not in capability_names:
                    issues.append(f"{prefix}引用了不存在的能力：{capability}")

    if stage == "capability":
        return issues

    scenarios = data.get("场景")
    if not isinstance(scenarios, list) or not scenarios:
        return issues + ["场景阶段必须提供非空场景数组"]
    scenario_names: set[str] = set()
    scenario_pairs: set[tuple[str, str]] = set()
    for index, scenario in enumerate(scenarios, start=1):
        prefix = f"场景第{index}项"
        if not isinstance(scenario, dict):
            issues.append(f"{prefix}必须是对象")
            continue
        for field in SCENARIO_FIELDS:
            value = scenario.get(field)
            valid = _nonempty_text_list(value) if field == "规则来源" else _nonempty_text(value)
            if not valid:
                issues.append(f"{prefix}缺少或为空：{field}")
        name = scenario.get("名称")
        capability = scenario.get("能力")
        if _nonempty_text(name):
            if name in scenario_names:
                issues.append(f"场景名称重复：{name}")
            scenario_names.add(name)
        if _nonempty_text(capability) and capability not in capability_names:
            issues.append(f"{prefix}引用了不存在的能力：{capability}")
        if _nonempty_text(capability) and _nonempty_text(name):
            pair = (capability, name)
            if pair in scenario_pairs:
                issues.append(f"同一能力下场景重复：{capability}/{name}")
            scenario_pairs.add(pair)
    return issues


def main() -> None:
    parser = argparse.ArgumentParser(description="检查能力地图和场景计划")
    parser.add_argument("input", help="能力地图 JSON 文件")
    parser.add_argument("--stage", choices=("capability", "scenario"), default="scenario")
    parser.add_argument("--strict", action="store_true", help="发现问题时以非零状态退出")
    parser.add_argument("--write-report", help="可选：写入中文校验报告")
    args = parser.parse_args()

    path = Path(args.input).expanduser().resolve()
    if not path.is_file():
        parser.error(f"找不到能力地图：{path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        parser.error(f"能力地图不是合法 JSON：{exc.msg}")

    issues = validate_capability_map(data, args.stage)
    capability_count = len(data.get("能力") or []) if isinstance(data, dict) else 0
    scenario_count = len(data.get("场景") or []) if isinstance(data, dict) else 0
    report = {
        "输入文件": str(path),
        "校验阶段": args.stage,
        "能力数": capability_count,
        "场景数": scenario_count,
        "是否通过": not issues,
        "问题": issues,
        "说明": "本校验检查结构、证据和场景判别字段；场景是否真正互斥仍须回读规则并人工审阅。",
    }
    text = json.dumps(report, ensure_ascii=False, indent=2)
    if args.write_report:
        output = Path(args.write_report).expanduser().resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text + "\n", encoding="utf-8")
    print(text)
    if args.strict and issues:
        sys.exit(1)


if __name__ == "__main__":
    main()
