# Kickstarter Monitor - Setup & Deployment Guide

## 📋 Prerequisites

- Python 3.10+
- Git
- Kickstarter browser cookies & CSRF token (from DevTools)
- (Optional) ClickUp, OpenAI, Supabase accounts

## 🚀 Local Development Setup

### 1. Clone & Navigate

```bash
git clone <repo-url>
cd kickstarter-monitor
```

### 2. Create Virtual Environment

```bash
# Windows
python -m venv venv
.\venv\Scripts\activate

# Mac/Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment

```bash
# Copy example file
cp .env.example .env

# Edit .env with your credentials
# Required: KICKSTARTER_* variables
# Optional: CLICKUP_*, OPENAI_API_KEY, SUPABASE_*
```

**Required Variables** (Phase 1 works alone):

```env
KICKSTARTER_KEYWORDS=travel bag|backpack|sling bag
KICKSTARTER_DAYS_BACK=14
KICKSTARTER_MAX_PAGES=10
KICKSTARTER_REQUEST_DELAY=1
KICKSTARTER_CSRF_TOKEN=<from browser DevTools Network tab>
KICKSTARTER_COOKIE_STRING=<from browser DevTools>
```

**Optional Variables** (Enable phases 2-4):

```env
# Phase 2: ClickUp voice guidelines
CLICKUP_WORKSPACE_ID=3666576
CLICKUP_VOICE_DOC_ID=3fwmg-16918
CLICKUP_VOICE_PAGE_ID=3fwmg-2598
CLICKUP_SOP_EXTRACTION_DOC_ID=3fwmg-17058
CLICKUP_SOP_EXTRACTION_PAGE_ID=3fwmg-2658
CLICKUP_API_KEY=pk_...

# Phase 3: LLM scoring
OPENAI_API_KEY=sk_...

# Phase 4: Database storage
SUPABASE_URL=https://...supabase.co
SUPABASE_KEY=eyJhbGc...

# Logging
LOG_LEVEL=INFO
```

### 5. Run the Monitor

```bash
python main.py
```

**Output**:

- `debug_merged.json` - All discovered & processed projects
- Console logs - Real-time progress
- Supabase - Project data persisted (if Phase 4 enabled)

## 📦 Project Structure

```
kickstarter-monitor/
├── main.py                    # Entry point (orchestrates phases)
├── config.py                  # Logging & env variables
├── phase1_search_fetch.py     # Search & GraphQL fetch
├── phase1_merge_clean.py      # Merge & clean data
├── phase2_clickup.py          # Fetch ClickUp documents
├── phase3_llm.py              # OpenAI LLM scoring
├── phase4_supabase.py         # Supabase persistence
├── requirements.txt           # Dependencies
├── .env.example              # Template for .env (commit this)
├── .gitignore                # Git exclusions
├── README.md                 # Architecture & workflow
└── SETUP.md                  # This file
```

## 🔄 How It Works

### Phase 1: Search, Fetch & Clean

1. Discover projects via Kickstarter REST API (keywords)
2. Fetch full details via GraphQL API (for each project)
3. Merge discovery + GraphQL data → flat JSON object
4. Clean HTML story → plain text
5. Save `debug_merged.json`

**Inputs**: Keywords, date range, pagination  
**Outputs**: Flat project objects with clean metadata

### Phase 2: Fetch ClickUp Documents

1. Retrieve **Brand Voice** guidelines (tone/rules)
2. Retrieve **Extraction SOP** (scoring instructions)

**Inputs**: ClickUp workspace ID, document IDs, API key  
**Outputs**: Document content as text

### Phase 3: LLM Scoring

1. For each project:
   - Select 8 key fields (name, blurb, story, funding, backers, etc.)
   - Send to GPT-4 with ClickUp documents
   - Parse JSON response (format defined in SOP)
2. Merge LLM output with original project metadata

**Inputs**: Projects, Brand Voice, Extraction SOP  
**Outputs**: Projects with LLM scores & recommendations

### Phase 4: Store to Supabase

1. Batch upsert all projects to `kickstarter_projects` table
2. Use `project_id` as unique key (on_conflict)
3. Update `updated_at` timestamp

**Inputs**: Processed projects  
**Outputs**: Data in Supabase

## 🔑 Getting Credentials

### Kickstarter

1. Open any Kickstarter project in browser
2. Press F12 → Network tab
3. Reload page, find any API request
4. Copy `x-csrf-token` header → `KICKSTARTER_CSRF_TOKEN`
5. Copy `cookie` header → `KICKSTARTER_COOKIE_STRING`

### ClickUp

1. Go to [ClickUp](https://clickup.com/api) dashboard
2. Create API token
3. Get workspace/doc/page IDs from URL

### OpenAI

1. Visit [OpenAI API Keys](https://platform.openai.com/api-keys)
2. Create new secret key

### Supabase

1. Go to [Supabase](https://supabase.com) project
2. Settings → API keys
3. Copy URL and public anon key

## 🚀 Deployment

### Environment Variables

- **Never commit `.env`** (included in `.gitignore`)
- Commit `.env.example` as template
- Set env vars in deployment platform:
  - GitHub Actions: Secrets
  - Heroku/Railway: Config Vars
  - AWS Lambda: Environment Variables
  - Docker: Pass via `docker run -e KEY=value`

### Docker (Optional)

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["python", "main.py"]
```

```bash
docker build -t kickstarter-monitor .
docker run -e KICKSTARTER_KEYWORDS=... kickstarter-monitor
```

### GitHub Actions Workflow

```yaml
name: Run Kickstarter Monitor
on:
  schedule:
    - cron: '0 0 * * *' # Daily at midnight
  workflow_dispatch:

jobs:
  monitor:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.12'
      - run: pip install -r requirements.txt
      - run: python main.py
        env:
          KICKSTARTER_KEYWORDS: ${{ secrets.KICKSTARTER_KEYWORDS }}
          KICKSTARTER_CSRF_TOKEN: ${{ secrets.KICKSTARTER_CSRF_TOKEN }}
          KICKSTARTER_COOKIE_STRING: ${{ secrets.KICKSTARTER_COOKIE_STRING }}
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
          SUPABASE_URL: ${{ secrets.SUPABASE_URL }}
          SUPABASE_KEY: ${{ secrets.SUPABASE_KEY }}
          CLICKUP_API_KEY: ${{ secrets.CLICKUP_API_KEY }}
```

## 🐛 Troubleshooting

### "No projects discovered"

- Check `KICKSTARTER_KEYWORDS` format (pipe-separated)
- Verify CSRF token & cookies are fresh
- Check `KICKSTARTER_DAYS_BACK` value

### "Cloudflare challenge detected"

- Your IP might be rate-limited
- Increase `KICKSTARTER_REQUEST_DELAY` (default 1s)
- Use VPN if blocked

### "OpenAI timeout"

- Check your OpenAI API balance
- Verify `gpt-4` model access in your account
- Reduce project batch size if needed

### "Supabase connection failed"

- Verify `SUPABASE_URL` and `SUPABASE_KEY`
- Check table `kickstarter_projects` exists
- Ensure network allows Supabase connections

## 📝 Notes

- Credentials expire periodically - refresh if API calls fail
- LLM scoring costs money (OpenAI API charges per token)
- Be respectful to Kickstarter API (1 second delay between requests recommended)
- ClickUp & Supabase are optional - monitor works without them
- Phase 1 can run completely standalone for discovery

## 📞 Support

For issues:

1. Check `.gitignore` doesn't exclude important files
2. Verify all `.env` variables are set correctly
3. Review logs: `python main.py 2>&1 | tee run.log`
4. Check GitHub Issues
