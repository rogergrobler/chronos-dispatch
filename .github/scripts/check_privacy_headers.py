"""Fail the send if the live edition is missing noindex / robots.txt.

noindex is necessary but not sufficient for partner-confidential hosting
(GitHub Pages is still publicly reachable). This check only prevents a
generator regression that ships crawlable HTML. Basic Auth belongs in
front of the host (see cloudflare/chronicle-auth-worker.js).
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
REQUIRED_META = "noindex"
REQUIRED_ROBOTS_SNIPPET = "Disallow: /"


def check() -> tuple[int, str]:
    index = (REPO / "index.html").read_text(encoding="utf-8")
    robots = (REPO / "robots.txt").read_text(encoding="utf-8")
    problems = []
    if REQUIRED_META not in index.lower():
        problems.append("index.html missing noindex robots meta")
    if REQUIRED_ROBOTS_SNIPPET not in robots:
        problems.append("robots.txt missing Disallow: /")
    if problems:
        return 1, "PRIVACY CHECK FAILED: " + "; ".join(problems)
    return 0, "OK noindex meta + robots.txt Disallow present"


def main() -> int:
    code, msg = check()
    print(msg)
    return code


if __name__ == "__main__":
    sys.exit(main())
