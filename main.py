# main.py - Complete Kickstarter Monitor (Phases 1-4)
# Entry point: orchestrates Search → Fetch → Merge → Clean → ClickUp → LLM → Supabase
import os
import shutil
from datetime import datetime, timezone

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
# SCHEDULER FUNCTIONS
# =========================

def check_scheduler(last_run_file="last_run.txt"):
    """Check if enough time has passed since last successful run
    
    Args:
        last_run_file: Path to file storing timestamp of last successful run
    
    Returns:
        bool: True if should proceed with scraping, False if should skip
    """
    # Check if last_run.txt exists
    if not os.path.exists(last_run_file):
        logger.info("[SCHEDULER] No previous run found, proceeding with scraping")
        return True
    
    # Read timestamp from file
    try:
        with open(last_run_file, 'r') as f:
            last_run_timestamp_str = f.read().strip()
        
        last_run_dt = datetime.fromisoformat(last_run_timestamp_str)
        now = datetime.now(timezone.utc)
        
        # Calculate days since last run
        days_since_last_run = (now - last_run_dt.replace(tzinfo=timezone.utc)).days
        
        logger.info(f"[SCHEDULER] Last run: {last_run_dt}")
        logger.info(f"[SCHEDULER] Days since last run: {days_since_last_run}")
        
        if days_since_last_run >= 14:
            logger.info(f"[SCHEDULER] {days_since_last_run} days passed (>= 14), proceeding with scraping")
            return True
        else:
            logger.info(f"[SCHEDULER] Only {days_since_last_run} days passed (< 14), skipping this run")
            return False
    
    except Exception as e:
        logger.error(f"[SCHEDULER] Error reading {last_run_file}: {e}")
        logger.warning("[SCHEDULER] Proceeding with scraping due to read error")
        return True


def update_last_run(last_run_file="last_run.txt"):
    """Update last_run.txt with current timestamp after successful run
    
    Args:
        last_run_file: Path to file storing timestamp of last successful run
    """
    try:
        now = datetime.now(timezone.utc)
        with open(last_run_file, 'w') as f:
            f.write(now.isoformat())
        logger.info(f"[SCHEDULER] Updated {last_run_file} with timestamp: {now.isoformat()}")
    except Exception as e:
        logger.error(f"[SCHEDULER] Error writing {last_run_file}: {e}")


# =========================
# MAIN ORCHESTRATION
# =========================

def main():
    """Main entry point: orchestrate all 4 phases"""
    # ============ CLEANUP PYCACHE ============
    logger.info("\n" + "="*80)
    logger.info("CLEANING UP PYCACHE")
    logger.info("="*80)
    
    try:
        pycache_path = "__pycache__"
        if os.path.exists(pycache_path):
            shutil.rmtree(pycache_path, ignore_errors=True)
            logger.info(f"✅ Removed {pycache_path} folder")
        else:
            logger.info("✅ No pycache folder found to clean")
    except Exception as e:
        logger.warning(f"⚠️  Error cleaning pycache: {e}")
    
    # ============ SCHEDULER CHECK ============
    logger.info("\n" + "="*80)
    logger.info("STARTING KICKSTARTER MONITOR - SCHEDULER CHECK")
    logger.info("="*80)
    
    if not check_scheduler():
        logger.info("\n[SCHEDULER] Skipping run - less than 14 days since last successful run")
        return
    
    logger.info("\n[SCHEDULER] Proceeding with scraping...\n")
    
    # Track all errors throughout run for end-of-run summary alert
    run_errors = {
        "total_errors": 0,
        "cloudflare_blocks": [],
        "merge_failures": [],
        "phases": {}
    }
    
    try:
        # Phase 1a: Search
        search_result = search_phase()
        
        # Unpack search result (now returns dict with projects and failed_keywords)
        discovered = search_result.get("projects", [])
        failed_keywords = search_result.get("failed_keywords", [])
        
        # Track Cloudflare failures
        if failed_keywords:
            run_errors["cloudflare_blocks"] = failed_keywords
            run_errors["total_errors"] += len(failed_keywords)
            run_errors["phases"]["Phase 1 (Cloudflare Blocks)"] = len(failed_keywords)
        
        if not discovered:
            logger.error("❌ No projects discovered, stopping")
            # Send error summary before returning
            if run_errors["total_errors"] > 0:
                send_end_of_run_summary_alert(run_errors)
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
        
        # ============ SCHEDULER UPDATE ============
        # Only update last_run.txt after successful completion
        logger.info("\n[SCHEDULER] Scraping completed successfully, updating last_run.txt...")
        update_last_run()
    
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        # Send ClickUp alert for pipeline crash
        send_pipeline_crash_alert(str(e))
        # Also send error summary if we have partial errors
        if run_errors["total_errors"] > 0:
            send_end_of_run_summary_alert(run_errors)
        # NOTE: Do NOT update last_run.txt on failure - script will retry on next scheduled run
        logger.warning("[SCHEDULER] Scraping failed - NOT updating last_run.txt for retry on next run")
        raise


if __name__ == "__main__":
    main()