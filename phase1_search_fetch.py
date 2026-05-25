# phase1_search_fetch.py - Phase 1a (Search) and 1b (Fetch GraphQL)
# Human-like request pacing with Cloudflare recovery strategy

from curl_cffi.requests import Session
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode
from random import uniform
import time
import json

from config import (
    logger, KEYWORDS, DAYS_BACK, MAX_PAGES, REQUEST_DELAY,
    KICKSTARTER_CSRF_TOKEN, KICKSTARTER_COOKIES,
    BASE_URL, GRAPHQL_URL
)
from alerts import send_cloudflare_alert


# Module-level flag to send only one Cloudflare alert per run
cloudflare_alert_sent = False

# Module-level variable to store warmed Kickstarter session for reuse across phases
_warmed_kickstarter_session = None


# ==================== HELPER FUNCTIONS ====================

def get_randomized_delay(base_delay, max_jitter=4):
    """Generate human-like randomized delay with jitter
    
    Args:
        base_delay: Base delay in seconds
        max_jitter: Max additional random jitter (0 to max_jitter)
    
    Returns:
        float: Total delay time
    """
    return uniform(base_delay, base_delay + max_jitter)


def get_exponential_backoff_with_jitter(retry_attempt):
    """Calculate exponential backoff with randomized jitter for Cloudflare retries
    
    Retry 1: 8-15s (short cooldown)
    Retry 2: 20-40s (larger cooldown)
    Retry 3: 45-90s (aggressive cooldown)
    
    Args:
        retry_attempt: 0-indexed retry attempt (0, 1, 2)
    
    Returns:
        float: Wait time in seconds
    """
    if retry_attempt == 0:
        # Retry 1: 8-15s
        return uniform(8, 15)
    elif retry_attempt == 1:
        # Retry 2: 20-40s
        return uniform(20, 40)
    else:
        # Retry 3: 45-90s
        return uniform(45, 90)


def is_cloudflare_blocked(response_text, status_code):
    """Detect Cloudflare challenge or 403 block
    
    Args:
        response_text: Response HTML/text body
        status_code: HTTP status code
    
    Returns:
        bool: True if Cloudflare block detected
    """
    # Check for 403 Forbidden
    if status_code == 403:
        return True
    
    # Check for Cloudflare challenge markers
    checks = [
        "Just a moment",
        "challenge-platform",
        "cf-browser-verification",
        "/cdn-cgi/challenge-platform",
        "Checking your browser before accessing",
    ]
    
    return any(check in response_text for check in checks)


def fetch_with_network_retry(session, url, headers=None, max_retries=3, backoff_factor=2):
    """Fetch URL with network failure retry logic (separate from Cloudflare)
    
    Args:
        session: curl_cffi Session
        url: URL to fetch
        headers: Optional headers dict to pass with request
        max_retries: Max network retry attempts
        backoff_factor: Exponential backoff multiplier
    
    Returns:
        Response or None
    """
    for attempt in range(max_retries):
        try:
            logger.debug(f"[NETWORK_FETCH] Attempt {attempt + 1}/{max_retries}: {url}")
            response = session.get(url, headers=headers, allow_redirects=True, timeout=30)
            logger.debug(f"[NETWORK_RESPONSE] Status: {response.status_code}")
            return response
        except Exception as e:
            logger.debug(f"[NETWORK_ERROR] Attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                wait_time = backoff_factor ** attempt
                logger.debug(f"[NETWORK_RETRY] Waiting {wait_time}s before retry...")
                time.sleep(wait_time)
            else:
                logger.error(f"[NETWORK_FAILED] All {max_retries} network attempts failed for {url}")
                raise
    
    return None


def warm_up_session(session, document_headers):
    """Warm up session with multi-step browsing before keyword requests
    
    Flow:
    1. Visit homepage (https://www.kickstarter.com/) with document headers
    2. Wait 3-6 seconds (human-like delay)
    3. Visit discovery page (https://www.kickstarter.com/discover/advanced) with document headers
    4. Wait 5-10 seconds (pre-search delay)
    5. Ready for keyword requests (will use API headers)
    
    Purpose:
    - Establish Cloudflare cookies to avoid 403 on first keyword request
    - Simulate realistic human browsing behavior (document requests, not API calls)
    - Build request history in session
    
    Args:
        session: curl_cffi Session
        document_headers: Headers for normal document requests (not API calls)
    """
    logger.info("🔥 Warming up session with multi-step browsing...")
    
    # Step 1: Visit homepage with document headers
    homepage_url = "https://www.kickstarter.com/"
    try:
        logger.debug(f"[WARMUP_STEP1] Visiting: {homepage_url}")
        response = session.get(homepage_url, headers=document_headers, allow_redirects=True, timeout=30)
        logger.debug(f"[WARMUP_STEP1] Status: {response.status_code}")
        if response.status_code == 200:
            logger.info("  ✅ Homepage loaded")
        else:
            logger.warning(f"  ⚠️  Homepage returned status {response.status_code}")
    except Exception as e:
        logger.warning(f"  ⚠️  Homepage failed: {e}")
    
    # Step 2: Wait 3-6 seconds
    delay1 = uniform(3, 6)
    logger.debug(f"[WARMUP_DELAY1] Waiting {delay1:.2f}s before discovery page...")
    time.sleep(delay1)
    
    # Step 3: Visit discovery page with document headers
    discovery_url = "https://www.kickstarter.com/discover/advanced"
    try:
        logger.debug(f"[WARMUP_STEP2] Visiting: {discovery_url}")
        response = session.get(discovery_url, headers=document_headers, allow_redirects=True, timeout=30)
        logger.debug(f"[WARMUP_STEP2] Status: {response.status_code}")
        if response.status_code == 200:
            logger.info("  ✅ Discovery page loaded")
        else:
            logger.warning(f"  ⚠️  Discovery page returned status {response.status_code}")
    except Exception as e:
        logger.warning(f"  ⚠️  Discovery page failed: {e}")
    
    # Step 4: Wait 5-10 seconds before keyword requests
    delay2 = uniform(5, 10)
    logger.debug(f"[WARMUP_DELAY2] Waiting {delay2:.2f}s before keyword search requests...")
    time.sleep(delay2)
    
    logger.info("✅ Session warm-up complete, ready for keyword requests")


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
    """Phase 1a: Search for projects across all keywords with Cloudflare handling"""
    global cloudflare_alert_sent, _warmed_kickstarter_session
    
    logger.info("\n📍 PHASE 1a: SEARCH")
    logger.info("-" * 80)
    
    # Document headers: for normal browser page requests (warmup)
    document_headers = {
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "accept-language": "en-GB,en-US;q=0.9,en;q=0.8",
        "referer": "https://www.kickstarter.com/",
    }
    
    # API/AJAX headers: for keyword discovery search requests
    api_headers = {
        "accept": "application/json, text/javascript, */*; q=0.01",
        "accept-language": "en-GB,en-US;q=0.9,en;q=0.8",
        "x-requested-with": "XMLHttpRequest",
        "referer": "https://www.kickstarter.com/discover/advanced",
    }
    
    # Create session without global headers, let curl_cffi impersonate chrome
    # Headers will be passed per-request for flexibility
    session = Session(impersonate="chrome", timeout=30)
    all_projects = []
    seen_ids = set()
    
    # ==================== WARM UP SESSION ====================
    # Establish Cloudflare cookies before first keyword request
    warm_up_session(session, document_headers)
    logger.info("-" * 80)
    
    # Store warmed session for reuse by GraphQL fetching
    _warmed_kickstarter_session = session
    logger.debug("[SESSION] Warmed session stored for GraphQL reuse")
    
    utc_now = datetime.now(timezone.utc)
    from_date = utc_now - timedelta(days=DAYS_BACK)
    
    for keyword in KEYWORDS:
        logger.info(f"\n🔍 Keyword: '{keyword}'")
        stop_keyword = False
        
        for page in range(1, MAX_PAGES + 1):
            if stop_keyword:
                break
            
            url = build_discovery_url(keyword, page)
            cloudflare_retry_count = 0
            max_cloudflare_retries = 3
            
            # ==================== CLOUDFLARE RETRY LOOP ====================
            while cloudflare_retry_count <= max_cloudflare_retries:
                try:
                    # Fetch with network retry (separate from Cloudflare retry)
                    # Pass API headers for keyword search requests
                    response = fetch_with_network_retry(session, url, headers=api_headers, max_retries=3, backoff_factor=2)
                    
                    logger.info(f"   Page {page}/{MAX_PAGES} - Status: {response.status_code}")
                    
                    # Check for Cloudflare block
                    if is_cloudflare_blocked(response.text, response.status_code):
                        cloudflare_retry_count += 1
                        
                        if cloudflare_retry_count > max_cloudflare_retries:
                            # Max Cloudflare retries exceeded for this keyword
                            logger.error(
                                f"   ❌ Cloudflare block: Max {max_cloudflare_retries} retries exceeded for '{keyword}'"
                            )
                            logger.warning(f"   ⏭️  Skipping keyword: '{keyword}'")
                            
                            # Send ClickUp alert (only once per run)
                            if not cloudflare_alert_sent:
                                send_cloudflare_alert(keyword, page, max_cloudflare_retries)
                                cloudflare_alert_sent = True
                            
                            stop_keyword = True
                            break
                        
                        # Calculate exponential backoff with jitter
                        wait_time = get_exponential_backoff_with_jitter(cloudflare_retry_count - 1)
                        logger.warning(
                            f"   ⚠️  Cloudflare challenge detected (attempt {cloudflare_retry_count}/{max_cloudflare_retries})"
                        )
                        logger.info(f"   💤 Cooling down for {wait_time:.1f}s before retry...")
                        time.sleep(wait_time)
                        
                        # Retry same page
                        continue
                    
                    # Success: Parse JSON
                    try:
                        data = response.json()
                        projects = data.get("projects", [])
                        logger.info(f"   ✅ Success: Found {len(projects)} projects")
                        
                        if not projects:
                            break
                        
                        # Process projects
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
                        
                        # Exit Cloudflare retry loop on success
                        break
                    
                    except json.JSONDecodeError as e:
                        # Could be HTML error page (Cloudflare block before JSON parsing)
                        logger.error(f"   ❌ JSON parse failed: {e}")
                        logger.warning(f"   ⚠️  Possible Cloudflare block (no valid JSON)")
                        
                        cloudflare_retry_count += 1
                        
                        if cloudflare_retry_count > max_cloudflare_retries:
                            logger.error(
                                f"   ❌ Cloudflare block: Max {max_cloudflare_retries} retries exceeded for '{keyword}'"
                            )
                            logger.warning(f"   ⏭️  Skipping keyword: '{keyword}'")
                            
                            # Send ClickUp alert (only once per run)
                            if not cloudflare_alert_sent:
                                send_cloudflare_alert(keyword, page, max_cloudflare_retries)
                                cloudflare_alert_sent = True
                            
                            stop_keyword = True
                            break
                        
                        wait_time = get_exponential_backoff_with_jitter(cloudflare_retry_count - 1)
                        logger.info(f"   💤 Cooling down for {wait_time:.1f}s before retry...")
                        time.sleep(wait_time)
                        continue
                
                except Exception as e:
                    # Network error already retried by fetch_with_network_retry
                    logger.error(f"   ❌ Request failed: {e}")
                    time.sleep(3)
                    break
        
        # Keyword complete: Apply inter-keyword delay before next keyword
        delay = get_randomized_delay(REQUEST_DELAY, max_jitter=6)
        logger.debug(f"[KEYWORD_DELAY] Waiting {delay:.2f}s before next keyword...")
        time.sleep(delay)
    
    logger.info(f"\n✅ Search complete: {len(all_projects)} unique projects discovered")
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


def fetch_graphql_with_retry(slug, session=None, max_retries=3, backoff_factor=2):
    """Fetch GraphQL with retry logic using warmed session + Cloudflare handling
    
    Args:
        slug: Project slug (creator_id/project_slug)
        session: curl_cffi Session (reuses warmed session if provided)
        max_retries: Max Cloudflare retry attempts
        backoff_factor: Exponential backoff multiplier
    
    Returns:
        dict: GraphQL response data or None if failed
    """
    global _warmed_kickstarter_session
    
    # Always create a FRESH session for GraphQL (not reusing warmed session)
    # This prevents old cookies from search phase interfering
    # Fresh CSRF + cookies will be passed as headers from .env
    logger.debug(f"[GRAPHQL] Creating fresh session for {slug} (headers will use .env credentials)")
    session = Session(impersonate="chrome", timeout=30)
    
    # GraphQL request headers (no User-Agent, let curl_cffi handle it)
    graphql_headers = {
        "accept": "*/*",
        "accept-language": "en-GB,en-US;q=0.9,en;q=0.8",
        "content-type": "application/json",
        "origin": "https://www.kickstarter.com",
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
    }
    
    # Add CSRF token if available from .env (fallback)
    if KICKSTARTER_CSRF_TOKEN:
        graphql_headers["x-csrf-token"] = KICKSTARTER_CSRF_TOKEN
    
    # Add cookies if available from .env (fallback)
    if KICKSTARTER_COOKIES:
        graphql_headers["cookie"] = KICKSTARTER_COOKIES
    
    # Debug: Log what credentials are being used
    csrf_preview = KICKSTARTER_CSRF_TOKEN[:20] if KICKSTARTER_CSRF_TOKEN else "NONE"
    cookies_preview = KICKSTARTER_COOKIES[:50] if KICKSTARTER_COOKIES else "NONE"
    logger.debug(f"[GRAPHQL_HEADERS] CSRF: {csrf_preview}... | Cookies: {cookies_preview}...")
    
    payload = {
        "query": GRAPHQL_QUERY,
        "variables": {"slug": slug}
    }
    
    cloudflare_retry_count = 0
    max_cloudflare_retries = 3
    
    # ==================== CLOUDFLARE RETRY LOOP ====================
    while cloudflare_retry_count <= max_cloudflare_retries:
        try:
            # Step 1: For fresh sessions, skip project page pre-visit
            # Just go directly to GraphQL with fresh CSRF+cookies headers
            # (The test file that works doesn't visit project page first)
            
            # Step 2: Fetch GraphQL
            logger.debug(f"[GRAPHQL] Attempt {cloudflare_retry_count + 1}/{max_cloudflare_retries + 1}: {slug}")
            response = session.post(GRAPHQL_URL, json=payload, headers=graphql_headers, allow_redirects=True, timeout=30)
            
            logger.debug(f"[GRAPHQL_RESPONSE] Status: {response.status_code}, Body (first 200 chars): {response.text[:200]}")
            
            # Check for Cloudflare block (403 or specific markers)
            if is_cloudflare_blocked(response.text, response.status_code):
                cloudflare_retry_count += 1
                
                if cloudflare_retry_count > max_cloudflare_retries:
                    # Max retries exceeded
                    logger.error(f"[GRAPHQL_BLOCKED] Max {max_cloudflare_retries} retries exceeded for {slug}")
                    return None
                
                # Calculate exponential backoff with jitter
                wait_time = get_exponential_backoff_with_jitter(cloudflare_retry_count - 1)
                logger.warning(f"[GRAPHQL_BLOCKED] Cloudflare block detected (attempt {cloudflare_retry_count}/{max_cloudflare_retries})")
                logger.info(f"[GRAPHQL_RETRY] Cooling down for {wait_time:.1f}s before retry...")
                time.sleep(wait_time)
                continue
            
            # Success: Parse response
            if response.status_code == 200:
                data = response.json()
                if "errors" in data:
                    logger.error(f"[GRAPHQL_ERROR] GraphQL errors in response: {data['errors']}")
                    return None
                logger.debug(f"[GRAPHQL_SUCCESS] Fetched data for {slug}")
                return data
            else:
                logger.warning(f"[GRAPHQL_FAILED] Status={response.status_code}, Body={response.text[:200]}")
                return None
        
        except Exception as e:
            logger.error(f"[GRAPHQL_ERROR] Attempt {cloudflare_retry_count + 1}: {e}")
            return None
    
    logger.error(f"[GRAPHQL_FAILED] All attempts exhausted for {slug}")
    return None
