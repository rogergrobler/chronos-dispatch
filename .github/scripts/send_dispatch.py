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

SIGNOFF_TEXT = "— Spock @ Chronos\n🖖 Live long and prosper."
SIGNOFF_HTML = '<p style="margin-top: 36px; color: #14110E;">— Spock @ Chronos<br>🖖 Live long and prosper.</p>'

WELCOME_TEXT = (
    "The Chronos Dispatch is a learning digest. The objective: surface things worth reading, "
    "and get better over time at knowing what is worth your time and what is not.\n\n"
    "Each morning Spock reads through roughly twenty-five sources — newsletters, research firms, "
    "the annual letters of the world's best investment thinkers — and picks the six items most "
    "likely to clear the bar. Roger has calibrated Spock against his own reading over the past "
    "two weeks, so today's edition starts from a defensible baseline. From here it is yours to shape.\n\n"
    "Teach Spock what you want to see. Every thumbs vote and line of commentary feeds back — by "
    "source, topic and framing — so the dispatch becomes shaped by what the partners collectively "
    "value, not by what Spock alone finds interesting. Submissions are the strongest signal of all: "
    "paste a link with one line of context, and the item appears in tomorrow's edition under your "
    "name. Spock learns from those faster than from votes.\n\n"
)

WELCOME_HTML = """<p>The Chronos Dispatch is a learning digest. The objective: surface things worth reading, and get better over time at knowing what is worth your time and what is not.</p>

<p>Each morning Spock reads through roughly twenty-five sources — newsletters, research firms, the annual letters of the world's best investment thinkers — and picks the six items most likely to clear the bar. Roger has calibrated Spock against his own reading over the past two weeks, so today's edition starts from a defensible baseline. From here it is yours to shape.</p>

<p>Teach Spock what you want to see. Every thumbs vote and line of commentary feeds back — by source, topic and framing — so the dispatch becomes shaped by what the partners collectively value, not by what Spock alone finds interesting. Submissions are the strongest signal of all: paste a link with one line of context, and the item appears in tomorrow's edition under your name. Spock learns from those faster than from votes.</p>

<hr style="border: none; border-top: 1px solid #BFB3A0; margin: 28px 0;">
"""


def build_email(code, name, email):
    url = f"{base_url}/?p={code}"
    subject = f"The Chronos Dispatch · Issue {int(issue_num):03d} · {date_str}"
    if is_first_send:
        subject += " · welcome"

    items_text = "\n".join(f"  {i+1}. {h}" for i, h in enumerate(headlines))

    # Text body
    if is_first_send:
        intro_text = f"{name},\n\n" + WELCOME_TEXT
    else:
        intro_text = f"{name},\n\n"

    text_body = intro_text + f"""ISSUE {int(issue_num):03d} · {date_str}

{url}

"{editors_note}"

Six items today:
{items_text}

Workshop tip: {tip_headline}

{SIGNOFF_TEXT}

Anything off — reply directly.
"""

    # HTML body
    items_html = "".join(f"<li style=\"margin-bottom: 6px;\">{h}</li>" for h in headlines)

    if is_first_send:
        intro_html = f'<p style="font-size: 17px;">{name},</p>\n\n' + WELCOME_HTML
    else:
        intro_html = f'<p style="font-size: 17px;">{name},</p>'

    html_body = f"""<!DOCTYPE html>
<html><body style="font-family: Georgia, serif; max-width: 640px; margin: 0 auto; padding: 28px; color: #14110E; line-height: 1.65; background: #F6F1E7;">

{intro_html}

<p style="font-family: 'IBM Plex Mono', monospace; font-size: 11px; letter-spacing: 0.18em; color: #6B1F2B; text-transform: uppercase; margin-bottom: 4px;">Issue {int(issue_num):03d} · {date_str}</p>

<p style="text-align: center; margin: 20px 0;"><a href="{url}" style="display: inline-block; background: #6B1F2B; color: #F6F1E7; padding: 14px 32px; text-decoration: none; border-radius: 2px; font-family: 'IBM Plex Mono', monospace; letter-spacing: 0.14em; font-size: 13px;">OPEN ISSUE {int(issue_num):03d} →</a></p>

<p style="font-style: italic; color: #14110E; padding: 16px 20px; background: #EDE5D2; border-left: 3px solid #6B1F2B; margin: 20px 0;">"{editors_note}"</p>

<p><strong>Six items today:</strong></p>
<ol style="padding-left: 20px;">{items_html}</ol>

<p><strong>Workshop tip:</strong> {tip_headline}</p>

{SIGNOFF_HTML}

<p style="color: #6C604F; font-size: 12px; font-style: italic; margin-top: 24px;">Anything off — reply directly.</p>

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
