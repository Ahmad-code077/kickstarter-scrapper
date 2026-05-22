# Kickstarter Monitor - Setup & Run Instructions

## 🚀 Quick Start

### 1. Activate Virtual Environment

```bash
# Windows
./venv/Scripts/activate

# Mac/Linux
source venv/bin/activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure .env File

Copy and fill in these values:

```
# Kickstarter (required)
KICKSTARTER_KEYWORDS=travel bag|backpack|sling bag
KICKSTARTER_DAYS_BACK=14
KICKSTARTER_MAX_PAGES=10
KICKSTARTER_REQUEST_DELAY=1
KICKSTARTER_CSRF_TOKEN=<from browser DevTools>
KICKSTARTER_COOKIE_STRING=<from browser DevTools>

# ClickUp (optional - for voice guidelines)
CLICKUP_WORKSPACE_ID=3666576
CLICKUP_DOC_ID=3fwmg-16918
CLICKUP_PAGE_ID=3fwmg-2598
CLICKUP_API_KEY=<get from ClickUp>

# OpenAI (optional - for LLM scoring)
OPENAI_API_KEY=<get from OpenAI dashboard>

# Supabase (optional - for database storage)
SUPABASE_URL=<get from Supabase project settings>
SUPABASE_KEY=<get from Supabase project settings>

# Logging
LOG_LEVEL=INFO
```

### 4. Run the Monitor

```bash
python main.py
```

## 📊 What It Does (Phases 1-4)

### Phase 1: Search, Fetch, Merge, Clean

- Searches each keyword on Kickstarter (REST API)
- Fetches full project details via GraphQL
- Merges discovery data + GraphQL data
- Cleans HTML from story field → plain text
- Saves debug output to `debug_merged.json`

### Phase 2: Fetch ClickUp Voice Guidelines

- Gets scoring guidelines from ClickUp document
- (Skipped if credentials not set)

### Phase 3: LLM Scoring

- Sends each project + voice guidelines to OpenAI
- Gets structured JSON with:
  - score (0-100)
  - fit_rating (excellent/good/fair/poor)
  - key_strengths
  - concerns
  - recommendation
- (Skipped if OpenAI API key not set)

### Phase 4: Store to Supabase

- Upserts all projects to database
- Includes merged + LLM data
- Uses project_id as unique key
- (Skipped if Supabase not configured)

## 📁 Output Files

- **debug_merged.json** - Flattened, cleaned projects before LLM (always created)
- **All data stored in memory** - No intermediate files

## 🔧 Getting Browser Credentials (for KICKSTARTER_CSRF_TOKEN & KICKSTARTER_COOKIE_STRING)

1. Open Kickstarter in browser
2. Visit any project page (e.g., a travel bag project)
3. Open DevTools (F12)
4. Go to Network tab
5. Look for any POST/GET request to kickstarter.com
6. Copy the `x-csrf-token` header → KICKSTARTER_CSRF_TOKEN
7. Copy the `cookie` header → KICKSTARTER_COOKIE_STRING

## 📝 Logging Levels

- `LOG_LEVEL=INFO` - Normal progress (recommended)
- `LOG_LEVEL=DEBUG` - Detailed debugging (verbose)

## ⚠️ Notes

- Credentials expire periodically - refresh if API calls fail
- LLM scoring costs money (OpenAI API charges)
- Be respectful to Kickstarter API (1 second delay between requests)
- ClickUp & Supabase are optional - monitor works without them
