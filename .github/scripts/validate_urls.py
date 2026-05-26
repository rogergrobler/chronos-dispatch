"""Validate every source URL in index.html before email send.

Philosophy: only fail on URLs that don't exist (404) or have unreachable
domains (DNS failure). Bot-protection blocks (401, 403, 429) or other 4xx/5xx
responses mean the URL is real — our bot is just being blocked. That's fine;
partners' browsers will reach the content. Treat those as warnings, not failures.
"""
import re
import socket
import sys
import urllib.error
import urllib.request
from pathlib import Path

INDEX = Path("index.html").read_text(encoding="utf-8")

# Source links inside .item articles only (not watchlist)
source_urls = re.findall(r'<a href="([^"]+)"[^>]*class="source-link"', INDEX)
source_urls = list(dict.fromkeys(source_urls))

print(f"Found {len(source_urls)} source URLs in index.html.")
for u in source_urls:
    print(f"  · {u}")
print()

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "identity",
}


def check_url(url):
    """Return (verdict, detail). Verdict is 'OK', 'WARN', or 'FAIL'."""
    if not url.startswith("http"):
        return "WARN", "non-http URL"

    last_error = "no method tried"
    for method in ("HEAD", "GET"):
        try:
            req = urllib.request.Request(url, method=method, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=15) as resp:
                return "OK", f"{resp.status} via {method}"
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return "FAIL", "404 Not Found"
            # Any other HTTP code means the URL EXISTS; pass with warning
            last_error = f"HTTP {e.code} via {method}"
            if method == "GET":
                return "WARN", f"{last_error} (URL exists, bot blocked)"
        except urllib.error.URLError as e:
            reason = str(e.reason)
            # DNS failure = the URL is fundamentally broken
            dns_markers = ("nodename nor servname", "Name or service not known",
                           "getaddrinfo failed", "Temporary failure in name resolution")
            if any(m in reason for m in dns_markers):
                return "FAIL", f"DNS failure: {reason}"
            last_error = f"network ({reason}) via {method}"
            if method == "GET":
                return "WARN", last_error
        except socket.timeout:
            last_error = f"timeout via {method}"
            if method == "GET":
                return "WARN", "timeout (URL probably exists)"
        except Exception as e:
            last_error = f"{type(e).__name__}: {e} via {method}"
            if method == "GET":
                return "WARN", last_error

    return "WARN", f"all methods inconclusive; last: {last_error}"


failures = []
warnings = []

for url in source_urls:
    verdict, detail = check_url(url)
    marker = {"OK": "✓", "WARN": "~", "FAIL": "✗"}.get(verdict, "?")
    print(f"  [{marker}] {verdict:5} {detail:55}  {url}")
    if verdict == "FAIL":
        failures.append((url, detail))
    elif verdict == "WARN":
        warnings.append((url, detail))

print()
print(f"Checked {len(source_urls)} URLs · {len(failures)} hard failure(s) · {len(warnings)} warning(s)")

if failures:
    print("\nHARD FAILURES (halting send):", file=sys.stderr)
    for url, err in failures:
        print(f"  {url}  ({err})", file=sys.stderr)
    sys.exit(1)

print("\nValidation passed. Proceeding to send.")
sys.exit(0)
