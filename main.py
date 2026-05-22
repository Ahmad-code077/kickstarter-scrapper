# test_discovery.py

from curl_cffi.requests import Session
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode
from dotenv import load_dotenv
import json
import time
import os
import sys

# =========================
# LOAD .env FILE
# =========================
load_dotenv()


# =========================
# CONFIG - FROM .env OR ENVIRONMENT
# =========================

def get_env(var_name, default=None, required=False):
    """Get environment variable from .env or system env"""
    value = os.getenv(var_name, default)
    
    if required and not value:
        print(f"\n❌ ERROR: '{var_name}' is required but not set!")
        print(f"\n   Please add it to your .env file:")
        print(f"   {var_name}=your_value")
        print(f"\n   Or create .env file with:")
        print(f"   KICKSTARTER_KEYWORDS=travel bag,backpack,sling bag")
        sys.exit(1)
    
    return value


# Required: Keywords (will exit if not present)
keywords_env = get_env("KICKSTARTER_KEYWORDS", required=True)
KEYWORDS = [k.strip() for k in keywords_env.split(",") if k.strip()]

if not KEYWORDS:
    print(f"\n❌ ERROR: KICKSTARTER_KEYWORDS is set but empty!")
    print(f"   Please provide at least one keyword in .env file.")
    print(f"\n   Example .env file:")
    print(f"   KICKSTARTER_KEYWORDS=travel bag,backpack,sling bag")
    sys.exit(1)

# Optional with defaults from .env or environment
DAYS_BACK = int(get_env("KICKSTARTER_DAYS_BACK", "14"))
MAX_PAGES = int(get_env("KICKSTARTER_MAX_PAGES", "10"))
REQUEST_DELAY = float(get_env("KICKSTARTER_REQUEST_DELAY", "1"))
OUTPUT_FILE = get_env("KICKSTARTER_OUTPUT_FILE", "kickstarter_discovery.json")

BASE_URL = "https://www.kickstarter.com/discover/advanced"


# =========================
# PRINT CONFIGURATION
# =========================

print(f"\n{'=' * 80}")
print(f"🔧 KICKSTARTER DISCOVERY CONFIGURATION")
print(f"{'=' * 80}")
print(f"📌 Keywords: {', '.join(KEYWORDS)}")
print(f"📅 Days back: {DAYS_BACK}")
print(f"📄 Max pages per keyword: {MAX_PAGES}")
print(f"⏱️  Request delay: {REQUEST_DELAY}s")
print(f"📁 Output file: {OUTPUT_FILE}")
print(f"{'=' * 80}")


# =========================
# DATE WINDOW
# =========================

utc_now = datetime.now(timezone.utc)
from_date = utc_now - timedelta(days=DAYS_BACK)

print(f"\n📅 Searching projects launched between:")
print(f"   From: {from_date.strftime('%Y-%m-%d')}")
print(f"   To:   {utc_now.strftime('%Y-%m-%d')}")
print(f"   (Last {DAYS_BACK} days)")


# =========================
# CURL_CFFI SESSION
# =========================

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

session = Session(
    impersonate="chrome136",
    headers=headers,
    timeout=30,
)


# =========================
# HELPERS
# =========================

def build_url(keyword, page=1):
    params = {
        "google_chrome_workaround": "",
        "term": keyword,
        "sort": "newest",
        "page": page,
    }
    return f"{BASE_URL}?{urlencode(params)}"


def is_cloudflare_blocked(text):
    checks = [
        "Just a moment",
        "challenge-platform",
        "cf-browser-verification",
        "/cdn-cgi/challenge-platform",
    ]
    return any(c in text for c in checks)


def ts_to_datetime(ts):
    return datetime.fromtimestamp(ts, tz=timezone.utc)


def extract_project_data(project, keyword):
    """Extract only the fields we need for the newsletter"""
    
    # Get creator info
    creator = project.get("creator") or {}
    creator_id = creator.get("id")
    creator_name = creator.get("name")
    
    # Get project slug (without creator ID)
    project_slug = project.get("slug", "")
    
    # Build FULL slug with creator ID for GraphQL queries
    full_slug = f"{creator_id}/{project_slug}" if creator_id else project_slug
    
    # Get main image (only the 'full' size)
    photo = project.get("photo") or {}
    main_image = photo.get("full")
    
    # Get project URL
    urls = project.get("urls") or {}
    web = urls.get("web") or {}
    project_url = web.get("project")
    
    # Get location
    location = project.get("location") or {}
    location_name = location.get("displayable_name") or location.get("name")
    
    # Get category
    category = project.get("category") or {}
    
    # Extract USD pledged amount
    usd_pledged = project.get("usd_pledged")
    if usd_pledged:
        usd_pledged = str(round(float(usd_pledged), 2))
    
    # Build the clean output object
    return {
        "project_id": project.get("id"),
        "project_name": project.get("name"),
        "blurb": project.get("blurb"),
        "goal": project.get("goal"),
        "goal_currency": project.get("currency", "USD"),
        "pledged": project.get("pledged"),
        "pledged_currency": project.get("currency", "USD"),
        "usd_pledged": usd_pledged,
        "backers_count": project.get("backers_count"),
        "percent_funded": project.get("percent_funded"),
        "state": project.get("state"),
        "deadline": project.get("deadline"),
        "launched_at": project.get("launched_at"),
        "created_at": project.get("created_at"),
        "staff_pick": project.get("staff_pick", False),
        "country": project.get("country"),
        "currency_symbol": project.get("currency_symbol", "$"),
        "main_image": main_image,
        "project_url": project_url,
        "slug": full_slug,
        "creator_name": creator_name,
        "location": location_name,
    }


# =========================
# MAIN
# =========================

all_projects = []
seen_ids = set()

for keyword in KEYWORDS:
    print(f"\n{'=' * 80}")
    print(f"🔍 SEARCHING KEYWORD: '{keyword}'")
    print(f"{'=' * 80}")

    stop_keyword = False

    for page in range(1, MAX_PAGES + 1):
        if stop_keyword:
            break

        url = build_url(keyword, page)
        print(f"\n📄 Page {page}/{MAX_PAGES}")

        try:
            response = session.get(url, allow_redirects=True)
            print(f"   Status: {response.status_code}")

            text = response.text

            # =========================
            # CLOUDFLARE DETECTION
            # =========================
            if is_cloudflare_blocked(text):
                print(f"\n⚠️  Cloudflare challenge detected for keyword '{keyword}'!")
                with open(f"cloudflare_block_{keyword}.html", "w", encoding="utf-8") as f:
                    f.write(text)
                print(f"💾 Saved cloudflare_block_{keyword}.html")
                break

            # =========================
            # JSON PARSING
            # =========================
            try:
                data = response.json()
            except Exception:
                print(f"❌ Failed to parse JSON for keyword '{keyword}'")
                with open(f"response_{keyword}.html", "w", encoding="utf-8") as f:
                    f.write(text)
                print(f"💾 Saved response_{keyword}.html")
                break

            projects = data.get("projects", [])
            print(f"   Projects found: {len(projects)}")

            if not projects:
                print(f"   No more projects for keyword '{keyword}'")
                break

            # =========================
            # PROJECT LOOP
            # =========================
            for project in projects:
                project_id = project.get("id")
                if project_id in seen_ids:
                    continue

                launched_at = project.get("launched_at")
                if not launched_at:
                    continue

                launched_dt = ts_to_datetime(launched_at)

                # STOP PAGINATION (newest → oldest)
                if launched_dt < from_date:
                    print(f"\n   ⏸️  Reached projects older than {from_date.strftime('%Y-%m-%d')}")
                    print(f"      Last project date: {launched_dt.strftime('%Y-%m-%d')}")
                    print(f"      Stopping keyword '{keyword}'")
                    stop_keyword = True
                    break

                # Extract clean project data
                item = extract_project_data(project, keyword)

                all_projects.append(item)
                seen_ids.add(project_id)

                # Print summary
                print(f"   ✅ {item['project_name'][:50]}... | {launched_dt.strftime('%Y-%m-%d')} | {item['backers_count']} backers | {item['percent_funded']:.1f}%")

            # Polite delay
            time.sleep(REQUEST_DELAY)

        except Exception as e:
            print(f"❌ ERROR for keyword '{keyword}': {e}")
            time.sleep(3)
            continue


# =========================
# SAVE RESULTS
# =========================

with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(all_projects, f, indent=2, ensure_ascii=False)

print(f"\n{'=' * 80}")
print(f"✅ DISCOVERY COMPLETE!")
print(f"{'=' * 80}")
print(f"📊 Total unique projects found: {len(all_projects)}")
print(f"📁 Output file: {OUTPUT_FILE}")
print(f"{'=' * 80}")

# Summary by keyword
if all_projects:
    print(f"\n📊 Summary by keyword:")
    keyword_counts = {}
    for p in all_projects:
        # Keyword is not stored in the clean output, so we need to track separately
        pass
    
    print(f"\n💡 Next steps:")
    print(f"   1. Review projects in {OUTPUT_FILE}")
    print(f"   2. For high-score candidates, fetch full details using the 'slug' field")
    print(f"   3. Example GraphQL query:")
    print(f"      project(slug: \"{all_projects[0]['slug']}\") {{ ... }}")