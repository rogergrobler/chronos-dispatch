"""Fail if today's weekday Chronicle issue file is missing from the repo.

The generator (Claude Cowork scheduled task) is supposed to push
YYYY-MM-DD.html plus index.html around 03:43 UTC on Mon–Fri. This repo's
email workflow only runs *after* that push. If the generator is silent,
email-dispatch never runs and the outage is invisible — that is what
happened after Issue 070 (2026-08-24).

Exit 0: today's dated HTML exists (or today is a weekend).
Exit 1: weekday fire is missing.
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def utc_today(now: datetime | None = None) -> datetime:
    return (now or datetime.now(timezone.utc)).astimezone(timezone.utc)


def should_expect_issue(day: datetime) -> bool:
    return day.weekday() < 5  # Mon–Fri


def issue_path_for(day: datetime) -> Path:
    return REPO / f"{day.date().isoformat()}.html"


def check(day: datetime | None = None) -> tuple[int, str]:
    day = utc_today(day)
    path = issue_path_for(day)
    if not should_expect_issue(day):
        return 0, f"SKIP weekend {day.date().isoformat()} (no scheduled fire)"
    if path.is_file() and path.stat().st_size > 0:
        return 0, f"OK {path.name} present ({path.stat().st_size} bytes)"
    last = sorted(REPO.glob("2026-*.html"))
    last_name = last[-1].name if last else "(none)"
    return (
        1,
        "MISSING weekday issue {today}. Last dated file in repo: {last}. "
        "email-dispatch.yml never runs unless a feat: Issue commit pushes "
        "index.html. Restore the Cowork Mon–Fri 05:30 SAST generator and "
        "rotate the cowork-dispatch-bot GitHub PAT (Notion documented a "
        "~90-day PAT created 26 May 2026 → expiry ~24 Aug 2026, the last "
        "successful fire).".format(today=path.name, last=last_name),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--date",
        help="UTC date YYYY-MM-DD to check (default: now UTC)",
    )
    args = parser.parse_args(argv)
    day = None
    if args.date:
        day = datetime.fromisoformat(args.date).replace(tzinfo=timezone.utc)
    code, msg = check(day)
    print(msg)
    return code


if __name__ == "__main__":
    sys.exit(main())
