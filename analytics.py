import json
import re
from pathlib import Path
from collections import Counter
from datetime import datetime, timezone

ROOT = Path(__file__).parent
OUTPUT = ROOT / "progress.json"

EXCLUDED_DIRS = {
    ".git",
    ".github",
    ".venv",
    "node_modules",
}

def scan_solutions():
    problems = {}

    for folder in ROOT.iterdir():
        if not folder.is_dir():
            continue

        if folder.name in EXCLUDED_DIRS:
            continue

        match = re.match(r"^(\d+)-(.+)$", folder.name)

        if not match:
            continue

        problem_id = int(match.group(1))
        slug = match.group(2)

        solution_files = [
            file for file in folder.iterdir()
            if file.is_file()
            and file.name.startswith("solution.")
        ]

        if not solution_files:
            continue

        problems[problem_id] = {
            "id": problem_id,
            "title": slug.replace("-", " ").title(),
            "slug": slug,
            "files": [file.name for file in solution_files],
            "url": f"https://leetcode.com/problems/{slug}/",
        }

    return sorted(
        problems.values(),
        key=lambda problem: problem["id"]
    )


def main():
    problems = scan_solutions()

    report = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "total_solved": len(problems),
        "problems": problems,
        "languages": dict(Counter(
            file.rsplit(".", 1)[-1]
            for problem in problems
            for file in problem["files"]
        )),
    }

    OUTPUT.write_text(
        json.dumps(report, indent=2),
        encoding="utf-8"
    )

    print(f"Total solved: {report['total_solved']}")
    print(f"Progress saved to: {OUTPUT}")


if __name__ == "__main__":
    main()
