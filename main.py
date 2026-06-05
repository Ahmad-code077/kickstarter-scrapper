# main.py - Complete Kickstarter Monitor (Phases 1-4)
# Entry point: orchestrates Search → Fetch → Merge → Clean → ClickUp → LLM → Supabase
import os
import shutil
from datetime import datetime, timezone

# Import from config (sets up logger and loads environment)
from config import logger, supabase_client

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

def check_scheduler():
    """Check if enough time has passed since last successful run using Supabase
    
    Fetches from new_drops_pipeline_control table:
    - last_cycle_completed_at: UTC timestamp of last successful run
    - python_ready: boolean indicating if data is already prepared
    
    Returns:
        bool: True if should proceed with scraping (14+ days AND python_ready=false)
    """
    if not supabase_client:
        logger.warning("[SCHEDULER] Supabase not configured, proceeding with scraping")
        return True
    
    try:
        # Fetch pipeline control row
        response = supabase_client.table("new_drops_pipeline_control").select("last_cycle_completed_at, python_ready").eq("id", "new_drops").execute()
        
        if not response.data:
            logger.info("[SCHEDULER] No previous cycle found in Supabase, proceeding with scraping")
            return True
        
        control_row = response.data[0]
        last_cycle_completed_at = control_row.get("last_cycle_completed_at")
        python_ready = control_row.get("python_ready", False)
        
        logger.info("\n" + "="*80)
        logger.info("[SCHEDULER] 📊 DETAILED DATE CALCULATION REPORT")
        logger.info("="*80)
        
        # ========== SUPABASE DATA ==========
        logger.info("\n[SCHEDULER] 🗄️  SUPABASE DATA:")
        logger.info(f"  • last_cycle_completed_at (raw): {last_cycle_completed_at}")
        logger.info(f"  • python_ready: {python_ready}")
        
        # Parse timestamp (already UTC)
        last_dt = datetime.fromisoformat(last_cycle_completed_at.replace("Z", "+00:00"))
        now_utc = datetime.now(timezone.utc)
        
        logger.info("\n[SCHEDULER] 🔄 TIMESTAMP PARSING:")
        logger.info(f"  • Parsed last_cycle_completed_at: {last_dt}")
        logger.info(f"  • Current time (UTC): {now_utc}")
        logger.info(f"  • Timezone info (last_dt): {last_dt.tzinfo}")
        logger.info(f"  • Timezone info (now_utc): {now_utc.tzinfo}")
        
        # Extract calendar dates
        last_date = last_dt.date()
        now_date = now_utc.date()
        
        logger.info("\n[SCHEDULER] 📅 CALENDAR DATES (ignoring time):")
        logger.info(f"  • Last cycle date: {last_date} ({last_date.strftime('%A, %B %d, %Y')})")
        logger.info(f"  • Current date: {now_date} ({now_date.strftime('%A, %B %d, %Y')})")
        
        # Calculate days difference
        days_delta = now_date - last_date
        days_since = days_delta.days
        
        logger.info("\n[SCHEDULER] 🧮 DATE DIFFERENCE CALCULATION:")
        logger.info(f"  • Days delta: {now_date} - {last_date}")
        logger.info(f"  • Days since last cycle: {days_since}")
        logger.info(f"  • Required days: 14")
        logger.info(f"  • Condition (days_since >= 14): {days_since >= 14}")
        
        # ========== DECISION LOGIC ==========
        logger.info("\n[SCHEDULER] ⚙️  DECISION LOGIC:")
        logger.info(f"  • Requirement 1: days_since ({days_since}) >= 14? {days_since >= 14}")
        logger.info(f"  • Requirement 2: python_ready ({python_ready}) == False? {not python_ready}")
        logger.info(f"  • Both conditions met? {(days_since >= 14) and (not python_ready)}")
        
        # Run if: 14+ days passed AND data not yet prepared (python_ready=false)
        if days_since >= 14 and not python_ready:
            logger.info("\n[SCHEDULER] ✅ GO AHEAD WITH SCRAPING")
            logger.info(f"  Reason: {days_since} days have passed (>= 14 required) AND data not yet prepared")
            logger.info("="*80 + "\n")
            return True
        else:
            logger.info("\n[SCHEDULER] ⏸️  SKIP THIS RUN")
            if days_since < 14:
                logger.info(f"  Reason: Only {days_since} days passed. Need 14 days. Wait {14 - days_since} more day(s)")
            elif python_ready:
                logger.info(f"  Reason: Data already prepared (python_ready=true). Waiting for next cycle")
            logger.info("="*80 + "\n")
            return False
    
    except Exception as e:
        logger.error(f"[SCHEDULER] Error fetching from Supabase: {e}")
        logger.warning("[SCHEDULER] Proceeding with scraping due to read error")
        return True


def update_last_run():
    """Update Supabase pipeline control after successful run
    
    Sets:
    - python_ready: true (data has been prepared)
    - python_completed_at: current UTC timestamp
    """
    if not supabase_client:
        logger.warning("[SCHEDULER] Supabase not configured, cannot update run status")
        return
    
    try:
        now_utc = datetime.now(timezone.utc)
        
        supabase_client.table("new_drops_pipeline_control").update({
            "python_ready": True,
            "python_completed_at": now_utc.isoformat()
        }).eq("id", "new_drops").execute()
        
        logger.info(f"[SCHEDULER] Updated Supabase: python_ready=true, python_completed_at={now_utc.isoformat()}")
    except Exception as e:
        logger.error(f"[SCHEDULER] Error updating Supabase: {e}")


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
        # Only update Supabase after successful completion
        logger.info("\n[SCHEDULER] Scraping completed successfully, updating Supabase...")
        update_last_run()
    
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        # Send ClickUp alert for pipeline crash
        send_pipeline_crash_alert(str(e))
        # Also send error summary if we have partial errors
        if run_errors["total_errors"] > 0:
            send_end_of_run_summary_alert(run_errors)
        # NOTE: Do NOT update Supabase on failure - script will retry on next scheduled run
        logger.warning("[SCHEDULER] Scraping failed - NOT updating Supabase for retry on next run")
        raise


if __name__ == "__main__":
    main()