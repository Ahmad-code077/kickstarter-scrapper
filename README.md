# 🎯 Kickstarter Monitor - Complete Pipeline

**Production-ready Python pipeline for discovering and scoring Kickstarter projects with AI.**

One entry point (`main.py`), four independent phases, fully modular architecture.

## 🏗️ Architecture

```
main.py (Single Orchestrator)
├─ Phase 1: Search, Fetch & Clean (Kickstarter API)
│  ├─ config.py (Centralized config & logging)
│  ├─ phase1_search_fetch.py (REST API search + GraphQL fetch)
│  └─ phase1_merge_clean.py (Merge data + clean HTML)
│
├─ Phase 2: Fetch ClickUp Documents
│  └─ phase2_clickup.py (Brand Voice + Extraction SOP)
│
├─ Phase 3: LLM Scoring with OpenAI
│  └─ phase3_llm.py (GPT-4 scoring using ClickUp instructions)
│
└─ Phase 4: Persist to Supabase
   └─ phase4_supabase.py (Batch upsert to PostgreSQL)
```

## 📊 Data Flow

### Phase 1: Discovery & Cleaning

```
Keywords (pipe-separated)
    ↓
Kickstarter REST API
    ├─ Search across all keywords
    ├─ Filter by DAYS_BACK
    └─ Paginate up to MAX_PAGES
    ↓
For Each Project:
    ├─ Fetch full details (GraphQL)
    ├─ Merge discovery + GraphQL data
    ├─ Flatten nested structures
    ├─ Clean HTML story → plain text
    └─ Deduplicate
    ↓
💾 debug_merged.json (inspection point)
```

### Phase 2: Voice Guidelines

```
ClickUp API
    ├─ Fetch Brand Voice document
    └─ Fetch Extraction SOP document
    ↓
Text content (used by LLM in Phase 3)
```

### Phase 3: AI Scoring

```
For Each Project:
    ├─ Select 8 key fields
    ├─ Send to GPT-4 with:
    │  ├─ Brand Voice guidelines
    │  ├─ Extraction SOP instructions
    │  └─ Project data
    ├─ Parse JSON response (format from SOP)
    └─ Merge with original metadata
```

### Phase 4: Persistence

```
For Each Project:
    └─ Upsert to Supabase
       ├─ Table: kickstarter_projects
       ├─ Key: project_id (unique)
       └─ Merge: New scores + existing metadata
```

## 🔧 Setup

See **[SETUP.md](SETUP.md)** for complete setup and deployment instructions.

### Quick Start

```bash
# 1. Clone
git clone <repo-url> && cd kickstarter-monitor

# 2. Create environment
python -m venv venv && source venv/bin/activate  # Linux/Mac
# OR on Windows: .\venv\Scripts\activate

# 3. Install
pip install -r requirements.txt

# 4. Configure
cp .env.example .env
# Edit .env with your Kickstarter cookies & API keys

# 5. Run
python main.py
```

## 📋 Configuration

### Required (Phase 1 only)

```env
KICKSTARTER_KEYWORDS=travel bag|backpack|sling bag
KICKSTARTER_DAYS_BACK=14
KICKSTARTER_MAX_PAGES=10
KICKSTARTER_REQUEST_DELAY=1
KICKSTARTER_CSRF_TOKEN=<from browser DevTools>
KICKSTARTER_COOKIE_STRING=<from browser DevTools>
```

### Optional (Phases 2-4)

```env
# Phase 2: ClickUp voice guidelines
CLICKUP_WORKSPACE_ID=...
CLICKUP_VOICE_DOC_ID=...
CLICKUP_VOICE_PAGE_ID=...
CLICKUP_SOP_EXTRACTION_DOC_ID=...
CLICKUP_SOP_EXTRACTION_PAGE_ID=...
CLICKUP_API_KEY=...

# Phase 3: OpenAI LLM
OPENAI_API_KEY=...

# Phase 4: Supabase
SUPABASE_URL=...
SUPABASE_KEY=...

# Logging
LOG_LEVEL=INFO
```

## 📦 Project Structure

```
kickstarter-monitor/
├── main.py                    # Orchestrator (entry point)
├── config.py                  # Environment & logging setup
├── phase1_search_fetch.py     # Search REST API + GraphQL fetch
├── phase1_merge_clean.py      # Merge data + clean HTML
├── phase2_clickup.py          # Fetch ClickUp documents
├── phase3_llm.py              # OpenAI GPT-4 scoring
├── phase4_supabase.py         # Supabase persistence
├── requirements.txt           # Dependencies (6 core packages)
├── .env.example              # Template (commit to repo)
├── .gitignore                # Excludes .env, venv, __pycache__, etc
├── README.md                 # This file
└── SETUP.md                  # Setup & deployment guide
```

## 🚀 Features

✅ **Modular Design** - Each phase in separate file  
✅ **No Hardcoded Prompts** - LLM instructions from ClickUp documents  
✅ **Flexible Outputs** - Use Phase 1 alone or enable phases 2-4  
✅ **Clean Logging** - DEBUG/INFO levels, real-time progress  
✅ **Retry Logic** - Exponential backoff for API failures  
✅ **HTML Cleaning** - Regex + HTMLParser for story field  
✅ **Flat JSON** - No nested structures in output  
✅ **Database Upsert** - Smart updates to Supabase

## 📊 Sample Output

### Phase 1: Merged & Cleaned Project

```json
{
  "project_id": 1207952088,
  "project_name": "Reusable Grocery Bag",
  "blurb": "Sustainable bag for nomads...",

  "goal": 5000,
  "pledged": 150000,
  "usd_pledged": "150000.00",
  "percent_funded": 3000,
  "backers_count": 3500,
  "comments_count": 1240,

  "creator_name": "Eco Brands Inc",
  "creator_id": 123456,
  "creator_past_campaigns": 5,
  "creator_url": "https://...",

  "story_clean": "Plain text with no HTML tags or images",
  "risks": "Possible manufacturing delays...",

  "staff_pick": true,
  "state": "live",
  "country": "US",
  "currency": "USD"
}
```

### Phase 3: LLM Scored (ClickUp SOP format)

```json
{
  "...all Phase 1 fields...",

  "llm_score": 87,
  "llm_fit_rating": "excellent",
  "llm_strengths": [
    "Strong funding indicates product-market fit",
    "Eco-friendly aligns with nomad values",
    "High backer engagement"
  ],
  "llm_concerns": [
    "Weight may limit portability",
    "International shipping unclear"
  ],
  "llm_recommendation": "Excellent choice for sustainability-focused nomads..."
}
```

## 🔑 Core Modules

### `main.py` - Orchestrator

Chains all 4 phases:

```python
1. discovered = search_phase()
2. merged = phase_1_search_fetch_merge_clean(discovered)
3. voice, sop = fetch_brand_voice(), fetch_extraction_sop()
4. scored = phase_3_llm_scoring(merged, voice, sop)
5. upsert_to_supabase(scored)
```

### `config.py` - Centralized Setup

- Loads `.env` variables
- Configures logger (INFO/DEBUG)
- Initializes Supabase client
- Validates required credentials

### `phase1_search_fetch.py` - Discovery

- `search_phase()` - Discover via REST API
- `fetch_graphql_with_retry()` - Fetch details (3 retries, backoff)
- Deduplication & date filtering

### `phase1_merge_clean.py` - Cleaning

- `merge_and_flatten()` - Combine + flatten
- `clean_story_field()` - Strip HTML/scripts/images
- `HTMLStripper` - Custom HTML parser

### `phase2_clickup.py` - Documents

- `fetch_brand_voice()` - Brand guidelines
- `fetch_extraction_sop()` - Scoring instructions

### `phase3_llm.py` - Scoring

- `score_with_openai()` - Single project scoring
- `phase_3_llm_scoring()` - Batch scoring
- No hardcoded prompts (uses ClickUp docs)

### `phase4_supabase.py` - Persistence

- `upsert_to_supabase()` - Batch upsert
- Conflict handling via `on_conflict="project_id"`

## 🔗 API Keys

| Service     | Purpose                 | Get From                             |
| ----------- | ----------------------- | ------------------------------------ |
| Kickstarter | Search & fetch projects | Browser DevTools (F12 → Network)     |
| ClickUp     | Voice guidelines & SOP  | https://clickup.com/api              |
| OpenAI      | LLM scoring             | https://platform.openai.com/api-keys |
| Supabase    | Database storage        | https://supabase.com/dashboard       |

## 🚀 Deployment

See **[SETUP.md](SETUP.md)** for:

- Docker deployment
- GitHub Actions scheduled runs
- Environment variable setup
- Credential management

## 📝 Development Notes

- **Python 3.10+** required
- **6 core dependencies**: curl-cffi, requests, python-dotenv, openai, supabase, python-dateutil
- **~50 total** (including transitive dependencies)
- Fully tested import chain
- No file output except `debug_merged.json`

## 📄 License

MIT

## 🤝 Contributing

Pull requests welcome. Please:

1. Test all 4 phases
2. Verify `.env` secrets not committed
3. Update SETUP.md for deployment changes
