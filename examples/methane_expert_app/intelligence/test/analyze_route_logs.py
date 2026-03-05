# !/usr/bin/env python3
# -*- coding:utf-8 -*-

import json
from collections import Counter
from pathlib import Path


def main():
    log_file = Path(__file__).resolve().parent / ".route_logs" / "route_audit.jsonl"
    if not log_file.exists():
        print(f"No route audit log found: {log_file}")
        return

    rows = []
    with log_file.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue

    if not rows:
        print("Route audit log is empty.")
        return

    code_counter = Counter(row.get("route_code", "UNKNOWN") for row in rows)
    type_counter = Counter(row.get("question_type", "UNKNOWN") for row in rows)

    print(f"Total routed questions: {len(rows)}")
    print("\nBy route_code:")
    for k, v in code_counter.most_common():
        print(f"  {k}: {v}")

    print("\nBy question_type:")
    for k, v in type_counter.most_common():
        print(f"  {k}: {v}")

    print("\nLatest 3 records:")
    for row in rows[-3:]:
        print(
            f"- [{row.get('timestamp')}] {row.get('route_code')} | "
            f"{row.get('question_type')} | q={row.get('question')[:60]}"
        )


if __name__ == "__main__":
    main()

