# test_proxy_search.py - Isolate WHY the real pipeline 403s through the proxy
# but this test did not. We hold the proxy IP constant and vary ONE thing at a
# time: the `origin` header, and the request order (cold homepage vs API-first).
#
# Run:  python test_proxy_search.py

from curl_cffi.requests import Session
from urllib.parse import urlencode
from config import PROXY_URL

BASE_URL = "https://www.kickstarter.com/discover/advanced"
HOME_URL = "https://www.kickstarter.com/"
KEYWORD = "travel bag"

API_HEADERS = {
    "accept": "application/json, text/javascript, */*; q=0.01",
    "accept-language": "en-GB,en-US;q=0.9,en;q=0.8",
    "origin": "https://www.kickstarter.com",
    "referer": "https://www.kickstarter.com/discover/advanced",
    "x-requested-with": "XMLHttpRequest",
}

# Exactly what the real warmup sends (note the extra "origin")
DOC_HEADERS_WITH_ORIGIN = {
    "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
    "accept-language": "en-GB,en-US;q=0.9,en;q=0.8",
    "referer": "https://www.kickstarter.com/",
    "origin": "https://www.kickstarter.com",
}

# What a real browser sends on a top-level navigation (no "origin")
DOC_HEADERS_NO_ORIGIN = {
    "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
    "accept-language": "en-GB,en-US;q=0.9,en;q=0.8",
    "referer": "https://www.kickstarter.com/",
}


def build_url():
    return f"{BASE_URL}?{urlencode({'google_chrome_workaround': '', 'term': KEYWORD, 'sort': 'newest', 'page': 1})}"


def new_session():
    s = Session(impersonate="chrome", timeout=30)
    if PROXY_URL:
        s.proxies = {"http": PROXY_URL, "https": PROXY_URL}
    return s


def fire(session, label, url, headers):
    try:
        r = session.get(url, headers=headers, allow_redirects=True, timeout=30)
        blocked = r.status_code == 403 or "Just a moment" in r.text
        print(f"  [{r.status_code}] {'❌ BLOCKED' if blocked else '✅ OK'}  {label}")
        return r
    except Exception as e:
        print(f"  [ERR] ❌ {label}: {e}")
        return None


if __name__ == "__main__":
    print(f"Proxy: {PROXY_URL.split('@')[1] if PROXY_URL else 'NONE'}\n")

    # CASE A: exact real-pipeline behaviour - fresh session, COLD homepage first,
    #         WITH the origin header. This is what 403s in main.
    print("CASE A: cold homepage first, WITH origin header (== real pipeline)")
    fire(new_session(), "homepage (cold, +origin)", HOME_URL, DOC_HEADERS_WITH_ORIGIN)

    # CASE B: same as A but drop the origin header. If this is OK, origin is the cause.
    print("\nCASE B: cold homepage first, NO origin header")
    fire(new_session(), "homepage (cold, no origin)", HOME_URL, DOC_HEADERS_NO_ORIGIN)

    # CASE C: API first (plants __cf_bm cookie), THEN homepage WITH origin.
    #         If A fails but C is OK, the cold-cookie order is the cause.
    print("\nCASE C: API call first, THEN homepage WITH origin header")
    s = new_session()
    fire(s, "api search (XHR)", build_url(), API_HEADERS)
    fire(s, "homepage (warm, +origin)", HOME_URL, DOC_HEADERS_WITH_ORIGIN)

    print("\nVerdict:")
    print("  A BLOCKED + B OK            -> the 'origin' header is the cause")
    print("  A BLOCKED + B BLOCKED + C OK-> cold request order / missing __cf_bm cookie is the cause")
    print("  A OK                        -> not reproducible; difference is elsewhere\n")
