"""Send The Chronos Dispatch to partners via Gmail SMTP."""
import json
import os
import re
import smtplib
import sys
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

INDEX = Path("index.html").read_text(encoding="utf-8")

# Extract issue number, date, editor's note, item headlines
issue_match = re.search(r"Issue No\.\s*(\d+)", INDEX)
date_match = re.search(r'<title>The Chronos Dispatch · Issue \d+ · ([^<]+)</title>', INDEX)
note_match = re.search(r'<div class="kicker">Today\'s Read</div>\s*<p>"([^"]+)"', INDEX, re.DOTALL)
headlines = re.findall(r'<h2>([^<]+)</h2>', INDEX)
tip_match = re.search(r'<h4>([^<]+)</h4>', INDEX)

issue_num = issue_match.group(1) if issue_match else "?"
date_str = date_match.group(1) if date_match else ""
editors_note = note_match.group(1).strip() if note_match else ""
tip_headline = tip_match.group(1) if tip_match else ""

partners_raw = os.environ.get("PARTNER_EMAILS_JSON", "{}")
try:
    partners = json.loads(partners_raw)
except json.JSONDecodeError as e:
    print(f"FATAL: PARTNER_EMAILS_JSON is not valid JSON: {e}", file=sys.stderr)
    sys.exit(1)

if not partners:
    print("No partners configured. Skipping.", file=sys.stderr)
    sys.exit(0)

app_password = os.environ["SPOCK_GMAIL_APP_PASSWORD"].replace(" ", "")
spock_email = os.environ["SPOCK_EMAIL"]
base_url = os.environ["DISPATCH_BASE_URL"].rstrip("/")
dry_run = os.environ.get("DRY_RUN", "").lower() == "true"

def build_email(code: str, name: str) -> tuple[str, str, str]:
    url = f"{base_url}/?p={code}"
    subject = f"The Chronos Dispatch · Issue {issue_num} · {date_str}"
    items_text = "\n".join(f"  {i+1}. {h}" for i, h in enumerate(headlines))
    text_body = f"""Good morning {name}.

Today's edition: {url}

{editors_note}

Six items cleared the bar:
{items_text}

Plus today's Workshop tip: {tip_headline}

— Spock

(Vote, comment, submit Finds inline. Your URL is unique so feedback attributes correctly.)
"""
    html_body = f"""<!DOCTYPE html>
<html><body style="font-family: Georgia, serif; max-width: 600px; margin: 0 auto; padding: 24px; color: #14110E;">
<p>Good morning {name}.</p>
<p><a href="{url}" style="display: inline-block; background: #6B1F2B; color: #F6F1E7; padding: 12px 20px; text-decoration: none; border-radius: 2px; font-family: monospace; letter-spacing: 0.1em; font-size: 12px;">OPEN TODAY'S DISPATCH →</a></p>
<p style="font-style: italic; color: #6C604F;">"{editors_note}"</p>
<p><strong>Six items cleared the bar:</strong></p>
<ol>{''.join(f'<li>{h}</li>' for h in headlines)}</ol>
<p><strong>Workshop tip:</strong> {tip_headline}</p>
<p style="color: #6C604F; font-size: 13px;">— Spock</p>
<p style="color: #6C604F; font-size: 11px; font-style: italic;">Vote, comment, and submit Finds inline. Your URL is unique so feedback attributes to you.</p>
</body></html>"""
    return subject, text_body, html_body

print(f"Issue {issue_num} · {date_str}")
print(f"Sending to {len(partners)} partners...")
if dry_run:
    print("DRY RUN — no emails will actually be sent.")

server = None
if not dry_run:
    server = smtplib.SMTP("smtp.gmail.com", 587)
    server.starttls()
    server.login(spock_email, app_password)

for code, info in partners.items():
    name = info["name"]
    email = info["email"]
    subject, text_body, html_body = build_email(code, name)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"Spock @ Chronos <{spock_email}>"
    msg["To"] = email
    msg.attach(MIMEText(text_body, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    if dry_run:
        print(f"  [DRY-RUN] would send to {name} <{email}>")
    else:
        server.sendmail(spock_email, email, msg.as_string())
        print(f"  Sent to {name} <{email}>")

if server:
    server.quit()
print("Done.")
