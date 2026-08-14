# ip_check.py - IP check before the pipeline runs
#
# The scraper goes out through the proxy IP in .env. If that proxy is dead
# (down / credentials wrong / port blocked), every request fails and the whole
# run is wasted. This checks the outbound IP 3 times BEFORE scraping starts:
#
#   at least 1 of 3 checks works -> pipeline runs
#   all 3 checks fail            -> pipeline stops, nothing is processed
#
# The check NEVER touches Kickstarter. It only asks neutral "what is my IP"
# services, so a Kickstarter/Cloudflare hiccup can never abort a run, and we
# don't spend one of our Kickstarter requests on a health check.
#
# Manual test:  python ip_check.py

import ipaddress
import time

from config import logger, PROXY_URL, get_env
from session_utils import create_session

# One neutral endpoint per attempt - all return the caller's IP as plain text.
# Deliberately three DIFFERENT services: hitting the same one 3 times would fail
# together if that single service is down or rate-limiting our static IP.
IP_ENDPOINTS = [
    "https://api.ipify.org",
    "https://icanhazip.com",
    "https://ifconfig.me/ip",   # the /ip path returns plain text (the bare host returns HTML)
]

ATTEMPT_TIMEOUT = 8   # seconds per attempt - keep the failure path fast
ATTEMPT_DELAY = 2     # seconds between attempts


def _probe_ip(url):
    """Ask one endpoint for our outbound IP

    Returns:
        str | None: The IP as a string, or None if the request failed or the
                    response body was not a valid IP (proxy error page, HTML,
                    captive portal, etc.)
    """
    session = create_session(impersonate="chrome", timeout=ATTEMPT_TIMEOUT)

    try:
        response = session.get(url, timeout=ATTEMPT_TIMEOUT)
    except Exception as e:
        logger.warning(f"   ⚠️  {url} -> request failed ({e})")
        return None

    if response.status_code != 200:
        logger.warning(f"   ⚠️  {url} -> HTTP {response.status_code}")
        return None

    body = response.text.strip()

    # A 200 is not enough: a broken proxy returns an HTML error page with 200.
    # Only a body that actually parses as an IP counts as a working IP.
    try:
        ip = str(ipaddress.ip_address(body))
    except ValueError:
        logger.warning(f"   ⚠️  {url} -> HTTP 200 but body is not an IP: {body[:80]!r}")
        return None

    return ip


def check_ip():
    """Check the outbound IP 3 times before the pipeline runs

    Each attempt uses a different neutral IP-echo service, so one dead service
    cannot fail the whole check. Kickstarter is never contacted here.

    The run proceeds if at least one attempt returns a valid IP - one flaky
    request should not throw away a scheduled run. It stops only if all 3
    attempts fail, which means the proxy really is unreachable.

    Returns:
        bool: True if the IP works and scraping can proceed, False otherwise
    """
    logger.info("\n" + "=" * 80)
    logger.info("🌐 IP CHECK (3 attempts, Kickstarter not contacted)")
    logger.info("=" * 80)

    if PROXY_URL:
        logger.info(f"Proxy: http://***:***@{PROXY_URL.split('@')[1]}")
    else:
        logger.info("Proxy: none configured (direct connection)")

    found_ips = []

    for attempt, url in enumerate(IP_ENDPOINTS, start=1):
        logger.info(f"Attempt {attempt}/{len(IP_ENDPOINTS)}: {url}")

        ip = _probe_ip(url)
        if ip:
            found_ips.append(ip)
            logger.info(f"   ✅ Outbound IP: {ip}")

        if attempt < len(IP_ENDPOINTS):
            time.sleep(ATTEMPT_DELAY)

    # ---------- All 3 failed: the proxy/connection is down ----------
    if not found_ips:
        logger.error(f"❌ IP CHECK FAILED: all {len(IP_ENDPOINTS)} attempts failed")
        if PROXY_URL:
            logger.error("   The proxy is down, unreachable, or the credentials are wrong.")
        else:
            logger.error("   No internet connection.")
        logger.info("=" * 80 + "\n")
        return False

    # ---------- At least one worked: the IP is usable ----------
    # Everything below is informational only - it never fails the check.
    if len(set(found_ips)) > 1:
        logger.warning(f"⚠️  Outbound IP was not stable across attempts: {found_ips}")
        logger.warning("   The proxy may be rotating IPs instead of serving a static one.")

    # Only comparable when PROXY_IP is a literal IP - it is often a gateway
    # hostname (e.g. geo.iproyal.com), which never matches an exit IP.
    proxy_ip = (get_env("PROXY_IP") or "").strip()
    try:
        ipaddress.ip_address(proxy_ip)
    except ValueError:
        proxy_ip = None

    if proxy_ip and proxy_ip not in found_ips:
        logger.warning(f"⚠️  Outbound IP {found_ips[0]} != PROXY_IP {proxy_ip}")
        logger.warning("   Normal for gateway-style proxies (they exit on a different IP).")

    logger.info(f"✅ IP CHECK PASSED ({len(found_ips)}/{len(IP_ENDPOINTS)} attempts OK) - starting pipeline")
    logger.info("=" * 80 + "\n")
    return True


if __name__ == "__main__":
    import sys
    sys.exit(0 if check_ip() else 1)
