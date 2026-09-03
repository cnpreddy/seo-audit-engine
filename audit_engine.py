#!/usr/bin/env python3
"""
Local SEO Audit Engine (prototype v1)

Fetches a business website and runs a set of on-page SEO / technical checks
relevant to local service businesses (plumbers, dentists, contractors, etc).
Outputs a structured JSON result with a 0-100 score and prioritized findings.

Usage:
    python3 audit_engine.py --url https://example.com --name "Acme Plumbing" \
        --city "Austin, TX" --out report_data.json
"""
import argparse
import json
import re
import ssl
import socket
import sys
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

HEADERS = {
    # A real browser UA — many sites (Wix, Squarespace, Cloudflare-protected
    # sites) silently return an empty or near-empty page to obvious bot UAs
    # instead of an error, which used to make this tool report false
    # "no title / no H1 / everything missing" results for those sites.
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"),
    "Accept": ("text/html,application/xhtml+xml,application/xml;q=0.9,"
               "image/webp,*/*;q=0.8"),
    "Accept-Language": "en-US,en;q=0.9",
    # Deliberately omit brotli (br) — some environments lack a brotli
    # decoder, which can silently yield an empty/garbled body.
    "Accept-Encoding": "gzip, deflate",
}

MIN_VALID_HTML_LENGTH = 500

# Each check returns: (passed: bool, weight: int, label: str, detail: str, fix: str)
CHECKS = []


def check(weight, label):
    def decorator(fn):
        CHECKS.append((weight, label, fn))
        return fn
    return decorator


def fetch(url, timeout=15):
    resp = requests.get(url, headers=HEADERS, timeout=timeout, allow_redirects=True)
    resp.raise_for_status()
    return resp


def get_ssl_info(hostname, port=443, timeout=8):
    try:
        ctx = ssl.create_default_context()
        with socket.create_connection((hostname, port), timeout=timeout) as sock:
            with ctx.wrap_socket(sock, server_hostname=hostname):
                return True
    except Exception:
        return False


def run_audit(url, business_name=None, city=None):
    parsed = urlparse(url if url.startswith("http") else f"https://{url}")
    hostname = parsed.hostname
    results = []
    score_total = 0
    score_max = 0

    # --- Fetch page ---
    try:
        resp = fetch(url if url.startswith("http") else f"https://{url}")
        html = resp.text
        if len(html.strip()) < MIN_VALID_HTML_LENGTH:
            raise ValueError(
                f"Response body was only {len(html.strip())} characters — this "
                "usually means the site blocked the request (bot/WAF protection) "
                "or requires JavaScript to render, not that the page is actually "
                "empty. Results below would be unreliable, so this audit stopped "
                "rather than report false findings."
            )
        soup = BeautifulSoup(html, "html.parser")
        fetch_ok = True
    except Exception as e:
        results.append({
            "label": "Website reachable",
            "passed": False,
            "weight": 20,
            "detail": f"Could not reliably load the site: {e}",
            "fix": "Ensure the website is online and accessible over HTTPS. If it "
                   "uses bot protection (Cloudflare, etc.), this tool may need to "
                   "be allowlisted or use a headless browser instead.",
        })
        return {
            "url": url, "business_name": business_name, "city": city,
            "score": 0, "max_score": 20, "checks": results,
            "fetch_failed": True,
        }

    def add(weight, label, passed, detail, fix):
        nonlocal score_total, score_max
        score_max += weight
        if passed:
            score_total += weight
        results.append({
            "label": label, "passed": passed, "weight": weight,
            "detail": detail, "fix": (None if passed else fix),
        })

    # --- Suspicious-page detection ---
    # A bot-protection challenge page (Cloudflare "Just a moment...", a CAPTCHA
    # wall, etc.) can easily be several KB — long enough to pass the raw length
    # guard above — while still having none of a real page's basic signals.
    # Rather than silently score that as "this business has zero SEO" (false
    # and misleading), detect it and report an honest "couldn't verify" result.
    title_raw = soup.title.string.strip() if soup.title and soup.title.string else ""
    meta_desc_tag_raw = soup.find("meta", attrs={"name": "description"})
    meta_desc_raw = meta_desc_tag_raw.get("content", "").strip() if meta_desc_tag_raw else ""
    h1s_raw = soup.find_all("h1")

    # NOTE: these markers are used only to make the failure message more
    # specific — they must NEVER trigger on their own. Words like "captcha"
    # or "access denied" show up on plenty of completely normal sites (a
    # reCAPTCHA widget on a contact form, boilerplate error-handling JS,
    # etc.), so gating on them alone caused false positives on real,
    # perfectly fine sites. The only real trigger is looks_empty_of_signals.
    CHALLENGE_MARKERS = [
        "just a moment", "checking your browser", "cf-browser-verification",
        "enable javascript and cookies", "attention required",
        "verify you are a human", "ray id",
    ]
    lower_html = html.lower()
    looks_like_challenge = any(m in lower_html for m in CHALLENGE_MARKERS)
    looks_empty_of_signals = (not title_raw) and (not meta_desc_raw) and (len(h1s_raw) == 0)

    if looks_empty_of_signals:
        reason = ("a bot-protection/challenge page was detected in the response, "
                   "and the page has no title, meta description, or H1 tag"
                   if looks_like_challenge else
                   "the page has no title, no meta description, and no H1 tag "
                   "at all — extremely unusual for a real business homepage, "
                   "and much more likely to mean the request was blocked or "
                   "served a JavaScript-only shell than that the page is "
                   "genuinely blank")
        results.append({
            "label": "Website reachable",
            "passed": False,
            "weight": 20,
            "detail": f"Could not reliably audit this site: {reason}.",
            "fix": "This site may be behind bot protection (Cloudflare, etc.) or "
                   "require JavaScript to render its real content. Try verifying "
                   "manually in a browser, or this tool may need a headless-"
                   "browser fetcher instead of a plain HTTP request for this site.",
        })
        return {
            "url": url, "business_name": business_name, "city": city,
            "score": 0, "max_score": 20, "checks": results,
            "fetch_failed": True,
        }

    # 1. HTTPS / SSL
    https_ok = url.startswith("https://") or get_ssl_info(hostname)
    add(10, "Secure connection (HTTPS)", https_ok,
        "Site loads over HTTPS." if https_ok else "Site is not served over HTTPS.",
        "Install an SSL certificate and force all traffic to HTTPS. Google penalizes insecure sites in rankings.")

    # 2. Title tag
    title = title_raw
    title_ok = 10 <= len(title) <= 65
    add(10, "Title tag present & well-sized", title_ok,
        f"Title: \"{title}\" ({len(title)} chars)." if title else "No <title> tag found.",
        "Write a unique title (50-60 characters) that includes your business type and city, e.g. 'Acme Plumbing | 24/7 Plumber in Austin, TX'.")

    # 3. Meta description
    meta_desc = meta_desc_raw
    meta_ok = 50 <= len(meta_desc) <= 165
    add(8, "Meta description present & well-sized", meta_ok,
        f"Meta description: \"{meta_desc[:100]}...\" ({len(meta_desc)} chars)." if meta_desc else "No meta description found.",
        "Add a 120-160 character meta description summarizing your services and service area to improve click-through from search results.")

    # 4. H1 tag
    h1s = h1s_raw
    h1_ok = len(h1s) == 1
    add(6, "Single, clear H1 heading", h1_ok,
        f"Found {len(h1s)} H1 tag(s)." + (f" Text: \"{h1s[0].get_text(strip=True)}\"" if h1s else ""),
        "Use exactly one H1 per page that clearly states what the business does and where.")

    # 5. Mobile viewport
    viewport = soup.find("meta", attrs={"name": "viewport"})
    add(10, "Mobile-friendly viewport tag", viewport is not None,
        "Viewport meta tag present." if viewport else "No mobile viewport meta tag found.",
        "Add <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\"> so the site renders properly on phones — most local searches happen on mobile.")

    # 6. LocalBusiness schema markup
    schema_scripts = soup.find_all("script", attrs={"type": "application/ld+json"})
    has_local_schema = False
    for s in schema_scripts:
        try:
            data = json.loads(s.string or "{}")
            blob = json.dumps(data).lower()
            if "localbusiness" in blob or "@type" in blob and any(
                t in blob for t in ["plumber", "dentist", "restaurant", "store", "professionalservice"]
            ):
                has_local_schema = True
        except Exception:
            continue
    add(12, "LocalBusiness structured data (schema.org)", has_local_schema,
        "Found structured LocalBusiness markup." if has_local_schema else "No LocalBusiness schema.org markup detected.",
        "Add JSON-LD LocalBusiness schema with your name, address, phone, hours, and service area — this helps Google show rich results and understand your business.")

    # 7. NAP (Name, Address, Phone) visible on page
    page_text = soup.get_text(" ", strip=True)
    phone_match = re.search(r"(\(?\d{3}\)?[\s\-.]?\d{3}[\s\-.]?\d{4})", page_text)
    address_hint = re.search(r"\d{1,6}\s+\w+.{0,30}(street|st\.|ave|avenue|road|rd\.|blvd|suite|ste)", page_text, re.I)
    nap_ok = bool(phone_match) and bool(address_hint)
    add(10, "Name/Address/Phone (NAP) visible on page", nap_ok,
        f"Phone found: {'yes' if phone_match else 'no'}; address found: {'yes' if address_hint else 'no'}.",
        "Display your full business name, physical address, and phone number in the page footer or header (not just a contact form) — this is a core local ranking signal.")

    # 8. Image alt text coverage
    imgs = soup.find_all("img")
    if imgs:
        with_alt = sum(1 for i in imgs if i.get("alt", "").strip())
        alt_ratio = with_alt / len(imgs)
    else:
        alt_ratio = 1.0
    alt_ok = alt_ratio >= 0.8
    add(6, "Image alt text coverage", alt_ok,
        f"{int(alt_ratio*100)}% of images have descriptive alt text ({with_alt if imgs else 0}/{len(imgs)}).",
        "Add descriptive alt text to images (e.g. 'licensed plumber repairing water heater in Austin TX') to help image search and accessibility.")

    # 9. Canonical tag
    canonical = soup.find("link", attrs={"rel": "canonical"})
    add(4, "Canonical tag present", canonical is not None,
        "Canonical tag present." if canonical else "No canonical tag found.",
        "Add a <link rel=\"canonical\"> tag to avoid duplicate content issues across URL variants.")

    # 10. Page weight (proxy for speed)
    page_kb = len(html.encode("utf-8")) / 1024
    weight_ok = page_kb < 500
    add(6, "Reasonable page size (speed proxy)", weight_ok,
        f"HTML payload is {page_kb:.0f} KB.",
        "Trim unused scripts/styles and compress images — heavy pages hurt mobile load speed, which affects both rankings and conversion.")

    # 11. City/location mentioned in visible text
    city_ok = True
    if city:
        city_ok = city.split(",")[0].strip().lower() in page_text.lower()
        add(8, "City/service area mentioned on page", city_ok,
            f"'{city.split(',')[0].strip()}' {'was' if city_ok else 'was NOT'} found in visible page text.",
            f"Explicitly mention '{city}' and nearby neighborhoods in your headings and body copy — local relevance is a major local-pack ranking factor.")

    # 12. Contact/CTA presence
    cta_words = ["call", "book", "schedule", "contact", "get a quote", "request"]
    cta_ok = any(w in page_text.lower() for w in cta_words)
    add(6, "Clear call-to-action present", cta_ok,
        "Found call-to-action language on the page." if cta_ok else "No obvious call-to-action found.",
        "Add a prominent call-to-action ('Call Now', 'Book a Free Estimate') near the top of the page.")

    pct = round(100 * score_total / score_max) if score_max else 0

    return {
        "url": url,
        "business_name": business_name,
        "city": city,
        "score": pct,
        "raw_score": score_total,
        "max_score": score_max,
        "checks": results,
    }


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", required=True)
    ap.add_argument("--name", default=None)
    ap.add_argument("--city", default=None)
    ap.add_argument("--out", default="report_data.json")
    args = ap.parse_args()

    result = run_audit(args.url, args.name, args.city)
    with open(args.out, "w") as f:
        json.dump(result, f, indent=2)
    print(json.dumps(result, indent=2))
