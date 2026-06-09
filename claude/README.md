# 🎯 Kickstarter Monitor Pipeline - Complete Project Guide

**Purpose:** A production-ready Python pipeline that discovers, evaluates, and scores Kickstarter projects related to travel/nomadic lifestyle using AI, then stores results in a PostgreSQL database.

**Target:** Automated discovery of promising Kickstarter projects for a newsletter focused on nomadic lifestyle products.

---

## 📋 Quick Overview

This is a **4-phase pipeline** orchestrated by a single entry point (`main.py`):

1. **Phase 1** - Search & Fetch from Kickstarter, clean data
2. **Phase 2** - Fetch brand voice guidelines from ClickUp
3. **Phase 3** - Score projects using OpenAI GPT-4
4. **Phase 4** - Store results in Supabase (PostgreSQL)

Each phase is modular and can run independently or as part of the full pipeline.

---

## 🏗️ Architecture & Data Flow

### High-Level Overview

```
┌─────────────────┐
│   main.py       │ (Orchestrator)
│  (Entry Point)  │
└────────┬────────┘
         │
         ├──→ [PHASE 1] Search & Fetch
         │    └─ phase1_search_fetch.py
         │    └─ phase1_merge_clean.py
         │    └─ Outputs: debug_merged.json
         │
         ├──→ [PHASE 2] ClickUp Voice Guidelines
         │    └─ phase2_clickup.py
         │    └─ Fetches: Brand Voice + Extraction SOP
         │
         ├──→ [PHASE 3] LLM Scoring
         │    └─ phase3_llm.py
         │    └─ Uses: OpenAI GPT-4 with guidelines
         │    └─ Outputs: Scored projects
         │
         └──→ [PHASE 4] Persist to Supabase
              └─ phase4_supabase.py
              └─ Table: kickstarter_projects
```

### Detailed Data Flow

#### **PHASE 1: Search, Fetch & Clean**

**Input:** Keywords (pipe-separated: "travel bag|backpack|sling bag")

**Process:**

```
1. Load keywords from .env (KICKSTARTER_KEYWORDS)
2. For each keyword:
   a) Call Kickstarter REST API search endpoint
   b) Get paginated results (up to MAX_PAGES)
   c) Filter by DAYS_BACK parameter
   d) For each discovered project:
      - Fetch full details using GraphQL endpoint
      - Merge REST + GraphQL data
      - Flatten nested structures
      - Clean HTML story → plain text
      - Deduplicate by project_id
   e) Append to results list
3. Save merged results to debug_merged.json
4. Return projects list to main.py
```

**Key Fields Extracted:**

- `project_id` - Unique Kickstarter ID
- `project_name` - Campaign title
- `blurb` - Short description
- `story_clean` - Full story (HTML cleaned to plain text)
- `percent_funded` - Funding percentage
- `backers_count` - Number of backers
- `comments_count` - Community engagement
- `staff_pick` - Kickstarter staff selection flag
- `creator_name` - Campaign creator
- `creator_past_campaigns` - Creator's track record
- `launched_at` - Campaign start date
- `deadline` - Campaign end date
- `country` - Project location
- `main_image` - Primary project image
- `project_url` - Direct link to Kickstarter

**Files Involved:**

- `phase1_search_fetch.py` - REST API search + GraphQL fetch
- `phase1_merge_clean.py` - Data merging & cleaning
- `config.py` - Configuration & logging

---

#### **PHASE 2: Fetch ClickUp Voice Guidelines**

**Input:** ClickUp API credentials from .env

**Process:**

```
1. Fetch Brand Voice document from ClickUp
   - Contains: Brand tone, style guidelines, messaging rules
2. Fetch Extraction & Scoring SOP document from ClickUp
   - Contains: JSON schema, evaluation criteria, scoring instructions
3. Return both as plain text strings to Phase 3
```

**Purpose:**
These documents are used as system prompts for the OpenAI API. They ensure consistent evaluation based on brand guidelines and specific scoring instructions.

**Files Involved:**

- `phase2_clickup.py` - Document fetching functions

---

#### **PHASE 3: LLM Scoring with OpenAI**

**Input:**

- Projects from Phase 1
- Brand Voice guidelines from Phase 2
- Extraction SOP from Phase 2
- OpenAI API key from .env

**Process:**

```
For each project:
  1. Prepare limited project input (8 key fields):
     - project_name, blurb, story_clean, percent_funded
     - backers_count, comments_count, staff_pick, creator_past_campaigns

  2. Create OpenAI prompt:
     SYSTEM: Brand Voice + Extraction SOP + Instructions
     USER: Project data above

  3. Send to GPT-4 API

  4. Parse JSON response containing:
     - relevance_score (1-10)
     - score_reason (why this score)
     - product_summary (brief overview)
     - key_features (list)
     - concerns (list)

  5. Merge scoring back to original project object

  6. Add rate limiting delay (OPENAI_REQUEST_DELAY env var)
```

**Output:** Projects enriched with AI-generated scoring and analysis

**Files Involved:**

- `phase3_llm.py` - OpenAI scoring logic

---

#### **PHASE 4: Persist to Supabase**

**Input:**

- Scored projects from Phase 3
- Supabase connection credentials from .env

**Process:**

```
For each project:
  1. Map project fields to Supabase table schema
  2. Prepare upsert operation (insert if new, update if exists)
  3. Key field for uniqueness: project_id
  4. Send to Supabase kickstarter_review table
  5. Log success/failure
```

**Supabase Table: `kickstarter_review`**

- `id` - Auto-generated primary key
- `project_id` - Unique Kickstarter ID (upsert key)
- `project_name`, `blurb`, `story` - Project details
- `percent_funded`, `backers_count`, `comments_count` - Metrics
- `staff_pick`, `creator_name`, `creator_past_campaigns` - Credibility
- `relevance_score`, `score_reason` - AI scoring
- `product_summary`, `key_features`, `concerns` - AI analysis
- `project_url`, `main_image` - Media
- `created_at` - Timestamp

**Files Involved:**

- `phase4_supabase.py` - Supabase upsert logic
- `config.py` - Supabase client initialization

---

## 📂 File Structure & Responsibilities

### Core Files

| File        | Purpose                                                                             | Dependencies                    |
| ----------- | ----------------------------------------------------------------------------------- | ------------------------------- |
| `main.py`   | **Orchestrator** - Controls all 4 phases, scheduler logic, error handling, alerting | All phase files, config, alerts |
| `config.py` | **Configuration hub** - Loads .env, sets up logging, initializes Supabase client    | python-dotenv, supabase         |
| `alerts.py` | **Error handling** - Sends Slack alerts on crash or completion                      | requests, config                |

### Phase Files

| File                     | Purpose                                                    | Phase |
| ------------------------ | ---------------------------------------------------------- | ----- |
| `phase1_search_fetch.py` | Search Kickstarter REST API, paginate results              | 1     |
| `phase1_merge_clean.py`  | Fetch GraphQL details, merge data, clean HTML, deduplicate | 1     |
| `phase2_clickup.py`      | Fetch brand voice & SOP documents from ClickUp             | 2     |
| `phase3_llm.py`          | Score projects using OpenAI GPT-4 with ClickUp guidelines  | 3     |
| `phase4_supabase.py`     | Upsert scored projects to PostgreSQL via Supabase          | 4     |

### Support Files

| File                    | Purpose                                       |
| ----------------------- | --------------------------------------------- |
| `requirements.txt`      | Python dependencies                           |
| `README.md`             | Project overview (root level)                 |
| `SETUP.md`              | Detailed setup & deployment guide             |
| `test_graphql_debug.py` | Debug script for testing GraphQL queries      |
| `logs/`                 | Directory containing timestamped log files    |
| `debug_merged.json`     | Output from Phase 1 (all discovered projects) |

---

## 🔧 Setup & Configuration

### Prerequisites

- **Python 3.10+**
- **Git**
- Kickstarter cookies & CSRF token (from browser DevTools)
- _Optional:_ ClickUp, OpenAI, Supabase accounts

### Environment Variables (.env)

Create `.env` file in project root. Copy from `.env.example` if available.

#### **Required for Phase 1 (Search & Fetch)**

```env
# Kickstarter API credentials
KICKSTARTER_CSRF_TOKEN=<get from browser DevTools>
KICKSTARTER_COOKIE_STRING=<get from browser DevTools>

# Search parameters
KICKSTARTER_KEYWORDS=travel bag|backpack|sling bag
KICKSTARTER_DAYS_BACK=14          # Only projects from last N days
KICKSTARTER_MAX_PAGES=10          # Max pages per keyword
KICKSTARTER_REQUEST_DELAY=1       # Delay between API calls (seconds)

# Logging
LOG_LEVEL=INFO
```

#### **Optional for Phase 2 (ClickUp)**

```env
# ClickUp credentials
CLICKUP_API_KEY=pk_...
CLICKUP_WORKSPACE_ID=3666576
CLICKUP_VOICE_DOC_ID=3fwmg-16918
CLICKUP_VOICE_PAGE_ID=3fwmg-2598
CLICKUP_SOP_EXTRACTION_DOC_ID=3fwmg-17058
CLICKUP_SOP_EXTRACTION_PAGE_ID=3fwmg-2658
```

#### **Optional for Phase 3 (OpenAI)**

```env
# OpenAI credentials
OPENAI_API_KEY=sk_...
OPENAI_REQUEST_DELAY=2       # Rate limiting for API calls
```

#### **Optional for Phase 4 (Supabase)**

```env
# Supabase credentials
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_KEY=eyJhbGc...
```

---

## 🚀 How to Run

### 1. Install Dependencies

```bash
python -m venv venv
source venv/Scripts/activate    # Windows: .\venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env with your credentials
```

### 3. Run Full Pipeline

```bash
python main.py
```

### 4. Monitor Output

**Console Output:**

- Real-time progress logs
- Phase-by-phase status
- Error messages & warnings

**Logs Directory:**

```
logs/kickstarter-monitor-2024-01-15-1430.log
logs/kickstarter-monitor-2024-01-15-1445.log
...
```

**Debugging Output:**

```
debug_merged.json  # All discovered projects after Phase 1
```

---

## 🔑 Key Functions & Methods

### main.py

| Function              | Purpose                                                                         |
| --------------------- | ------------------------------------------------------------------------------- |
| `check_scheduler()`   | Checks if 14+ days passed since last run (uses Supabase pipeline_control table) |
| `run_full_pipeline()` | Orchestrates all 4 phases, handles errors, sends alerts                         |
| Main block            | Entry point: loads config, checks scheduler, calls pipeline                     |

### phase1_search_fetch.py

| Function                       | Purpose                                                |
| ------------------------------ | ------------------------------------------------------ |
| `search_phase()`               | REST API search across all keywords, paginates results |
| `fetch_full_details_graphql()` | GraphQL query for detailed project data                |

### phase1_merge_clean.py

| Function                             | Purpose                                                                            |
| ------------------------------------ | ---------------------------------------------------------------------------------- |
| `phase_1_search_fetch_merge_clean()` | Main Phase 1 function; calls search, fetches GraphQL, merges, cleans, deduplicates |
| `merge_data()`                       | Combines REST + GraphQL data                                                       |
| `flatten_nested_structures()`        | Flattens nested JSON objects                                                       |
| `clean_html_story()`                 | Converts HTML story to plain text                                                  |

### phase2_clickup.py

| Function                    | Purpose                                   |
| --------------------------- | ----------------------------------------- |
| `fetch_brand_voice()`       | Fetches brand voice document              |
| `fetch_extraction_sop()`    | Fetches extraction & scoring SOP document |
| `_fetch_clickup_document()` | Generic fetch function for ClickUp docs   |

### phase3_llm.py

| Function                   | Purpose                                       |
| -------------------------- | --------------------------------------------- |
| `phase_3_llm_scoring()`    | Main Phase 3 function; scores all projects    |
| `score_with_openai()`      | Sends single project to GPT-4 with guidelines |
| `_prepare_project_input()` | Extracts 8 key fields for LLM input           |

### phase4_supabase.py

| Function                        | Purpose                                     |
| ------------------------------- | ------------------------------------------- |
| `upsert_to_supabase()`          | Main Phase 4 function; upserts all projects |
| `map_project_to_review_table()` | Maps project dict to Supabase schema        |

### config.py

| Function          | Purpose                              |
| ----------------- | ------------------------------------ |
| `setup_logging()` | Configures logging to console & file |

---

## 🧠 How Each Phase Works In Detail

### Phase 1: Search & Fetch (Rest + GraphQL)

**Why two endpoints?**

- **REST API** - Fast search, gets basic project data, pagination
- **GraphQL** - Detailed project data, story HTML, creator info

**What happens:**

1. Split KICKSTARTER_KEYWORDS by pipe (|)
2. For each keyword:
   - Call REST API with filters (days_back, pages)
   - Get paginated list of project IDs
   - For each ID:
     - Call GraphQL for full details
     - Extract & merge fields
     - Clean HTML story to plain text
     - Deduplicate by project_id
3. Save all to debug_merged.json
4. Return list to main.py

**Output Sample (debug_merged.json):**

```json
[
  {
    "project_id": "123456789",
    "project_name": "Ultra-Light Travel Backpack",
    "blurb": "The perfect companion for nomadic travelers",
    "story_clean": "After 5 years of traveling...",
    "percent_funded": 150,
    "backers_count": 2500,
    "comments_count": 342,
    "staff_pick": true,
    "creator_name": "Jane Doe",
    "creator_past_campaigns": 3,
    "launched_at": "2024-01-10T00:00:00Z",
    "deadline": "2024-02-10T00:00:00Z",
    "country": "US",
    "main_image": "https://...",
    "project_url": "https://www.kickstarter.com/projects/..."
  },
  ...
]
```

---

### Phase 2: Fetch ClickUp Guidelines

**What happens:**

1. Check if ClickUp API key & doc IDs are in .env
2. Call ClickUp API for Brand Voice document
3. Call ClickUp API for Extraction SOP document
4. Return both as plain text strings

**Used in Phase 3 as system prompts for OpenAI**

---

### Phase 3: LLM Scoring

**What happens:**

1. For each project from Phase 1:
   - Extract 8 key fields (name, blurb, story, metrics, creator info)
   - Build OpenAI prompt:
     - **System**: Brand Voice + SOP + Instructions
     - **User**: Project data
   - Send to GPT-4
   - Parse JSON response with:
     - `relevance_score` (1-10)
     - `score_reason` (why)
     - `product_summary`
     - `key_features` (array)
     - `concerns` (array)
   - Merge back to project object
   - Sleep OPENAI_REQUEST_DELAY seconds

**Output Sample (enriched project):**

```json
{
  "project_id": "123456789",
  ...existing fields...,
  "relevance_score": 8,
  "score_reason": "Strong product-market fit, excellent creator track record, high backer engagement",
  "product_summary": "Innovative ultralight backpack with modular compartments",
  "key_features": ["Modular design", "Under 500g weight", "Waterproof zippers"],
  "concerns": ["Premium pricing", "New brand in market"]
}
```

---

### Phase 4: Persist to Supabase

**What happens:**

1. Connect to Supabase (PostgreSQL)
2. For each project:
   - Map fields to `kickstarter_review` table schema
   - Upsert using `project_id` as unique key
   - Add `created_at` timestamp

**Result:** Data stored in PostgreSQL, queryable via Supabase

---

## 🔄 Scheduler Logic

The pipeline includes a scheduler that:

1. **Checks Supabase `pipeline_control` table** for:
   - `last_cycle_completed_at` - Timestamp of last successful run
   - `python_ready` - Boolean flag (false = ready to scrape)

2. **Calculates days since last run:**
   - If 14+ days passed AND `python_ready=false`
   - Then: Proceed with full pipeline
   - Else: Skip (wait for next cycle or manual intervention)

3. **Updates control table after completion:**
   - Sets `last_cycle_completed_at` to current time
   - Sets `python_ready` to false (ready for next cycle)

**Purpose:** Prevents redundant runs, coordinates with other systems

---

## 📊 Useful Debug Files

### debug_merged.json

- **What:** All discovered projects after Phase 1
- **When:** Generated after Phase 1 completes
- **How to inspect:** `cat debug_merged.json | jq '.[0]'` (first project)

### logs/kickstarter-monitor-\*.log

- **What:** Timestamped log files with full execution history
- **Location:** `logs/` directory
- **Latest:** Check most recent by date

### test_graphql_debug.py

- **What:** Standalone script to debug GraphQL queries
- **Use:** When Phase 1 fails, test GraphQL directly

---

## 🚨 Error Handling & Alerts

### Alert Destinations

- **Slack** - Pipeline crashes & completion summaries (if configured)
- **Logs** - All errors in log files
- **Console** - Real-time status updates

### Common Issues & Fixes

| Issue                        | Cause                                   | Fix                                       |
| ---------------------------- | --------------------------------------- | ----------------------------------------- |
| "GraphQL fetch failed"       | Kickstarter API down or cookies expired | Update KICKSTARTER_COOKIE_STRING in .env  |
| "ClickUp not configured"     | Missing ClickUp API key                 | Add CLICKUP_API_KEY to .env (optional)    |
| "OpenAI rate limit"          | Too many API calls                      | Increase OPENAI_REQUEST_DELAY in .env     |
| "Supabase connection failed" | Invalid credentials                     | Check SUPABASE_URL & SUPABASE_KEY in .env |

---

## 🔐 Security Notes

- **Never commit .env file** - Contains API keys
- **Cookies expire** - Update KICKSTARTER_COOKIE_STRING periodically
- **API keys rotate** - Update all keys in .env if compromised
- **Logs contain sensitive data** - Rotate logs directory regularly

---

## 💾 Dependencies Explained

| Package           | Version  | Purpose                                    |
| ----------------- | -------- | ------------------------------------------ |
| `curl-cffi`       | >=0.15.0 | Fast HTTP client for Kickstarter API calls |
| `requests`        | >=2.34.2 | HTTP library for ClickUp & other APIs      |
| `python-dotenv`   | >=1.2.2  | Load .env variables                        |
| `openai`          | >=2.38.0 | OpenAI GPT-4 API client                    |
| `supabase`        | >=2.30.0 | Supabase PostgreSQL client                 |
| `python-dateutil` | >=2.9.0  | Date parsing & manipulation                |

---

## 📈 Performance Notes

- **Phase 1:** ~1-5 minutes (depends on keywords, pages, API delays)
- **Phase 2:** <1 second (ClickUp API usually fast)
- **Phase 3:** ~30 seconds - 2 minutes (GPT-4 with rate limiting)
- **Phase 4:** ~1 minute (Supabase batch upsert)
- **Total:** ~2-8 minutes (full pipeline)

---

## 🎓 Understanding the Code

### Entering main.py

The entry point does:

```python
if __name__ == "__main__":
    logger.info("Starting Kickstarter Monitor...")

    # 1. Check scheduler (if 14+ days)
    should_run = check_scheduler()

    if should_run:
        # 2. Run full pipeline (all 4 phases)
        run_full_pipeline()
    else:
        logger.info("Not time to scrape yet")
```

### Flow Through Phases

```
main.py
├─ check_scheduler() → bool
├─ run_full_pipeline()
│  ├─ Phase 1: phase_1_search_fetch_merge_clean() → [projects]
│  ├─ Phase 2: fetch_brand_voice() + fetch_extraction_sop() → (str, str)
│  ├─ Phase 3: phase_3_llm_scoring(projects, voice, sop) → [scored_projects]
│  └─ Phase 4: upsert_to_supabase([scored_projects]) → DB
└─ send_end_of_run_summary_alert() → Slack
```

---

## 🔗 External APIs Used

| API                 | Purpose                | Auth                 | Phase |
| ------------------- | ---------------------- | -------------------- | ----- |
| Kickstarter REST    | Project search         | CSRF token + cookies | 1     |
| Kickstarter GraphQL | Detailed project data  | CSRF token + cookies | 1     |
| ClickUp API         | Brand voice & SOP docs | API key              | 2     |
| OpenAI API          | GPT-4 scoring          | API key              | 3     |
| Supabase API        | PostgreSQL access      | URL + API key        | 4     |

---

## 📝 Next Steps for Development

1. **Optimize Phase 1:** Add caching for repeated searches
2. **Enhance Phase 3:** A/B test different prompts for better scoring
3. **Monitor Phase 4:** Set up Supabase alerts for data quality
4. **Add Phase 5:** Email digest generation from scored projects
5. **Improve logging:** Add structured JSON logs for analytics

---

## 📞 Quick Reference

| Task              | Command                                     |
| ----------------- | ------------------------------------------- |
| Run full pipeline | `python main.py`                            |
| View logs         | `tail -f logs/kickstarter-monitor-*.log`    |
| Test GraphQL      | `python test_graphql_debug.py`              |
| View debug data   | `cat debug_merged.json \| jq '.'`           |
| Check .env        | `cat .env` (but don't commit!)              |
| Update deps       | `pip install -r requirements.txt --upgrade` |

---

## Version & Last Updated

- **Version:** 1.0.0
- **Last Updated:** 2024-01-15
- **Status:** Production-Ready
- **Maintainer:** Nomad Nation Team
