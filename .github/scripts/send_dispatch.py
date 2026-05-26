"""Send The Chronos Dispatch to partners via Gmail SMTP from GitHub Actions."""
import json
import os
import re
import smtplib
import sys
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

INDEX = Path("index.html").read_text(encoding="utf-8")

issue_match = re.search(r"Issue No\.\s*0*(\d+)", INDEX)
date_match = re.search(r'<title>The Chronos Dispatch · Issue \d+ · ([^<]+)</title>', INDEX)
note_match = re.search(r'<div class="kicker">Today\'s Read</div>\s*<p>"([^"]+)"', INDEX, re.DOTALL)
headlines = re.findall(r'<article class="item">.*?<h2>([^<]+)</h2>', INDEX, re.DOTALL)
tip_match = re.search(r'<article class="workshop-card">\s*<h4>([^<]+)</h4>', INDEX, re.DOTALL)

issue_num = issue_match.group(1) if issue_match else "?"
date_str = date_match.group(1).strip() if date_match else ""
editors_note = note_match.group(1).strip() if note_match else ""
tip_headline = (tip_match.group(1) if tip_match else "").strip()

partners_raw = os.environ.get("PARTNER_EMAILS_JSON", "{}")
try:
    partners = json.loads(partners_raw)
except json.JSONDecodeError as e:
    print(f"FATAL: PARTNER_EMAILS_JSON invalid: {e}", file=sys.stderr)
    sys.exit(1)

only_to = os.environ.get("ONLY_TO", "").strip()
if only_to:
    if only_to not in partners:
        print(f"FATAL: only_to='{only_to}' not in partners list", file=sys.stderr)
        sys.exit(1)
    partners = {only_to: partners[only_to]}
    print(f"FILTER: sending only to {only_to}")

if not partners:
    print("No partners configured.", file=sys.stderr)
    sys.exit(0)

app_password = os.environ["SPOCK_GMAIL_APP_PASSWORD"].replace(" ", "")
spock_email = os.environ["SPOCK_EMAIL"]
base_url = os.environ["DISPATCH_BASE_URL"].rstrip("/")

is_first_send = (only_to is not None and only_to != "") or int(issue_num) <= 10

def build_email(code, name, email):
    url = f"{base_url}/?p={code}"
    subject = f"The Chronos Dispatch · Issue {int(issue_num):03d} · {date_str}"
    if is_first_send:
        subject += " · welcome"

    items_text = "\n".join(f"  {i+1}. {h}" for i, h in enumerate(headlines))

    if is_first_send:
        intro_text = f"""{name},

The Chronos Dispatch lives at {url}.

That URL is yours — the ?p={code} suffix routes your votes and commentary to you in the feedback database. Inside: vote 👍/👎 on each item with a line on what worked or didn't; submit a Find (one URL + your take, lands in tomorrow's edition); expand "Spock's take" for the longitudinal read on any item.

The bar is the test from Issue 008: "Would not have seen this otherwise." 25+ sources scanned daily — newsletters, research firms, world's-best-thinkers letters (Buffett, Marks, Klarman, Ferguson, Meeker). Six items clear.

"""
    else:
        intro_text = f"{name},\n\n"

    text_body = intro_text + f"""ISSUE {int(issue_num):03d} · {date_str}

{url}

"{editors_note}"

{items_text}

Workshop tip: {tip_headline}

— Spock

Anything off — URL broken, voting jammed, items off-pitch, lands in spam — reply here. The system tunes.
"""

    items_html = "".join(f"<li style=\"margin-bottom: 6px;\">{h}</li>" for h in headlines)

    if is_first_send:
        intro_html = f"""<p style="font-size: 17px;">{name},</p>

<p>The Chronos Dispatch lives at <a href="{url}" style="color: #6B1F2B;">{url}</a>.</p>

<p>That URL is yours — the <code style="background: #EDE5D2; padding: 2px 6px; border-radius: 2px;">?p={code}</code> suffix routes your votes and commentary to you in the feedback database. Inside: vote 👍/👎 on each item with a line on what worked or didn't; submit a Find (one URL + your take, lands in tomorrow's edition); expand "Spock's take" for the longitudinal read on any item.</p>

<p>The bar is the test from Issue 008: <em style="color: #6B1F2B;">"Would not have seen this otherwise."</em> 25+ sources scanned daily — newsletters, research firms, world's-best-thinkers letters (Buffett, Marks, Klarman, Ferguson, Meeker). Six items clear.</p>

<hr style="border: none; border-top: 1px solid #BFB3A0; margin: 28px 0;">
"""
    else:
        intro_html = f"<p style=\"font-size: 17px;\">{name},</p>"

    html_body = f"""<!DOCTYPE html>
<html><body style="font-family: Georgia, serif; max-width: 640px; margin: 0 auto; padding: 28px; color: #14110E; line-height: 1.65; background: #F6F1E7;">

{intro_html}

<p style="font-family: 'IBM Plex Mono', monospace; font-size: 11px; letter-spacing: 0.18em; color: #6B1F2B; text-transform: uppercase; margin-bottom: 4px;">Issue {int(issue_num):03d} · {date_str}</p>

<p style="text-align: center; margin: 20px 0;"><a href="{url}" style="display: inline-block; background: #6B1F2B; color: #F6F1E7; padding: 14px 32px; text-decoration: none; border-radius: 2px; font-family: 'IBM Plex Mono', monospace; letter-spacing: 0.14em; font-size: 13px;">OPEN ISSUE {int(issue_num):03d} →</a></p>

<p style="font-style: italic; color: #14110E; padding: 16px 20px; background: #EDE5D2; border-left: 3px solid #6B1F2B; margin: 20px 0;">"{editors_note}"</p>

<ol style="padding-left: 20px;">{items_html}</ol>

<p><strong>Workshop tip:</strong> {tip_headline}</p>

<p style="margin-top: 32px;">— Spock</p>

<p style="color: #6C604F; font-size: 12px; font-style: italic; margin-top: 24px;">Anything off — URL broken, voting jammed, items off-pitch, lands in spam — reply here. The system tunes.</p>

</body></html>"""

    return subject, text_body, html_body

print(f"Issue {issue_num} · {date_str}")
print(f"Sending to {len(partners)} partner(s)...")

server = smtplib.SMTP("smtp.gmail.com", 587, timeout=20)
server.starttls()
server.login(spock_email, app_password)

for code, info in partners.items():
    name = info["name"]
    email = info["email"]
    subject, text_body, html_body = build_email(code, name, email)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"Spock @ Chronos <{spock_email}>"
    msg["To"] = f"{name} <{email}>"
    msg.attach(MIMEText(text_body, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    server.sendmail(spock_email, email, msg.as_string())
    print(f"  Sent to {name} <{email}>")

server.quit()
print("Done.")
