# main.py - Complete Kickstarter Monitor (Phases 1-4)
# Entry point: orchestrates Search → Fetch → Merge → Clean → ClickUp → LLM → Supabase

from curl_cffi.requests import Session
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode
from dotenv import load_dotenv
from html.parser import HTMLParser
import json
import time
import os
import sys
import logging
import re
import requests
import openai
from supabase import create_client, Client

# =========================
# LOAD .env FILE
# =========================
load_dotenv()


# =========================
# LOGGING SETUP
# =========================

def setup_logging(log_level):
    """Configure logging with INFO and DEBUG levels"""
    log_format = "%(asctime)s - [%(levelname)s] - %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"
    
    logging.basicConfig(
        level=getattr(logging, log_level.upper(), logging.INFO),
        format=log_format,
        datefmt=date_format
    )
    return logging.getLogger(__name__)


def get_env(var_name, default=None, required=False):
    """Get environment variable from .env or system env"""
    value = os.getenv(var_name, default)
    
    if required and not value:
        logger.error(f"'{var_name}' is required but not set!")
        logger.error(f"Please add it to your .env file: {var_name}=your_value")
        sys.exit(1)
    
    return value


LOG_LEVEL = get_env("LOG_LEVEL", "INFO")
logger = setup_logging(LOG_LEVEL)

# =========================
# ENVIRONMENT VARIABLES
# =========================

# Kickstarter Discovery
keywords_env = get_env("KICKSTARTER_KEYWORDS", required=True)
KEYWORDS = [k.strip() for k in keywords_env.split("|") if k.strip()]

if not KEYWORDS:
    logger.error("KICKSTARTER_KEYWORDS is set but empty!")
    sys.exit(1)

DAYS_BACK = int(get_env("KICKSTARTER_DAYS_BACK", "14"))
MAX_PAGES = int(get_env("KICKSTARTER_MAX_PAGES", "10"))
REQUEST_DELAY = float(get_env("KICKSTARTER_REQUEST_DELAY", "1"))
KICKSTARTER_CSRF_TOKEN = get_env("KICKSTARTER_CSRF_TOKEN", required=False)
KICKSTARTER_COOKIES = get_env("KICKSTARTER_COOKIE_STRING", required=False)

# ClickUp Voice Guidelines
CLICKUP_WORKSPACE_ID = get_env("CLICKUP_WORKSPACE_ID", required=False)
CLICKUP_DOC_ID = get_env("CLICKUP_DOC_ID", required=False)
CLICKUP_PAGE_ID = get_env("CLICKUP_PAGE_ID", required=False)
CLICKUP_API_KEY = get_env("CLICKUP_API_KEY", required=False)

# OpenAI
OPENAI_API_KEY = get_env("OPENAI_API_KEY", required=False)
if OPENAI_API_KEY:
    openai.api_key = OPENAI_API_KEY

# Supabase
SUPABASE_URL = get_env("SUPABASE_URL", required=False)
SUPABASE_KEY = get_env("SUPABASE_KEY", required=False)

# Initialize Supabase client
supabase_client = None
if SUPABASE_URL and SUPABASE_KEY:
    supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)
    logger.info("✅ Supabase client initialized")

BASE_URL = "https://www.kickstarter.com/discover/advanced"
GRAPHQL_URL = "https://www.kickstarter.com/graph"

logger.info("=" * 80)
logger.info("🎯 KICKSTARTER MONITOR - Complete Pipeline")
logger.info("=" * 80)
logger.info(f"📌 Keywords: {', '.join(KEYWORDS)}")
logger.info(f"📅 Days back: {DAYS_BACK}")
logger.info(f"📊 Log level: {LOG_LEVEL}")
logger.info("=" * 80)


# =========================
# PHASE 1: SEARCH, FETCH, MERGE, CLEAN
# =========================

# ==================== 1A. SEARCH ====================

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


# ==================== 1B. FETCH GRAPHQL ====================

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


# ==================== 1C. MERGE & CLEAN ====================

class HTMLStripper(HTMLParser):
    """Strip HTML tags"""
    def __init__(self):
        super().__init__()
        self.reset()
        self.fed = []

    def handle_data(self, d):
        self.fed.append(d)

    def get_data(self):
        return ''.join(self.fed)


def strip_html_tags(html_text):
    """Remove all HTML tags"""
    if not html_text:
        return ""
    try:
        stripper = HTMLStripper()
        stripper.feed(html_text)
        return stripper.get_data()
    except Exception as e:
        logger.debug(f"[HTML_STRIP] Error: {e}")
        return html_text


def clean_story_field(story_html):
    """Clean story: remove HTML, images, scripts, excessive whitespace"""
    if not story_html:
        return ""
    
    story = re.sub(r'<script[^>]*>.*?</script>', '', story_html, flags=re.DOTALL | re.IGNORECASE)
    story = re.sub(r'<style[^>]*>.*?</style>', '', story, flags=re.DOTALL | re.IGNORECASE)
    story = re.sub(r'<img[^>]*>', '', story, flags=re.IGNORECASE)
    story = re.sub(r'src=["\']([^"\']*)["\']', '', story, flags=re.IGNORECASE)
    story = strip_html_tags(story)
    story = re.sub(r'\s+', ' ', story).strip()
    
    return story


def merge_and_flatten(discovery, graphql_data):
    """Merge discovery + GraphQL, flatten all nested structures"""
    project = graphql_data.get("data", {}).get("project", {})
    
    if not project:
        return None
    
    creator = project.get("creator", {})
    comments = project.get("comments", {})
    env_commitments = project.get("environmentalCommitments", [])
    
    story_raw = project.get("story", "")
    story_clean = clean_story_field(story_raw)
    
    env_commitments_text = " | ".join([
        f"{c.get('commitmentCategory', '')}: {c.get('description', '')}"
        for c in env_commitments if c.get('description')
    ]) if env_commitments else ""
    
    merged = {
        "project_id": discovery.get("project_id"),
        "project_name": discovery.get("project_name"),
        "blurb": discovery.get("blurb"),
        "goal": discovery.get("goal"),
        "pledged": discovery.get("pledged"),
        "usd_pledged": discovery.get("usd_pledged"),
        "backers_count": discovery.get("backers_count"),
        "percent_funded": discovery.get("percent_funded"),
        "state": discovery.get("state"),
        "deadline": discovery.get("deadline"),
        "launched_at": discovery.get("launched_at"),
        "staff_pick": discovery.get("staff_pick"),
        "country": discovery.get("country"),
        "currency": discovery.get("currency"),
        "main_image": discovery.get("main_image"),
        "project_url": discovery.get("project_url"),
        "slug": discovery.get("slug"),
        "creator_name": discovery.get("creator_name"),
        "location": discovery.get("location"),
        
        # GraphQL fields (only missing ones - NO DUPLICATES)
        "creator_id": creator.get("id"),
        "creator_url": creator.get("url", ""),
        "creator_location": creator.get("location", {}).get("displayableName", ""),
        "creator_past_campaigns": creator.get("launchedProjects", {}).get("totalCount", 0),        
        "story_clean": story_clean,
        "risks": project.get("risks", ""),
        "environmental_commitments": env_commitments_text,
        "comments_count": comments.get("totalCount", 0),
    }
    
    return merged


def phase_1_search_fetch_merge_clean(discovered_projects):
    """Phase 1b & 1c: Fetch details and merge for all projects"""
    logger.info("\n📍 PHASE 1b: FETCH GRAPHQL")
    logger.info("-" * 80)
    
    all_merged = []
    failed = []
    
    for idx, project in enumerate(discovered_projects, 1):
        project_id = project.get("project_id")
        slug = project.get("slug")
        
        logger.info(f"[{idx}/{len(discovered_projects)}] {project.get('project_name')[:50]}...")
        
        try:
            graphql_response = fetch_graphql_with_retry(slug)
            
            if graphql_response:
                merged = merge_and_flatten(project, graphql_response)
                if merged:
                    all_merged.append(merged)
                    logger.info(f"    ✅ Merged")
                else:
                    logger.warning(f"    ⚠️  Merge failed")
                    failed.append(project_id)
            else:
                logger.warning(f"    ⚠️  GraphQL fetch failed")
                failed.append(project_id)
        
        except Exception as e:
            logger.error(f"    ❌ Error: {e}")
            failed.append(project_id)
        
        time.sleep(1)
    
    logger.info(f"\n✅ Fetch & Merge complete: {len(all_merged)} projects merged, {len(failed)} failed")
    return all_merged


# =========================
# PHASE 2: FETCH CLICKUP VOICE GUIDELINES
# =========================

def fetch_clickup_guidelines():
    """Phase 2: Fetch ClickUp voice guidelines for LLM"""
    logger.info("\n📍 PHASE 2: FETCH CLICKUP VOICE GUIDELINES")
    logger.info("-" * 80)
    
    if not CLICKUP_API_KEY or not CLICKUP_WORKSPACE_ID or not CLICKUP_DOC_ID:
        logger.warning("⚠️  ClickUp credentials not set in .env, skipping voice guidelines")
        return None
    
    try:
        # Fetch ClickUp document
        url = f"https://api.clickup.com/api/v3/workspaces/{CLICKUP_WORKSPACE_ID}/docs/{CLICKUP_DOC_ID}/pages/{CLICKUP_PAGE_ID}?content_format=text%2Fplain"
        headers = {
            "Authorization": CLICKUP_API_KEY,
            "Content-Type": "application/json"
        }
        
        logger.debug(f"[CLICKUP] Fetching from: {url}")
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            content = data.get("content", "")
            logger.info(f"✅ ClickUp guidelines fetched ({len(content)} chars)")
            return content
        else:
            logger.error(f"❌ ClickUp fetch failed: {response.status_code}")
            return None
    
    except Exception as e:
        logger.error(f"❌ ClickUp error: {e}")
        return None


# =========================
# PHASE 3: LLM SCORING
# =========================

def score_with_openai(project, voice_guidelines):
    """Phase 3: Score a project using OpenAI with ClickUp voice guidelines"""
    
    if not OPENAI_API_KEY:
        logger.warning("⚠️  OpenAI API key not set, skipping LLM scoring")
        return None
    
    try:
        prompt = f"""You are a product expert evaluating Kickstarter projects for a nomadic lifestyle brand.

VOICE & SCORING GUIDELINES:
{voice_guidelines}

PROJECT DATA:
{json.dumps(project, indent=2)}

Based on the guidelines above, evaluate this project. Return a JSON object with:
- score (0-100)
- fit_rating (excellent/good/fair/poor)
- key_strengths (array of strings)
- concerns (array of strings)
- recommendation (string: why nomads would/wouldn't like it)

Return ONLY valid JSON, no markdown, no extra text."""

        logger.debug(f"[LLM] Scoring project {project.get('project_id')}")
        
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a JSON API. Return only valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            timeout=30
        )
        
        result_text = response["choices"][0]["message"]["content"].strip()
        result = json.loads(result_text)
        
        logger.info(f"    ✅ Scored: {result.get('fit_rating', 'N/A')} ({result.get('score', 0)}/100)")
        
        return result
    
    except Exception as e:
        logger.error(f"    ❌ LLM error: {e}")
        return None


def phase_3_llm_scoring(all_projects, voice_guidelines):
    """Phase 3: Score all projects with OpenAI"""
    logger.info("\n📍 PHASE 3: LLM SCORING")
    logger.info("-" * 80)
    
    if not voice_guidelines:
        logger.warning("⚠️  No voice guidelines, skipping LLM scoring")
        return all_projects
    
    for idx, project in enumerate(all_projects, 1):
        logger.info(f"[{idx}/{len(all_projects)}] {project.get('project_name')[:50]}...")
        
        llm_result = score_with_openai(project, voice_guidelines)
        
        if llm_result:
            # Add LLM results to project
            project["llm_score"] = llm_result.get("score")
            project["llm_fit_rating"] = llm_result.get("fit_rating")
            project["llm_strengths"] = llm_result.get("key_strengths", [])
            project["llm_concerns"] = llm_result.get("concerns", [])
            project["llm_recommendation"] = llm_result.get("recommendation")
        
        time.sleep(0.5)  # Be nice to OpenAI
    
    logger.info(f"✅ LLM scoring complete")
    return all_projects


# =========================
# PHASE 4: STORE TO SUPABASE
# =========================

def upsert_to_supabase(projects):
    """Phase 4: Upsert projects to Supabase"""
    logger.info("\n📍 PHASE 4: STORE TO SUPABASE")
    logger.info("-" * 80)
    
    if not supabase_client:
        logger.warning("⚠️  Supabase not configured, skipping database storage")
        return
    
    for idx, project in enumerate(projects, 1):
        try:
            project_id = project.get("project_id")
            logger.info(f"[{idx}/{len(projects)}] Upserting project {project_id}...")
            
            # Upsert with project_id as unique key
            response = supabase_client.table("kickstarter_projects").upsert(
                {
                    **project,
                    "updated_at": datetime.utcnow().isoformat()
                },
                on_conflict="project_id"
            ).execute()
            
            logger.info(f"    ✅ Upserted")
        
        except Exception as e:
            logger.error(f"    ❌ Error: {e}")
    
    logger.info(f"✅ Supabase storage complete")


# =========================
# MAIN ORCHESTRATION
# =========================

def main():
    """Main entry point: orchestrate all 4 phases"""
    try:
        # Phase 1a: Search
        discovered = search_phase()
        
        if not discovered:
            logger.error("❌ No projects discovered, stopping")
            return
        
        # Phase 1b & 1c: Fetch, Merge, Clean
        all_merged = phase_1_search_fetch_merge_clean(discovered)
        
        if not all_merged:
            logger.error("❌ No projects merged, stopping")
            return
        
        # Save debug file
        logger.info("\n📍 PHASE 1d: SAVE DEBUG FILE")
        logger.info("-" * 80)
        with open("debug_merged.json", "w", encoding="utf-8") as f:
            json.dump(all_merged, f, indent=2, ensure_ascii=False)
        logger.info(f"✅ Saved debug_merged.json ({len(all_merged)} projects)")
        
        # Phase 2: Fetch ClickUp guidelines
        voice_guidelines = fetch_clickup_guidelines()
        
        # Phase 3: LLM scoring
        if voice_guidelines:
            all_merged = phase_3_llm_scoring(all_merged, voice_guidelines)
        
        # Phase 4: Store to Supabase
        if supabase_client:
            upsert_to_supabase(all_merged)
        
        # Final summary
        logger.info("\n" + "=" * 80)
        logger.info("✅ KICKSTARTER MONITOR COMPLETE")
        logger.info("=" * 80)
        logger.info(f"📊 Processed: {len(all_merged)} projects")
        logger.info(f"💾 Debug file: debug_merged.json")
        logger.info("=" * 80)
    
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        raise


if __name__ == "__main__":
    main()