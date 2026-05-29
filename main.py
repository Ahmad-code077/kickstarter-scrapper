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
from alerts import send_pipeline_crash_alert, send_end_of_run_summary_alert


# =========================
# MAIN ORCHESTRATION
# =========================

def main():
    """Main entry point: orchestrate all 4 phases"""
    # Track all errors throughout run for end-of-run summary alert
    run_errors = {
        "total_errors": 0,
        "merge_failures": [],
        "phases": {}
    }
    
    try:
        # Phase 1a: Search
        discovered = search_phase()
        
        if not discovered:
            logger.error("❌ No projects discovered, stopping")
            return
        
        # Phase 1b & 1c: Fetch, Merge, Clean
        phase1_result = phase_1_search_fetch_merge_clean(discovered, session=phase1_search_fetch._warmed_kickstarter_session)
        
        # Unpack result (now a dict with 'merged' and 'failed')
        all_merged = phase1_result.get("merged", [])
        phase1_failed = phase1_result.get("failed", [])
        
        # Track phase 1 errors
        if phase1_failed:
            run_errors["phases"]["Phase 1 (GraphQL Merge)"] = len(phase1_failed)
            run_errors["total_errors"] += len(phase1_failed)
            for project_id in phase1_failed:
                run_errors["merge_failures"].append((project_id, "GraphQL fetch or merge failed"))
        
        if not all_merged:
            logger.error("❌ No projects merged, stopping")
            # Send error summary before returning
            if run_errors["total_errors"] > 0:
                send_end_of_run_summary_alert(run_errors)
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
        if run_errors["total_errors"] > 0:
            logger.warning(f"⚠️  Total errors encountered: {run_errors['total_errors']}")
        logger.info("=" * 80)
        
        # Send end-of-run error summary if any errors occurred
        if run_errors["total_errors"] > 0:
            logger.info("[ALERT] Sending end-of-run error summary...")
            send_end_of_run_summary_alert(run_errors)
    
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        # Send ClickUp alert for pipeline crash
        send_pipeline_crash_alert(str(e))
        # Also send error summary if we have partial errors
        if run_errors["total_errors"] > 0:
            send_end_of_run_summary_alert(run_errors)
        raise


if __name__ == "__main__":
    main()