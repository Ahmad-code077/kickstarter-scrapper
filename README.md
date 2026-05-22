# 🎯 Kickstarter Monitor - Complete Pipeline

**ONE entry point. FOUR phases. Simple. No over-engineering.**

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                      main.py (Single File)                  │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Phase 1: Search, Fetch, Merge, Clean                       │
│  ├─ search_phase() → Discover projects (REST API)          │
│  ├─ phase_1_search_fetch_merge_clean() → Fetch (GraphQL)   │
│  ├─ merge_and_flatten() → Combine & flatten                │
│  ├─ clean_story_field() → Strip HTML → plain text          │
│  └─ Save debug_merged.json                                 │
│                                                              │
│  Phase 2: Fetch ClickUp Voice Guidelines                   │
│  └─ fetch_clickup_guidelines() → Get scoring rules         │
│                                                              │
│  Phase 3: LLM Scoring with OpenAI                          │
│  └─ score_with_openai() → GPT-4 + guidelines → JSON        │
│                                                              │
│  Phase 4: Store to Supabase                                │
│  └─ upsert_to_supabase() → Save to DB                      │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## 📋 Workflow

### Phase 1: Search & Clean (Local Processing)

```
Keywords (pipe-separated)
    ↓
Kickstarter Discovery API (REST)
    ├─ Keyword 1 → Projects A, B, C...
    ├─ Keyword 2 → Projects D, E, F...
    └─ Filter by DAYS_BACK
    ↓
For Each Project:
    ├─ Fetch full details (GraphQL API)
    ├─ Merge discovery data + GraphQL data
    └─ Clean story HTML → plain text
    ↓
Flattened JSON (no nested objects)
    ├─ pledged_amount, pledged_currency (instead of nested pledged.amount)
    ├─ goal_amount, goal_currency
    ├─ creator_name, creator_id, creator_past_campaigns, creator_biography, etc.
    ├─ story_clean (plain text)
    └─ comments_count
    ↓
💾 Save debug_merged.json (for inspection)
```

### Phase 2: Fetch Voice Guidelines

```
ClickUp API (with API key)
    ↓
Retrieve document content
    ↓
→ Text string (voice guidelines for LLM)
```

### Phase 3: AI Scoring

```
For Each Project:
    ├─ Project data (JSON)
    ├─ Voice guidelines (text)
    ├─ System prompt ("You are a product expert")
    └─ Send to OpenAI GPT-4
        ↓
        Response (JSON):
        {
          "score": 85,
          "fit_rating": "excellent",
          "key_strengths": ["lightweight", "durable"],
          "concerns": ["price", "shipping"],
          "recommendation": "Perfect for nomads..."
        }
        ↓
        Merge into project data
```

### Phase 4: Store to Database

```
For Each Project (with LLM results):
    ├─ Upsert to Supabase
    ├─ Table: kickstarter_projects
    ├─ Key: project_id (unique)
    └─ Fields: all merged + LLM data
```

## 🔧 Configuration

### Required (Phase 1 works without anything else)

```env
KICKSTARTER_KEYWORDS=travel bag|backpack|sling bag
KICKSTARTER_DAYS_BACK=14
KICKSTARTER_MAX_PAGES=10
KICKSTARTER_REQUEST_DELAY=1
KICKSTARTER_CSRF_TOKEN=<from browser>
KICKSTARTER_COOKIE_STRING=<from browser>
```

### Optional (Add as needed)

```env
# ClickUp (for voice guidelines)
CLICKUP_WORKSPACE_ID=3666576
CLICKUP_DOC_ID=3fwmg-16918
CLICKUP_PAGE_ID=3fwmg-2598
CLICKUP_API_KEY=pk_...

# OpenAI (for LLM scoring)
OPENAI_API_KEY=sk_...

# Supabase (for database)
SUPABASE_URL=https://...
SUPABASE_KEY=eyJhbGc...
```

## 📊 Data Example

### Input: Discovered Project (from REST API)

```json
{
  "project_id": 1207952088,
  "project_name": "Reusable Grocery Bag",
  "blurb": "A sustainable...",
  "goal": 5000,
  "pledged": 150000,
  "backers_count": 3500,
  "percent_funded": 3000,
  "slug": "123456/reusable-grocery-bag"
}
```

### Merged & Cleaned (Phase 1 output)

```json
{
  "project_id": 1207952088,
  "project_name": "Reusable Grocery Bag",
  "blurb": "A sustainable...",

  "goal_amount": 5000,
  "goal_currency": "USD",
  "pledged_amount": 150000,
  "pledged_currency": "USD",
  "percent_funded": 3000,

  "backers_count": 3500,
  "comments_count": 1240,

  "creator_name": "Eco Brands Inc",
  "creator_id": 123456,
  "creator_past_campaigns": 5,
  "creator_biography": "We make...",
  "creator_url": "https://...",

  "story_clean": "Plain text version of the story with no HTML tags or images",
  "risks": "Manufacturing delays possible due to...",

  "staff_pick": true,
  "state": "live",
  "country": "US"
}
```

### LLM Scored (Phase 3 output)

```json
{
  "...all above fields...",

  "llm_score": 87,
  "llm_fit_rating": "excellent",
  "llm_strengths": [
    "High funding indicates product market fit",
    "Eco-friendly aligns with nomad values",
    "Strong backer engagement"
  ],
  "llm_concerns": [
    "Heavy for backpacking trips",
    "Delivery to international addresses unclear"
  ],
  "llm_recommendation": "Excellent choice for sustainable nomads focused on eco-friendly gear..."
}
```

## 🚀 Running the Monitor

```bash
# 1. Activate venv
./venv/Scripts/activate  # Windows

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure .env file
# (Edit .env with your credentials)

# 4. Run
python main.py
```

## 📁 Output

- **debug_merged.json** - Flattened, cleaned projects (Phase 1 output for inspection)
- **Supabase table** - Complete projects with LLM scores (if configured)

## ✨ Key Features

✅ **Single Entry Point** - Just `python main.py`
✅ **Modular Phases** - Each phase optional (run as far as credentials allow)
✅ **Data Flattening** - No nested objects, ready for DB storage
✅ **HTML Cleaning** - Regex-based tag removal, keeps plain text
✅ **Retry Logic** - 3 attempts with exponential backoff
✅ **Logging** - INFO and DEBUG levels
✅ **Debug Output** - `debug_merged.json` saved before LLM calls
✅ **Simple** - ~600 lines, no over-engineering

## 🔐 Credentials

### Kickstarter (CSRF Token & Cookies)

- Visit any Kickstarter project page
- DevTools → Network tab → Copy from any request
- Valid for ~24 hours

### OpenAI API Key

- Get from https://platform.openai.com/api-keys
- ~$0.01-0.05 per project scored

### ClickUp API Key

- Get from https://app.clickup.com/settings/integrations
- Document IDs from URL

### Supabase

- Get from https://supabase.com/dashboard
- Create table `kickstarter_projects` with project_id as primary key

## 📚 Next Steps

1. Fill in `.env` with at least Kickstarter credentials
2. Run `python main.py` to test Phase 1
3. Add OpenAI API key to enable LLM scoring
4. Add Supabase credentials to enable database storage
5. Schedule as cron job for daily runs
