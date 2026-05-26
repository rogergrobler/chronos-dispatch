"""URL validation — informational only.

Logs each URL's status. Does NOT block the send. Real URL validation must
happen at generation-time in the harvest script (where we can find
alternatives or drop items). Send-time blocking turns minor issues into
total failures, which is worse than letting one broken link through.
"""
import re
import socket
import sys
import urllib.error
import urllib.request
from pathlib import Path

INDEX = Path("index.html").read_text(encoding="utf-8")
source_urls = re.findall(r'<a href="([^"]+)"[^>]*class="source-link"', INDEX)
source_urls = list(dict.fromkeys(source_urls))

print(f"Checking {len(source_urls)} source URLs (informational only — does not block send)\n")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
}

for url in source_urls:
    status = "?"
    detail = ""
    if not url.startswith("http"):
        print(f"  [SKIP] non-http  {url}")
        continue
    for method in ("HEAD", "GET"):
        try:
            req = urllib.request.Request(url, method=method, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=15) as resp:
                status = "OK"
                detail = f"{resp.status} via {method}"
                break
        except urllib.error.HTTPError as e:
            status = "WARN" if e.code != 404 else "FAIL"
            detail = f"HTTP {e.code} via {method}"
            if method == "GET" or e.code == 404:
                break
        except urllib.error.URLError as e:
            status = "WARN"
            detail = f"network via {method}: {e.reason}"
            if method == "GET":
                break
        except Exception as e:
            status = "WARN"
            detail = f"{type(e).__name__} via {method}: {e}"
            if method == "GET":
                break

    marker = {"OK": "✓", "WARN": "~", "FAIL": "✗"}.get(status, "?")
    print(f"  [{marker}] {status:5} {detail:55}  {url}")

print("\nURL check complete (informational). Proceeding to send.")
sys.exit(0)
