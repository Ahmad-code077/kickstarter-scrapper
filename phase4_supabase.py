# phase4_supabase.py - Phase 4: Store to Supabase

from datetime import datetime

from config import logger, supabase_client


# =========================
# PHASE 4: STORE TO SUPABASE
# =========================

def upsert_to_supabase(projects):
    """Phase 4: Upsert projects to Supabase"""
    logger.info("\n📍 PHASE 4: STORE TO SUPABASE")
    logger.info("-" * 80)
    
    if not supabase_client:
        logger.warning("⚠️  Supabase not configured, skipping database storage")
        return
    
    for idx, project in enumerate(projects, 1):
        try:
            project_id = project.get("project_id")
            logger.info(f"[{idx}/{len(projects)}] Upserting project {project_id}...")
            
            # Upsert with project_id as unique key
            response = supabase_client.table("kickstarter_projects").upsert(
                {
                    **project,
                    "updated_at": datetime.utcnow().isoformat()
                },
                on_conflict="project_id"
            ).execute()
            
            logger.info(f"    ✅ Upserted")
        
        except Exception as e:
            logger.error(f"    ❌ Error: {e}")
    
    logger.info(f"✅ Supabase storage complete")
