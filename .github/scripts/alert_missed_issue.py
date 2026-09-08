"""SMTP ping to Roger when the weekday watchdog fails.

Uses the same Gmail app-password secret as email-dispatch. Does not
contact partners. A missing secret is a warning, not a second failure
mode — the watchdog step has already failed.
"""
from __future__ import annotations

import os
import smtplib
import sys
from email.mime.text import MIMEText

TO = os.environ.get("WATCHDOG_TO", "roger@ccap.ai")
FROM = os.environ.get("SPOCK_EMAIL", "spock@ccap.ai")


def main() -> int:
    password = os.environ.get("SPOCK_GMAIL_APP_PASSWORD", "").replace(" ", "")
    reason = os.environ.get("WATCHDOG_REASON", "weekday issue file missing")
    if not password:
        print("WARN: SPOCK_GMAIL_APP_PASSWORD unset — skip alert email")
        return 0

    body = (
        "Chronos Chronicle watchdog: no weekday issue file for today.\n\n"
        f"Detail: {reason}\n\n"
        "email-dispatch.yml only sends after a feat: Issue push to main. "
        "The generator is the Claude Cowork Mon–Fri 05:30 SAST routine "
        "(cowork-dispatch-bot PAT). Last successful fire was Issue 070 "
        "on 2026-08-24.\n"
    )
    msg = MIMEText(body)
    msg["Subject"] = "Chronos Chronicle missed today's fire"
    msg["From"] = f"Spock @ Chronos <{FROM}>"
    msg["To"] = TO

    server = smtplib.SMTP("smtp.gmail.com", 587, timeout=20)
    server.starttls()
    server.login(FROM, password)
    server.sendmail(FROM, TO, msg.as_string())
    server.quit()
    print(f"Alert sent to {TO}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
