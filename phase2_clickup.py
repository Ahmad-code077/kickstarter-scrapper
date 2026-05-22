# phase2_clickup.py - Phase 2: Fetch ClickUp Voice Guidelines

import requests

from config import (
    logger, CLICKUP_API_KEY, CLICKUP_WORKSPACE_ID, 
    CLICKUP_VOICE_DOC_ID, CLICKUP_VOICE_PAGE_ID,
    CLICKUP_SOP_EXTRACTION_DOC_ID, CLICKUP_SOP_EXTRACTION_PAGE_ID
)


# =========================
# PHASE 2: FETCH CLICKUP DOCUMENTS
# =========================

def _fetch_clickup_document(workspace_id, doc_id, page_id, doc_name):
    """Generic function to fetch a ClickUp document"""
    if not CLICKUP_API_KEY or not workspace_id or not doc_id or not page_id:
        logger.warning(f"⚠️  ClickUp credentials not set for {doc_name}, skipping")
        return None
    
    try:
        url = f"https://api.clickup.com/api/v3/workspaces/{workspace_id}/docs/{doc_id}/pages/{page_id}?content_format=text%2Fplain"
        headers = {
            "Authorization": CLICKUP_API_KEY,
            "Content-Type": "application/json"
        }
        
        logger.debug(f"[CLICKUP] Fetching {doc_name}: {url}")
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            content = data.get("content", "")
            logger.info(f"✅ {doc_name} fetched ({len(content)} chars)")
            return content
        else:
            logger.error(f"❌ {doc_name} fetch failed: {response.status_code}")
            return None
    
    except Exception as e:
        logger.error(f"❌ {doc_name} error: {e}")
        return None


def fetch_brand_voice():
    """Phase 2a: Fetch Brand Voice guidelines from ClickUp"""
    return _fetch_clickup_document(
        CLICKUP_WORKSPACE_ID,
        CLICKUP_VOICE_DOC_ID,
        CLICKUP_VOICE_PAGE_ID,
        "Brand Voice"
    )


def fetch_extraction_sop():
    """Phase 2b: Fetch Extraction SOP instructions from ClickUp"""
    return _fetch_clickup_document(
        CLICKUP_WORKSPACE_ID,
        CLICKUP_SOP_EXTRACTION_DOC_ID,
        CLICKUP_SOP_EXTRACTION_PAGE_ID,
        "Extraction SOP"
    )
