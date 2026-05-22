# main.py - Complete Kickstarter Monitor (Phases 1-4)
# Entry point: orchestrates Search → Fetch → Merge → Clean → ClickUp → LLM → Supabase

import json

# Import from config (sets up logger and loads environment)
from config import logger

# Import phase functions
from phase1_search_fetch import search_phase
from phase1_merge_clean import phase_1_search_fetch_merge_clean
from phase2_clickup import fetch_clickup_guidelines
from phase3_llm import phase_3_llm_scoring
from phase4_supabase import upsert_to_supabase


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
        all_merged = phase_1_search_fetch_merge_clean(discovered)
        
        if not all_merged:
            logger.error("❌ No projects merged, stopping")
            return
        
        # Save debug file
        logger.info("\n📍 PHASE 1d: SAVE DEBUG FILE")
        logger.info("-" * 80)
        with open("debug_merged.json", "w", encoding="utf-8") as f:
            json.dump(all_merged, f, indent=2, ensure_ascii=False)
        logger.info(f"✅ Saved debug_merged.json ({len(all_merged)} projects)")
        
        # Phase 2: Fetch ClickUp guidelines
        voice_guidelines = fetch_clickup_guidelines()
        logger.debug(f"Voice Guidelines:\n{voice_guidelines[:500]}...")  # Log first 500 chars
        
        logger.info(f"\n✅ Starting LLM scoring with OpenAI...",all_merged)
        # Phase 3: LLM scoring
        if voice_guidelines:
            all_merged = phase_3_llm_scoring(all_merged, voice_guidelines)
        
        # Phase 4: Store to Supabase
        upsert_to_supabase(all_merged)
        
        # Final summary
        logger.info("\n" + "=" * 80)
        logger.info("✅ KICKSTARTER MONITOR COMPLETE")
        logger.info("=" * 80)
        logger.info(f"📊 Processed: {len(all_merged)} projects")
        logger.info(f"💾 Debug file: debug_merged.json")
        logger.info("=" * 80)
    
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        raise


if __name__ == "__main__":
    main()