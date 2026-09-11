"""Check solver deliverables for machine-local repository paths.

This keeps the accepted problem folders portable across collaborators' local
checkout names.  It intentionally scans deliverable trees only; request boards
and historical discussion notes may contain archived absolute links.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCAN_ROOTS = ("code", "results", "files")
SKIP_PARTS = {".git", "__pycache__", ".pytest_cache"}
TEXT_SUFFIXES = {
    ".bib",
    ".cfg",
    ".csv",
    ".json",
    ".md",
    ".py",
    ".r",
    ".tex",
    ".txt",
    ".yaml",
    ".yml",
}

REPO_NAME = "MathModeling" + "_" + "Coworkbench"
FORBIDDEN_PATTERNS = (
    re.compile(r"[A-Za-z]:\\[^\n\r`\"']*" + re.escape(REPO_NAME), re.IGNORECASE),
    re.compile(re.escape(REPO_NAME) + r"_push_tmp\d*", re.IGNORECASE),
    re.compile(r"PROJECT_ROOT\.name"),
)


def is_text_candidate(path: Path) -> bool:
    if any(part in SKIP_PARTS for part in path.parts):
        return False
    return path.suffix.lower() in TEXT_SUFFIXES


def find_violations() -> list[tuple[Path, int, str]]:
    violations: list[tuple[Path, int, str]] = []
    for root_name in SCAN_ROOTS:
        root = PROJECT_ROOT / root_name
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if not path.is_file() or not is_text_candidate(path):
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
            for line_no, line in enumerate(text.splitlines(), start=1):
                if any(pattern.search(line) for pattern in FORBIDDEN_PATTERNS):
                    violations.append((path.relative_to(PROJECT_ROOT), line_no, line.strip()))
    return violations


def main() -> int:
    violations = find_violations()
    if violations:
        print("Found machine-local repository path assumptions:")
        for rel_path, line_no, line in violations:
            print(f"{rel_path}:{line_no}: {line}")
        return 1
    print("No machine-local repository path assumptions found in code/results/files.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
