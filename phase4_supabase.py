# phase4_supabase.py - Phase 4: Store to Supabase

from datetime import datetime

from config import logger, supabase_client


# =========================
# PHASE 4: STORE TO SUPABASE
# =========================

def map_project_to_review_table(project):
    """Map full project data to kickstarter_review table fields only"""
    
    return {
        "project_name": project.get("project_name"),
        "blurb": project.get("blurb"),
        "percent_funded": project.get("percent_funded"),
        "backers_count": project.get("backers_count"),
        "staff_pick": project.get("staff_pick"),
        "creator_name": project.get("creator_name"),
        "creator_past_campaigns": project.get("creator_past_campaigns"),
        "comments_count": project.get("comments_count"),
        "launched_at": project.get("launched_at"),
        "deadline": project.get("deadline"),
        "country": project.get("country"),
        "relevance_score": project.get("relevance_score"),
        "score_reason": project.get("score_reason"),
        "product_summary": project.get("product_summary"),
        "key_features": project.get("key_features", []),
        "concerns": project.get("concerns", []),
        "main_image": project.get("main_image"),
        "project_url": project.get("project_url"),
        "created_at": datetime.utcnow().isoformat()
    }


def upsert_to_supabase(projects):
    """Phase 4: Upsert projects to Supabase kickstarter_review table"""
    logger.info("\n📍 PHASE 4: STORE TO SUPABASE")
    logger.info("-" * 80)
    
    if not supabase_client:
        logger.warning("⚠️  Supabase not configured, skipping database storage")
        return
    
    for idx, project in enumerate(projects, 1):
        try:
            project_url = project.get("project_url")
            logger.info(f"[{idx}/{len(projects)}] Processing {project.get('project_name')[:40]}...")
            
            # Map only required fields for review table
            review_data = map_project_to_review_table(project)
            
            # Upsert with project_url as unique key
            response = supabase_client.table("kickstarter_review").upsert(
                review_data,
                on_conflict="project_url"
            ).execute()
            
            logger.info(f"    ✅ Stored (score: {project.get('relevance_score', 'N/A')})")
        
        except Exception as e:
            logger.error(f"    ❌ Error: {e}")
    
    logger.info(f"✅ Supabase storage complete")