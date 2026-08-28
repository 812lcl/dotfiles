#!/usr/bin/env python3
"""Check timed Obsidian tasks for a target date and report overlaps."""

from __future__ import annotations

import argparse
import pathlib
import re
import sys
from dataclasses import dataclass


TASK_RE = re.compile(
    r"^- \[[ xX]\] (?:(?P<sh>\d{2}):(?P<sm>\d{2}) - (?P<eh>\d{2}):(?P<em>\d{2}) )?(?P<title>.*)$"
)


@dataclass(frozen=True)
class Item:
    start: int
    end: int
    path: pathlib.Path
    line_no: int
    line: str

    @property
    def start_text(self) -> str:
        return f"{self.start // 60:02d}:{self.start % 60:02d}"

    @property
    def end_text(self) -> str:
        return f"{self.end // 60:02d}:{self.end % 60:02d}"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--date", required=True, help="Target date, e.g. 2026-08-12")
    parser.add_argument("--vault", default=".", help="Vault root. Defaults to cwd.")
    parser.add_argument(
        "--files",
        action="append",
        default=[],
        help="Additional vault-relative file to check. Repeatable.",
    )
    parser.add_argument(
        "--include-daily",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Include 1-plan/1-daily/YYYY-MM-DD.md. Default: true.",
    )
    parser.add_argument(
        "--print-items",
        action="store_true",
        help="Print all timed items before the overlap summary.",
    )
    return parser.parse_args()


def minutes(hour: str, minute: str) -> int:
    return int(hour) * 60 + int(minute)


def collect_file(path: pathlib.Path, target_date: str, always_include: bool) -> list[Item]:
    if not path.exists():
        return []

    items: list[Item] = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not always_include and target_date not in line:
            continue

        match = TASK_RE.match(line)
        if not match or match.group("sh") is None:
            continue

        start = minutes(match.group("sh"), match.group("sm"))
        end = minutes(match.group("eh"), match.group("em"))
        if end <= start:
            end += 24 * 60

        items.append(Item(start, end, path, line_no, line))

    return items


def main() -> int:
    args = parse_args()
    vault = pathlib.Path(args.vault).expanduser().resolve()
    files: list[pathlib.Path] = []

    if args.include_daily:
        files.append(vault / "1-plan" / "1-daily" / f"{args.date}.md")

    for raw in args.files:
        path = pathlib.Path(raw).expanduser()
        if not path.is_absolute():
            path = vault / path
        files.append(path)

    items: list[Item] = []
    seen: set[pathlib.Path] = set()
    for path in files:
        path = path.resolve()
        if path in seen:
            continue
        seen.add(path)
        always_include = path.name == f"{args.date}.md" and "1-daily" in path.parts
        items.extend(collect_file(path, args.date, always_include))

    items.sort(key=lambda item: (item.start, item.end, str(item.path), item.line_no))

    if args.print_items:
        print(f"TIMED ITEMS {len(items)}")
        for item in items:
            rel = item.path.relative_to(vault) if item.path.is_relative_to(vault) else item.path
            print(f"{item.start_text}-{item.end_text} {rel}:{item.line_no}: {item.line}")

    overlaps: list[tuple[Item, Item]] = []
    for left, right in zip(items, items[1:]):
        if right.start < left.end:
            overlaps.append((left, right))

    if overlaps:
        print("OVERLAPS")
        for left, right in overlaps:
            left_rel = left.path.relative_to(vault) if left.path.is_relative_to(vault) else left.path
            right_rel = right.path.relative_to(vault) if right.path.is_relative_to(vault) else right.path
            print(f"{left_rel}:{left.line_no}: {left.line}")
            print(f"{right_rel}:{right.line_no}: {right.line}")
        return 1

    print("overlap=none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

