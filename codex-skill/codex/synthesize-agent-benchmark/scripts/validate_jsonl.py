#!/usr/bin/env python3
"""检查 benchmark JSONL 的通用结构与基础跨字段关系，不替代业务语义校验。"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any


def _first(item: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in item:
            return item[key]
    return None


def _reference_answer(item: dict[str, Any]) -> Any:
    answer = _first(item, "标准答案", "reference_answer")
    if answer is not None:
        return answer
    reference = item.get("reference_output")
    return reference.get("reference_answer") if isinstance(reference, dict) else None


def _history(item: dict[str, Any]) -> Any:
    return _first(item, "历史对话", "history")


def _issues_for_history(history: Any) -> list[str]:
    if history is None:
        return []
    if not isinstance(history, list):
        return ["历史对话必须是数组"]
    issues: list[str] = []
    conversation_roles: list[str] = []
    role_map = {"用户": "user", "user": "user", "助手": "assistant", "assistant": "assistant"}
    for index, message in enumerate(history):
        if not isinstance(message, dict):
            issues.append(f"历史对话第{index + 1}条必须是对象")
            continue
        role = _first(message, "角色", "role")
        content = _first(message, "内容", "content")
        if role not in {"用户", "助手", "工具", "系统", "user", "assistant", "tool", "system"}:
            issues.append(f"历史对话第{index + 1}条角色非法：{role!r}")
        if not isinstance(content, str) or not content.strip():
            issues.append(f"历史对话第{index + 1}条内容为空或不是文本")
        if role in role_map:
            conversation_roles.append(role_map[role])
    for index, role in enumerate(conversation_roles):
        expected = "user" if index % 2 == 0 else "assistant"
        if role != expected:
            issues.append("用户/助手消息没有严格交替；如这是工具消息插入导致，请在业务校验中说明")
            break
    return issues


def _validation_issues(item: dict[str, Any]) -> list[str]:
    validation = _first(item, "校验", "validation")
    if not isinstance(validation, dict):
        return []
    issues = _first(validation, "问题", "issues")
    if not issues:
        return []
    if not isinstance(issues, list):
        return ["校验.问题 必须是数组"]
    return [str(issue) for issue in issues]


def validate_case(item: Any) -> list[str]:
    if not isinstance(item, dict):
        return ["case 必须是 JSON 对象"]
    issues: list[str] = []
    if not _first(item, "样本ID", "trace_id", "case_id"):
        issues.append("缺少样本ID")
    if not _first(item, "能力", "capability"):
        issues.append("缺少能力")
    if not _first(item, "场景", "case_category"):
        issues.append("缺少场景")
    if not isinstance(_first(item, "用户输入", "user_input"), str) or not _first(item, "用户输入", "user_input").strip():
        issues.append("用户输入为空")
    canonical_intent = item.get("标准意图")
    if canonical_intent is not None and (not isinstance(canonical_intent, str) or not canonical_intent.strip()):
        issues.append("标准意图为空或不是文本")
    answer = _reference_answer(item)
    if not isinstance(answer, str) or not answer.strip():
        issues.append("标准答案为空")
    issues.extend(_issues_for_history(_history(item)))

    action = item.get("预期动作")
    expected_tools = item.get("expected_tools")
    if action is not None and not isinstance(action, dict):
        issues.append("预期动作必须是对象")
    if action is None and expected_tools is None:
        issues.append("缺少预期动作或 expected_tools")
    if expected_tools is not None and not isinstance(expected_tools, list):
        issues.append("expected_tools 必须是数组")
    if isinstance(action, dict):
        mode = action.get("处理方式")
        if not isinstance(mode, str) or not mode.strip():
            issues.append("预期动作.处理方式为空")
        action_tools = action.get("预期工具")
        if action_tools is not None and not isinstance(action_tools, list):
            issues.append("预期动作.预期工具必须是数组")
        if action_tools and item.get("执行证据") is None:
            issues.append("预期调用工具但执行证据为空")
    if expected_tools and item.get("tool_result") is None and item.get("执行证据") is None:
        issues.append("expected_tools 非空但工具结果/执行证据为空")
    issues.extend(_validation_issues(item))
    return issues


def main() -> None:
    parser = argparse.ArgumentParser(description="检查 JSONL benchmark 的通用结构")
    parser.add_argument("input", help="待检查的 JSONL 文件")
    parser.add_argument("--strict", action="store_true", help="发现任何问题时以非零状态退出")
    parser.add_argument("--write-report", help="可选：写入中文 JSON 校验报告")
    args = parser.parse_args()

    path = Path(args.input).expanduser().resolve()
    if not path.is_file():
        parser.error(f"找不到输入文件：{path}")
    case_ids: set[str] = set()
    issue_rows: list[dict[str, Any]] = []
    total = 0
    with path.open(encoding="utf-8") as source:
        for line_number, line in enumerate(source, start=1):
            if not line.strip():
                continue
            total += 1
            try:
                item = json.loads(line)
            except json.JSONDecodeError as exc:
                issue_rows.append({"行号": line_number, "问题": [f"JSON 解析失败：{exc.msg}"]})
                continue
            issues = validate_case(item)
            sample_id = _first(item, "样本ID", "trace_id", "case_id") if isinstance(item, dict) else None
            if sample_id:
                if sample_id in case_ids:
                    issues.append(f"样本ID重复：{sample_id}")
                case_ids.add(sample_id)
            if issues:
                issue_rows.append({"行号": line_number, "样本ID": sample_id, "问题": issues})

    issue_counter = Counter(issue for row in issue_rows for issue in row["问题"])
    report = {
        "输入文件": str(path),
        "总条数": total,
        "自动检查通过条数": total - len(issue_rows),
        "发现问题的条数": len(issue_rows),
        "问题汇总": dict(issue_counter.most_common()),
        "问题明细": issue_rows,
        "说明": "本报告只检查通用结构和基础跨字段关系；业务规则、事实来源和执行证据正确性仍需 Agent 专属校验。",
    }
    text = json.dumps(report, ensure_ascii=False, indent=2)
    if args.write_report:
        output = Path(args.write_report).expanduser().resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text + "\n", encoding="utf-8")
    print(text)
    if args.strict and issue_rows:
        sys.exit(1)


if __name__ == "__main__":
    main()
