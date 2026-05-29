# test_graphql_debug.py - Automatic Cookie Collection Test
# Test GraphQL endpoint WITHOUT hardcoded cookies
# 1. Visit homepage -> collect cookies from Set-Cookie headers
# 2. Visit discovery page -> update cookies
# 3. Visit project page -> extract CSRF from HTML
# 4. POST GraphQL with collected cookies (automatic via session)

from curl_cffi.requests import Session
import time
import json
import logging
import re

# Setup basic logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - [%(levelname)s] - %(message)s')
logger = logging.getLogger(__name__)

# Different impersonate versions to test
IMPERSONATE_VERSIONS = [
    "chrome",           # Latest Chrome (WORKS ✅)
    "chrome136",        # Chrome 136 (WORKS ✅)
    "safari",           # Safari (WORKS ✅)
]

# Test constants
GRAPHQL_URL = "https://www.kickstarter.com/graph"
HOMEPAGE_URL = "https://www.kickstarter.com/"
DISCOVERY_URL = "https://www.kickstarter.com/discover/advanced"
TEST_SLUG = "1207952088/reusable-grocery-shopping-bag-thats-not-pain-in-the-hand"
PROJECT_URL = f"https://www.kickstarter.com/projects/{TEST_SLUG}"


GRAPHQL_QUERY = """
query GetCompleteProjectData($slug: String!) {
  project(slug: $slug) {
    risks
    story(assetWidth: 680)
    environmentalCommitments {
      commitmentCategory
      description
    }
    creator {
      id
      url
      location {
        displayableName
      }
      launchedProjects {
        totalCount
      }
    }
    comments {
      totalCount
    }
  }
}
"""


def extract_csrf_from_html(html_content):
    """Extract CSRF token from HTML meta tag"""
    match = re.search(r'<meta name=["\']csrf-token["\'] content=["\']([^"\']+)["\']', html_content)
    if match:
        token = match.group(1)
        logger.info(f"[CSRF] Extracted: {token[:25]}...")
        return token
    logger.warning("[CSRF] Could not extract CSRF token from HTML")
    return None


def test_with_automatic_cookies(impersonate_version):
    """Test GraphQL with automatic cookie collection (no hardcoded cookies)"""
    logger.info(f"\n{'='*80}")
    logger.info(f"Testing with impersonate='{impersonate_version}'")
    logger.info(f"{'='*80}")
    
    try:
        # Step 1: Create fresh session (curl_cffi will manage cookies automatically)
        session = Session(impersonate=impersonate_version, timeout=30)
        logger.info(f"[SESSION] Created fresh session with impersonate='{impersonate_version}'")
        
        # Step 2: Visit homepage to collect initial cookies
        logger.info(f"[WARMUP_1] Visiting homepage: {HOMEPAGE_URL}")
        home_response = session.get(
            HOMEPAGE_URL,
            headers={
                "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
                "accept-language": "en-GB,en-US;q=0.9,en;q=0.8",
                "referer": "https://www.kickstarter.com/",
            },
            allow_redirects=True,
            timeout=30
        )
        logger.info(f"[WARMUP_1] Status: {home_response.status_code}")
        
        # curl_cffi Session automatically stores Set-Cookie headers!
        logger.debug(f"[SESSION_COOKIES] Cookies collected from homepage")
        
        # Small delay between requests
        time.sleep(2)
        
        # Step 3: Visit discovery page to refresh cookies
        logger.info(f"[WARMUP_2] Visiting discovery page: {DISCOVERY_URL}")
        discovery_response = session.get(
            DISCOVERY_URL,
            headers={
                "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
                "accept-language": "en-GB,en-US;q=0.9,en;q=0.8",
                "referer": HOMEPAGE_URL,
            },
            allow_redirects=True,
            timeout=30
        )
        logger.info(f"[WARMUP_2] Status: {discovery_response.status_code}")
        logger.debug(f"[SESSION_COOKIES] Cookies updated from discovery page")
        
        time.sleep(2)
        
        # Step 4: Visit project page to extract fresh CSRF token
        logger.info(f"[PROJECT_PAGE] Visiting: {PROJECT_URL}")
        project_response = session.get(
            PROJECT_URL,
            headers={
                "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
                "accept-language": "en-GB,en-US;q=0.9,en;q=0.8",
                "referer": DISCOVERY_URL,
            },
            allow_redirects=True,
            timeout=30
        )
        logger.info(f"[PROJECT_PAGE] Status: {project_response.status_code}")
        
        # Extract CSRF token from project page HTML
        csrf_token = extract_csrf_from_html(project_response.text)
        if not csrf_token:
            logger.error("[CSRF] Failed to extract CSRF token - aborting")
            return False
        
        logger.debug(f"[SESSION_COOKIES] Cookies updated from project page (includes Cloudflare)")
        
        time.sleep(2)
        
        # Step 5: POST GraphQL with collected cookies (NO manual Cookie header needed!)
        logger.info(f"[GRAPHQL] Posting to GraphQL endpoint")
        
        graphql_headers = {
            "accept": "*/*",
            "accept-language": "en-GB,en-US;q=0.9,en;q=0.8",
            "content-type": "application/json",
            "origin": "https://www.kickstarter.com",
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
            "x-csrf-token": csrf_token,
            # NO "cookie" header - session handles it automatically!
        }
        
        payload = {
            "query": GRAPHQL_QUERY,
            "variables": {"slug": TEST_SLUG}
        }
        
        response = session.post(
            GRAPHQL_URL,
            json=payload,
            headers=graphql_headers,
            allow_redirects=True,
            timeout=30
        )
        
        logger.info(f"[GRAPHQL] Status: {response.status_code}")
        
        # Step 6: Check response
        if response.status_code == 200:
            try:
                data = response.json()
                if "errors" in data:
                    logger.error(f"[GRAPHQL] GraphQL errors: {data['errors']}")
                    return False
                else:
                    logger.info(f"[GRAPHQL] ✅ SUCCESS - Valid GraphQL response received!")
                    logger.info(f"[GRAPHQL] Project data: {data.get('data', {}).get('project', {}).get('name', 'Unknown')}")
                    return True
            except json.JSONDecodeError as e:
                logger.error(f"[GRAPHQL] Invalid JSON response: {e}")
                return False
        elif response.status_code == 403:
            logger.warning(f"[GRAPHQL] ❌ Cloudflare block (403) - cookies may be insufficient")
            return False
        else:
            logger.error(f"[GRAPHQL] Unexpected status {response.status_code}")
            logger.debug(f"[GRAPHQL] Response (first 200 chars): {response.text[:200]}")
            return False
    
    except Exception as e:
        logger.error(f"[ERROR] Test failed with exception: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


if __name__ == "__main__":
    logger.info("\n" + "="*80)
    logger.info("GraphQL Test: Automatic Cookie Collection (No Hardcoded Cookies)")
    logger.info("="*80)
    logger.info(f"\nTesting with {len(IMPERSONATE_VERSIONS)} impersonate versions:")
    logger.info(f"  {IMPERSONATE_VERSIONS}")
    logger.info(f"\nFlow:")
    logger.info(f"  1. Homepage (collect initial cookies)")
    logger.info(f"  2. Discovery page (update cookies)")
    logger.info(f"  3. Project page (extract CSRF + Cloudflare cookies)")
    logger.info(f"  4. GraphQL POST (use session cookies automatically)")
    logger.info(f"\n{'='*80}\n")
    
    results = {}
    
    for impersonate in IMPERSONATE_VERSIONS:
        success = test_with_automatic_cookies(impersonate)
        results[impersonate] = "✅ SUCCESS" if success else "❌ FAILED"
        
        # Wait between tests
        time.sleep(3)
    
    # Summary
    logger.info("\n" + "="*80)
    logger.info("TEST SUMMARY")
    logger.info("="*80)
    for impersonate, result in results.items():
        logger.info(f"  {impersonate:15} -> {result}")
    
    logger.info("="*80)
    logger.info("\nNOTE: Successful tests demonstrate automatic cookie handling!")
    logger.info("The session collects Set-Cookie headers automatically from each response.")
    logger.info("GraphQL requests then use these cookies without manual Cookie headers.")
