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

INTRO_TEXT = """This is the first daily edition of The Chronos Dispatch.

Every weekday at ~06:00 SAST you'll get this email with a link to that day's
edition. Your URL has a "?p=" parameter unique to you — when you vote or
comment on items, the feedback attributes to you in the Notion feedback
database automatically. Each partner has their own code.

THREE ACTIONS YOU CAN TAKE INSIDE THE DISPATCH

  1. Vote thumbs-up / thumbs-down on each item with optional commentary.
     Spock learns from this and tunes future editions.
  2. Submit a Find — paste a URL with your take. It appears in tomorrow's
     edition tagged "Submitted by [your name]".
  3. Expand "Spock's take" on any item for deeper analysis and longitudinal
     threads back to prior editions.

WHY THIS WORKS

Spock harvests 25+ sources every morning (newsletters, research firms, the
world's-best-thinkers letters from Buffett / Ackman / Klarman / Howard Marks
/ Ferguson / Meeker) and scores each candidate item against five dimensions:
portfolio relevance, thesis fit, operator lessons, deal craft, novelty.

The bar Spock measures against is: "Would I have seen this otherwise? Did it
sharpen my thinking?" If an item doesn't pass that test, it shouldn't be here.

═══════════════════════════════════════════════════════════════════════════

"""

INTRO_HTML = """<h3 style="color: #6B1F2B; font-family: 'Playfair Display', Georgia, serif; margin-top: 28px;">Welcome to The Chronos Dispatch</h3>
<p>Every weekday at ~06:00 SAST you'll get this email with a link to that day's edition. Your URL has a <code style="background: #EDE5D2; padding: 2px 6px; border-radius: 2px;">?p=</code> parameter unique to you — when you vote or comment on items, the feedback attributes to you in the Notion feedback database automatically. Each partner has their own code.</p>

<h3 style="color: #6B1F2B; font-family: 'Playfair Display', Georgia, serif;">Three actions inside the dispatch</h3>
<ol>
<li><strong>Vote 👍 / 👎</strong> on each item with optional commentary. Spock learns from this and tunes future editions.</li>
<li><strong>Submit a Find</strong> — paste a URL with your take. It appears in tomorrow's edition tagged "Submitted by [your name]".</li>
<li><strong>Expand "Spock's take"</strong> on any item for deeper analysis and longitudinal threads back to prior editions.</li>
</ol>

<h3 style="color: #6B1F2B; font-family: 'Playfair Display', Georgia, serif;">Why this works</h3>
<p>Spock harvests 25+ sources every morning (newsletters, research firms, world's-best-thinkers letters from Buffett / Ackman / Klarman / Howard Marks / Ferguson / Meeker) and scores each candidate item against five dimensions: portfolio relevance, thesis fit, operator lessons, deal craft, novelty.</p>

<p>The bar Spock measures against is: <em style="color: #6B1F2B;">"Would I have seen this otherwise? Did it sharpen my thinking?"</em> If an item doesn't pass that test, it shouldn't be here.</p>

<hr style="border: none; border-top: 1px solid #BFB3A0; margin: 36px 0;">
"""

def build_email(code, name, email):
    url = f"{base_url}/?p={code}"
    subject = f"The Chronos Dispatch · Issue {int(issue_num):03d} · {date_str}"
    if is_first_send:
        subject += " · welcome"

    items_text = "\n".join(f"  {i+1}. {h}" for i, h in enumerate(headlines))

    text_body = f"""{name},

"""
    if is_first_send:
        text_body += INTRO_TEXT

    text_body += f"""TODAY'S EDITION

{url}

"{editors_note}"

{len(headlines)} items cleared the bar:
{items_text}

Plus today's Workshop tip: {tip_headline}

═══════════════════════════════════════════════════════════════════════════

If anything's off — voting doesn't work, formatting wrong, items off-pitch,
URL broken, email lands in spam — reply directly to this. The system tunes.

— Spock @ Chronos
"""

    items_html = "".join(f"<li>{h}</li>" for h in headlines)
    html_body = f"""<!DOCTYPE html>
<html><body style="font-family: Georgia, serif; max-width: 640px; margin: 0 auto; padding: 28px; color: #14110E; line-height: 1.65; background: #F6F1E7;">
<p style="font-size: 17px;">{name},</p>
"""
    if is_first_send:
        html_body += INTRO_HTML

    html_body += f"""<p style="text-align: center; margin: 28px 0;"><a href="{url}" style="display: inline-block; background: #6B1F2B; color: #F6F1E7; padding: 14px 32px; text-decoration: none; border-radius: 2px; font-family: 'IBM Plex Mono', monospace; letter-spacing: 0.14em; font-size: 13px;">OPEN ISSUE {int(issue_num):03d} →</a></p>

<p style="font-style: italic; color: #14110E; padding: 16px 20px; background: #EDE5D2; border-left: 3px solid #6B1F2B; margin: 20px 0;">"{editors_note}"</p>

<p><strong>{len(headlines)} items cleared the bar today:</strong></p>
<ol>{items_html}</ol>

<p><strong>Workshop tip:</strong> {tip_headline}</p>

<p style="margin-top: 36px; color: #14110E;">— Spock @ Chronos</p>

<p style="color: #6C604F; font-size: 12px; font-style: italic; margin-top: 24px;">If anything's off — voting doesn't work, formatting wrong, items off-pitch, URL broken, email lands in spam — reply directly to this. The system tunes.</p>
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
