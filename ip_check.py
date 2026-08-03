# ip_check.py - One-time IP check before the pipeline runs
#
# The scraper goes out through the proxy IP in .env. If that IP is dead (proxy
# down / credentials wrong) or banned by Cloudflare, every request fails and the
# whole run is wasted. This checks it ONCE at startup:
#
#   IP works  -> pipeline runs
#   IP fails  -> pipeline stops, nothing is processed
#
# Manual test:  python ip_check.py

from urllib.parse import urlencode

from config import logger, PROXY_URL, BASE_URL, KEYWORDS
from session_utils import create_session

# Headers used for the Kickstarter test request (same as the pipeline's search)
PROBE_HEADERS = {
    "accept": "application/json, text/javascript, */*; q=0.01",
    "accept-language": "en-GB,en-US;q=0.9,en;q=0.8",
    "origin": "https://www.kickstarter.com",
    "referer": "https://www.kickstarter.com/discover/advanced",
    "x-requested-with": "XMLHttpRequest",
}


def check_ip():
    """Check once whether the outbound IP works

    Two quick requests through the same session type the pipeline uses:
      1. api.ipify.org  -> shows which IP we are going out from (proxy alive?)
      2. Kickstarter discover API -> is that IP served, or Cloudflare-blocked?

    Returns:
        bool: True if the IP works and scraping can proceed, False otherwise
    """
    logger.info("\n" + "=" * 80)
    logger.info("🌐 IP CHECK")
    logger.info("=" * 80)

    if PROXY_URL:
        logger.info(f"Proxy: http://***:***@{PROXY_URL.split('@')[1]}")
    else:
        logger.info("Proxy: none configured (direct connection)")

    session = create_session(impersonate="chrome", timeout=30)

    # ---------- 1. Which IP are we going out from? ----------
    try:
        response = session.get("https://api.ipify.org", timeout=15)
        current_ip = response.text.strip()
        logger.info(f"✅ Outbound IP: {current_ip}")
    except Exception as e:
        logger.error(f"❌ IP CHECK FAILED: cannot reach the internet ({e})")
        if PROXY_URL:
            logger.error("   The proxy is down, unreachable, or the credentials are wrong.")
        return False

    # ---------- 2. Does Kickstarter serve this IP? ----------
    probe_url = f"{BASE_URL}?{urlencode({'google_chrome_workaround': '', 'term': KEYWORDS[0], 'sort': 'newest', 'page': 1})}"

    try:
        response = session.get(probe_url, headers=PROBE_HEADERS, allow_redirects=True, timeout=30)
    except Exception as e:
        logger.error(f"❌ IP CHECK FAILED: Kickstarter request failed from IP {current_ip} ({e})")
        return False

    if response.status_code == 403 or "Just a moment" in response.text:
        logger.error(f"❌ IP CHECK FAILED: Kickstarter blocked IP {current_ip} (HTTP {response.status_code})")
        logger.error("   This IP is banned or challenged by Cloudflare - change the proxy IP.")
        return False

    if response.status_code != 200:
        logger.error(f"❌ IP CHECK FAILED: Kickstarter returned HTTP {response.status_code} for IP {current_ip}")
        return False

    try:
        projects = response.json().get("projects", [])
    except Exception:
        logger.error(f"❌ IP CHECK FAILED: Kickstarter did not return JSON for IP {current_ip} (blocked page)")
        return False

    logger.info(f"✅ Kickstarter reachable from {current_ip} ({len(projects)} projects visible)")
    logger.info("✅ IP CHECK PASSED - starting pipeline")
    logger.info("=" * 80 + "\n")
    return True


if __name__ == "__main__":
    import sys
    sys.exit(0 if check_ip() else 1)
