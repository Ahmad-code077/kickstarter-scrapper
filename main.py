# main.py - Complete Kickstarter Monitor (Phases 1-4)
# Entry point: orchestrates Search → Fetch → Merge → Clean → ClickUp → LLM → Supabase

import json

# Import from config (sets up logger and loads environment)
from config import logger

# Import phase functions
import phase1_search_fetch
from phase1_search_fetch import search_phase
from phase1_merge_clean import phase_1_search_fetch_merge_clean
from phase2_clickup import fetch_brand_voice, fetch_extraction_sop
from phase3_llm import phase_3_llm_scoring
from phase4_supabase import upsert_to_supabase

# Import alerting
from alerts import send_pipeline_crash_alert


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
        all_merged = phase_1_search_fetch_merge_clean(discovered, session=phase1_search_fetch._warmed_kickstarter_session)
        
        if not all_merged:
            logger.error("❌ No projects merged, stopping")
            return
        
        # Save debug file
        logger.info("\n📍 PHASE 1d: SAVE DEBUG FILE")
        logger.info("-" * 80)
        
        # Phase 2: Fetch ClickUp documents (Brand Voice + Extraction SOP)
        logger.info("\n📍 PHASE 2: FETCH CLICKUP DOCUMENTS")
        logger.info("-" * 80)
        brand_voice = fetch_brand_voice()
        extraction_sop = fetch_extraction_sop()
        
        # Phase 3: LLM scoring (only if both documents fetched)
        if brand_voice and extraction_sop:
            logger.info(f"\n✅ Both ClickUp documents fetched, starting LLM scoring...")
            all_merged = phase_3_llm_scoring(all_merged, brand_voice, extraction_sop)
        else:
            logger.warning("⚠️  Missing ClickUp documents, skipping LLM phase")
        
        # Phase 4: Store to Supabase
        upsert_to_supabase(all_merged)
        
        # Final summary
        logger.info("\n" + "=" * 80)
        logger.info("✅ KICKSTARTER MONITOR COMPLETE")
        logger.info("=" * 80)
        logger.info(f"📊 Processed: {len(all_merged)} projects")
        logger.info("=" * 80)
    
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")        # Send ClickUp alert for pipeline crash
        send_pipeline_crash_alert(str(e))        
        raise


if __name__ == "__main__":
    main()