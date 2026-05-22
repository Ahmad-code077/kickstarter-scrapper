# phase2_clickup.py - Phase 2: Fetch ClickUp Voice Guidelines

import requests

from config import (
    logger, CLICKUP_API_KEY, CLICKUP_WORKSPACE_ID, 
    CLICKUP_DOC_ID, CLICKUP_PAGE_ID
)


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
        # Fetch ClickUp document voice
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
