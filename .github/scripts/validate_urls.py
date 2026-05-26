"""Validate every source URL in index.html before email send."""
import re
import sys
import urllib.request
import urllib.error
from pathlib import Path

INDEX = Path("index.html").read_text(encoding="utf-8")

# Pull every source-link href and every watchlist href
source_urls = re.findall(r'class="source-link"[^>]*href="([^"]+)"', INDEX)
chart_source_urls = re.findall(r'class="source-link"\s+target="_blank"\s+href="([^"]+)"|href="([^"]+)"\s+class="source-link"', INDEX)
watchlist_urls = re.findall(r'class="watchlist-item"[^>]*>\s*<a href="([^"]+)"', INDEX)

# Be permissive about the regex — match all source-link hrefs robustly
all_source = re.findall(r'<a href="([^"]+)"[^>]*class="source-link"[^>]*>', INDEX)
all_source += re.findall(r'class="source-link"[^>]*target="_blank"[^>]*href="([^"]+)"', INDEX)

# Dedupe
source_urls = list(dict.fromkeys(source_urls + all_source))

print(f"Validating {len(source_urls)} source URLs from index.html...")

failures = []
for url in source_urls:
    if not url.startswith("http"):
        continue
    try:
        req = urllib.request.Request(url, method="HEAD",
                                     headers={"User-Agent": "Mozilla/5.0 (Spock Dispatch URL check)"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            code = resp.status
            if code >= 400:
                failures.append((url, code))
                print(f"  FAIL [{code}]  {url}")
            else:
                print(f"  OK   [{code}]  {url}")
    except urllib.error.HTTPError as e:
        # Some sites reject HEAD with 405 or 403 — fall back to GET
        if e.code in (403, 405, 501):
            try:
                req = urllib.request.Request(url, method="GET",
                                             headers={"User-Agent": "Mozilla/5.0 (Spock Dispatch URL check)"})
                with urllib.request.urlopen(req, timeout=10) as resp:
                    code = resp.status
                    if code >= 400:
                        failures.append((url, code))
                        print(f"  FAIL [{code}]  {url}")
                    else:
                        print(f"  OK   [{code} via GET]  {url}")
            except Exception as e2:
                failures.append((url, str(e2)))
                print(f"  FAIL [{e2}]  {url}")
        else:
            failures.append((url, e.code))
            print(f"  FAIL [{e.code}]  {url}")
    except Exception as e:
        failures.append((url, str(e)))
        print(f"  FAIL [{type(e).__name__}: {e}]  {url}")

if failures:
    print(f"\n{len(failures)} URL(s) failed validation. Halting send.")
    print("Failed URLs:")
    for url, err in failures:
        print(f"  {url}  ({err})")
    sys.exit(1)
else:
    print(f"\nAll {len(source_urls)} source URLs validated. Proceeding to send.")
