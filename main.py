# test_discovery.py

from curl_cffi.requests import Session
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode
import json
import time


# =========================
# CONFIG
# =========================

KEYWORDS = [
    "travel bag",
    "backpack",
    "sling bag",
    "duffel bag",
    "carry on bag",
]

DAYS_BACK = 14
MAX_PAGES = 10

BASE_URL = "https://www.kickstarter.com/discover/advanced"


# =========================
# DATE WINDOW
# =========================

utc_now = datetime.now(timezone.utc)
from_date = utc_now - timedelta(days=DAYS_BACK)

print(f"\nSearching projects from last {DAYS_BACK} days")
print("From:", from_date.isoformat())
print("To:", utc_now.isoformat())


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


# =========================
# MAIN
# =========================

all_projects = []
seen_ids = set()

for keyword in KEYWORDS:

    print(f"\n{'=' * 80}")
    print("KEYWORD:", keyword)
    print(f"{'=' * 80}")

    stop_keyword = False

    for page in range(1, MAX_PAGES + 1):

        if stop_keyword:
            break

        url = build_url(keyword, page)

        print(f"\nFetching page {page}")
        print(url)

        try:
            response = session.get(
                url,
                allow_redirects=True,
            )

            print("Status:", response.status_code)

            text = response.text

            # =========================
            # CLOUDFLARE DETECTION
            # =========================

            if is_cloudflare_blocked(text):

                print("\nCloudflare challenge detected")

                with open("cloudflare_block.html", "w", encoding="utf-8") as f:
                    f.write(text)

                print("Saved cloudflare_block.html")
                break

            # =========================
            # JSON
            # =========================

            try:
                data = response.json()

            except Exception:

                print("Failed to parse JSON")

                with open("response.html", "w", encoding="utf-8") as f:
                    f.write(text)

                print("Saved response.html")
                break

            projects = data.get("projects", [])

            print("Projects:", len(projects))

            if not projects:
                print("No more projects")
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

                # STOP PAGINATION
                # because newest -> oldest

                if launched_dt < from_date:
                    print(
                        f"Reached older projects "
                        f"({launched_dt.date()}) -> stopping keyword"
                    )
                    stop_keyword = True
                    break

                category = project.get("category") or {}

                urls = project.get("urls") or {}
                web = urls.get("web") or {}

                item = {
                    "keyword": keyword,
                    "project_id": project_id,
                    "project_name": project.get("name"),
                    "project_url": web.get("project"),
                    "creator": (project.get("creator") or {}).get("name"),
                    "category_name": category.get("name"),
                    "category_id": category.get("id"),
                    "launched_at": launched_dt.isoformat(),
                    "deadline": project.get("deadline"),
                    "state": project.get("state"),
                    "backers_count": project.get("backers_count"),
                    "pledged": project.get("pledged"),
                    "percent_funded": project.get("percent_funded"),
                    "blurb": project.get("blurb"),
                    "photo": (project.get("photo") or {}).get("full"),
                }

                all_projects.append(item)
                seen_ids.add(project_id)

                print(
                    f"Saved: {project.get('name')} "
                    f"({launched_dt.date()})"
                )

            # polite delay
            time.sleep(1)

        except Exception as e:
            print("ERROR:", e)

            time.sleep(3)

            continue


# =========================
# SAVE RESULTS
# =========================

with open(
    "kickstarter_discovery.json",
    "w",
    encoding="utf-8"
) as f:
    json.dump(all_projects, f, indent=2, ensure_ascii=False)

print(f"\nSaved {len(all_projects)} projects")
print("Output: kickstarter_discovery.json")