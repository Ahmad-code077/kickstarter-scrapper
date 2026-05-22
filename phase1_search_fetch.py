# phase1_search_fetch.py - Phase 1a (Search) and 1b (Fetch GraphQL)

from curl_cffi.requests import Session
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode
import time
import json

from config import (
    logger, KEYWORDS, DAYS_BACK, MAX_PAGES, REQUEST_DELAY,
    KICKSTARTER_CSRF_TOKEN, KICKSTARTER_COOKIES,
    BASE_URL, GRAPHQL_URL
)


# ==================== PHASE 1A: SEARCH ====================

def build_discovery_url(keyword, page=1):
    """Build discovery API URL"""
    params = {
        "google_chrome_workaround": "",
        "term": keyword,
        "sort": "newest",
        "page": page,
    }
    return f"{BASE_URL}?{urlencode(params)}"


def ts_to_datetime(ts):
    """Convert timestamp to datetime"""
    return datetime.fromtimestamp(ts, tz=timezone.utc)


def is_cloudflare_blocked(text):
    """Check if response is blocked by Cloudflare"""
    checks = [
        "Just a moment",
        "challenge-platform",
        "cf-browser-verification",
        "/cdn-cgi/challenge-platform",
    ]
    return any(c in text for c in checks)


def fetch_with_retry(session, url, max_retries=3, backoff_factor=2):
    """Fetch URL with retry logic and exponential backoff"""
    for attempt in range(max_retries):
        try:
            logger.debug(f"[FETCH] Attempt {attempt + 1}/{max_retries}: {url}")
            response = session.get(url, allow_redirects=True)
            logger.debug(f"[RESPONSE] Status: {response.status_code}")
            return response
        except Exception as e:
            logger.debug(f"[ERROR] Attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                wait_time = (backoff_factor ** attempt)
                logger.debug(f"[RETRY] Waiting {wait_time}s before retry...")
                time.sleep(wait_time)
            else:
                logger.error(f"[FAILED] All {max_retries} attempts failed for {url}")
                raise
    return None


def extract_discovery_project(project):
    """Extract simplified project data from discovery API"""
    creator = project.get("creator") or {}
    creator_id = creator.get("id")
    project_slug = project.get("slug", "")
    full_slug = f"{creator_id}/{project_slug}" if creator_id else project_slug
    
    photo = project.get("photo") or {}
    main_image = photo.get("full")
    
    urls = project.get("urls") or {}
    web = urls.get("web") or {}
    project_url = web.get("project")
    
    location = project.get("location") or {}
    location_name = location.get("displayable_name") or location.get("name")
    
    usd_pledged = project.get("usd_pledged")
    if usd_pledged:
        usd_pledged = str(round(float(usd_pledged), 2))
    
    logger.debug(f"[EXTRACT] Project ID: {project.get('id')}, Slug: {full_slug}")
    
    return {
        "project_id": project.get("id"),
        "project_name": project.get("name"),
        "blurb": project.get("blurb"),
        "goal": project.get("goal"),
        "pledged": project.get("pledged"),
        "usd_pledged": usd_pledged,
        "backers_count": project.get("backers_count"),
        "percent_funded": project.get("percent_funded"),
        "state": project.get("state"),
        "deadline": project.get("deadline"),
        "launched_at": project.get("launched_at"),
        "created_at": project.get("created_at"),
        "staff_pick": project.get("staff_pick", False),
        "country": project.get("country"),
        "currency": project.get("currency", "USD"),
        "main_image": main_image,
        "project_url": project_url,
        "slug": full_slug,
        "creator_name": creator.get("name"),
        "location": location_name,
    }


def search_phase():
    """Phase 1a: Search for projects across all keywords"""
    logger.info("\n📍 PHASE 1a: SEARCH")
    logger.info("-" * 80)
    
    headers = {
        "accept": "application/json, text/javascript, */*; q=0.01",
        "accept-language": "en-GB,en-US;q=0.9,en;q=0.8",
        "x-requested-with": "XMLHttpRequest",
        "referer": "https://www.kickstarter.com/discover/advanced",
        "user-agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/136.0.0.0 Safari/537.36"
        ),
    }
    
    session = Session(impersonate="chrome136", headers=headers, timeout=30)
    all_projects = []
    seen_ids = set()
    
    utc_now = datetime.now(timezone.utc)
    from_date = utc_now - timedelta(days=DAYS_BACK)
    
    for keyword in KEYWORDS:
        logger.info(f"\n🔍 Keyword: '{keyword}'")
        stop_keyword = False
        
        for page in range(1, MAX_PAGES + 1):
            if stop_keyword:
                break
            
            url = build_discovery_url(keyword, page)
            
            try:
                response = fetch_with_retry(session, url)
                logger.info(f"   Page {page}/{MAX_PAGES} - Status: {response.status_code}")
                
                if is_cloudflare_blocked(response.text):
                    logger.error(f"   ⚠️  Cloudflare challenge detected")
                    break
                
                data = response.json()
                projects = data.get("projects", [])
                logger.info(f"   Found: {len(projects)} projects")
                
                if not projects:
                    break
                
                for project in projects:
                    project_id = project.get("id")
                    if project_id in seen_ids:
                        continue
                    
                    launched_at = project.get("launched_at")
                    if not launched_at:
                        continue
                    
                    launched_dt = ts_to_datetime(launched_at)
                    
                    if launched_dt < from_date:
                        logger.info(f"   ⏸️  Reached older projects, stopping")
                        stop_keyword = True
                        break
                    
                    item = extract_discovery_project(project)
                    all_projects.append(item)
                    seen_ids.add(project_id)
                    logger.info(f"   ✅ {item['project_name'][:50]}... | {item['backers_count']} backers")
                
                time.sleep(REQUEST_DELAY)
            
            except Exception as e:
                logger.error(f"   ❌ Error: {e}")
                time.sleep(3)
    
    logger.info(f"\n✅ Search complete: {len(all_projects)} unique projects")
    return all_projects


# ==================== PHASE 1B: FETCH GRAPHQL ====================

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


def fetch_graphql_with_retry(slug, max_retries=3, backoff_factor=2):
    """Fetch GraphQL with retry logic"""
    if not KICKSTARTER_CSRF_TOKEN or not KICKSTARTER_COOKIES:
        logger.error("Cannot fetch GraphQL: CSRF_TOKEN and COOKIES must be set in .env")
        return None
    
    headers = {
        "accept": "*/*",
        "accept-language": "en-GB,en-US;q=0.9,en;q=0.8",
        "content-type": "application/json",
        "origin": "https://www.kickstarter.com",
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36",
        "x-csrf-token": KICKSTARTER_CSRF_TOKEN,
        "cookie": KICKSTARTER_COOKIES,
    }
    
    payload = {
        "query": GRAPHQL_QUERY,
        "variables": {"slug": slug}
    }
    
    session = Session(impersonate="chrome", headers=headers, timeout=30)
    
    for attempt in range(max_retries):
        try:
            logger.debug(f"[GRAPHQL] Attempt {attempt + 1}/{max_retries}: {slug}")
            response = session.post(GRAPHQL_URL, json=payload, allow_redirects=True)
            
            if response.status_code == 200:
                data = response.json()
                if "errors" in data:
                    logger.error(f"[GRAPHQL ERROR] {data['errors']}")
                    raise Exception(f"GraphQL error")
                return data
            else:
                if attempt < max_retries - 1:
                    wait_time = (backoff_factor ** attempt)
                    time.sleep(wait_time)
        except Exception as e:
            logger.debug(f"[ERROR] Attempt {attempt + 1}: {e}")
            if attempt < max_retries - 1:
                time.sleep(backoff_factor ** attempt)
    
    return None
