#!/usr/bin/env python3
"""Search the reference index; resolve one original prompt when requested."""

import argparse
import hashlib
import json
import re
import subprocess
import sys
import urllib.error
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

REFERENCES = Path(__file__).resolve().parents[1] / "references"
REPOS = {
    "handraw": "yang0/handraw-style",
    "awesome": "freestylefly/awesome-gpt-image-2",
}


def git(path, *args):
    return subprocess.check_output(["git", *args], cwd=path, text=True).strip()


def rebuild(handraw, awesome):
    entries = []
    sources = {}
    for key, root in (("handraw", handraw), ("awesome", awesome)):
        if git(root, "status", "--porcelain", "--untracked-files=no"):
            raise ValueError(f"参考仓库有改动，不能记录为干净版本：{root}")
        commit = git(root, "rev-parse", "HEAD")
        document = (
            "styles_200_reorganized.md"
            if key == "handraw"
            else "data/cases.json"
        )
        payload = (root / document).read_bytes()
        github = f"https://github.com/{REPOS[key]}/blob/{commit}"
        raw = f"https://raw.githubusercontent.com/{REPOS[key]}/{commit}"
        sources[key] = {
            "repository": f"https://github.com/{REPOS[key]}",
            "commit": commit,
            "document": document,
            "sha256": hashlib.sha256(payload).hexdigest(),
            "raw_document_url": f"{raw}/{document}",
            "license_url": f"{github}/LICENSE",
        }
        if key == "handraw":
            image_paths = set(
                git(
                    root, "ls-tree", "-r", "--name-only", "HEAD", "images"
                ).splitlines()
            )
            category = ""
            for line_number, line in enumerate(
                payload.decode().splitlines(), 1
            ):
                if line.startswith("## "):
                    category = line[3:]
                match = re.match(
                    r"^\|\s*(F[A-H]-\d+)\s*·\s*([^|]+)\|\s*([^|]+)\|\s*([^|]*)\|",
                    line,
                )
                if not match:
                    continue
                code, attribution, title, features = [
                    part.strip() for part in match.groups()
                ]
                image_path = f"images/individual/{code[:2]}/{code}.webp"
                entries.append(
                    {
                        "id": f"handraw:{code}",
                        "source": key,
                        "kind": "style",
                        "title": title,
                        "attribution": attribution,
                        "category": category,
                        "description": features,
                        "tags": [],
                        "url": f"{github}/{document}#L{line_number}",
                        "image_url": f"{raw}/{image_path}"
                        if image_path in image_paths
                        else None,
                    }
                )
        else:
            for case in json.loads(payload)["cases"]:
                number = case["id"]
                gallery = (
                    "gallery-part-1.md"
                    if number <= 165
                    else "gallery-part-2.md"
                )
                entries.append(
                    {
                        "id": f"awesome:{number}",
                        "source": key,
                        "kind": "case",
                        "title": case["title"],
                        "attribution": case.get("sourceLabel", ""),
                        "category": case.get("category", ""),
                        "description": case["prompt"][:700],
                        "tags": case.get("styles", [])
                        + case.get("scenes", []),
                        "url": f"{github}/docs/{gallery}#case-{number}",
                        "original_source_url": case.get("sourceUrl", ""),
                        "image_url": f"{raw}/data/images/case{number}.jpg",
                    }
                )
        (REFERENCES / f"{key}-LICENSE.txt").write_bytes(
            (root / "LICENSE").read_bytes()
        )
    if not entries or len({entry["id"] for entry in entries}) != len(entries):
        raise ValueError("目录为空或有重复编号，未更新索引")
    counts = dict(Counter(entry["source"] for entry in entries))
    manifest = {
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "counts": counts,
        "sources": sources,
    }
    for filename, value in (
        ("catalog.json", entries),
        ("sources.json", manifest),
    ):
        (REFERENCES / filename).write_text(
            json.dumps(value, ensure_ascii=False, indent=2) + "\n"
        )
    print(json.dumps(counts, ensure_ascii=False))


def original_prompt(entry):
    if entry["source"] == "handraw":
        return entry["description"]
    source = json.loads((REFERENCES / "sources.json").read_text())["sources"][
        "awesome"
    ]
    request = urllib.request.Request(
        source["raw_document_url"],
        headers={"User-Agent": "self-media-visual-style"},
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        payload = response.read()
    if hashlib.sha256(payload).hexdigest() != source["sha256"]:
        raise ValueError("原文校验不符，未采用该提示词")
    number = int(entry["id"].split(":", 1)[1])
    return next(
        case["prompt"]
        for case in json.loads(payload)["cases"]
        if case["id"] == number
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    search = commands.add_parser("search")
    search.add_argument("terms", nargs="+")
    search.add_argument("--source", choices=REPOS)
    search.add_argument("--limit", type=int, default=6)
    show = commands.add_parser("show")
    show.add_argument("id")
    show.add_argument(
        "--full",
        action="store_true",
        help="联网核对并读取 awesome 的完整原提示词",
    )
    build = commands.add_parser("rebuild")
    build.add_argument("--handraw", type=Path, required=True)
    build.add_argument("--awesome", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "rebuild":
        rebuild(args.handraw, args.awesome)
        return
    entries = json.loads((REFERENCES / "catalog.json").read_text())
    if args.command == "show":
        entry = next(
            (item.copy() for item in entries if item["id"] == args.id), None
        )
        if entry is None:
            parser.error(f"没有这个编号：{args.id}")
        if args.full:
            entry["original_prompt"] = original_prompt(entry)
        print(json.dumps(entry, ensure_ascii=False, indent=2))
        return
    if not 1 <= args.limit <= 30:
        parser.error("--limit 须在 1 至 30 之间")
    ranked = []
    for entry in entries:
        if args.source and entry["source"] != args.source:
            continue
        text = " ".join(
            [
                entry["title"],
                entry["description"],
                entry["category"],
                *entry["tags"],
            ]
        ).casefold()
        score = sum(term.casefold() in text for term in args.terms)
        if score:
            ranked.append((score, entry))
    ranked.sort(key=lambda item: (-item[0], item[1]["id"]))
    print(
        json.dumps(
            [entry for _, entry in ranked[: args.limit]],
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    try:
        main()
    except (
        OSError,
        ValueError,
        KeyError,
        StopIteration,
        subprocess.CalledProcessError,
        urllib.error.URLError,
    ) as error:
        print(f"参考库读取失败：{error}", file=sys.stderr)
        sys.exit(1)
