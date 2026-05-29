# phase1_merge_clean.py - Phase 1c (Merge & Clean)

from html.parser import HTMLParser
import re
import time

from config import logger
from phase1_search_fetch import fetch_graphql_with_retry


# ==================== HTML CLEANING ====================

class HTMLStripper(HTMLParser):
    """Strip HTML tags"""
    def __init__(self):
        super().__init__()
        self.reset()
        self.fed = []

    def handle_data(self, d):
        self.fed.append(d)

    def get_data(self):
        return ''.join(self.fed)


def strip_html_tags(html_text):
    """Remove all HTML tags"""
    if not html_text:
        return ""
    try:
        stripper = HTMLStripper()
        stripper.feed(html_text)
        return stripper.get_data()
    except Exception as e:
        logger.debug(f"[HTML_STRIP] Error: {e}")
        return html_text


def clean_story_field(story_html):
    """Clean story: remove HTML, images, scripts, excessive whitespace"""
    if not story_html:
        return ""
    
    story = re.sub(r'<script[^>]*>.*?</script>', '', story_html, flags=re.DOTALL | re.IGNORECASE)
    story = re.sub(r'<style[^>]*>.*?</style>', '', story, flags=re.DOTALL | re.IGNORECASE)
    story = re.sub(r'<img[^>]*>', '', story, flags=re.IGNORECASE)
    story = re.sub(r'src=["\']([^"\']*)["\']', '', story, flags=re.IGNORECASE)
    story = strip_html_tags(story)
    story = re.sub(r'\s+', ' ', story).strip()
    
    return story


# ==================== MERGE & FLATTEN ====================

def merge_and_flatten(discovery, graphql_data):
    """Merge discovery + GraphQL, flatten all nested structures"""
    if graphql_data is None:
        logger.error(f"[MERGE_ERROR] graphql_data is None for {discovery.get('project_name')}")
        return None
    
    if not isinstance(graphql_data, dict):
        logger.error(f"[MERGE_ERROR] graphql_data is not dict, got {type(graphql_data)}: {graphql_data}")
        return None
    
    project = graphql_data.get("data", {}).get("project", {})
    
    if not project:
        return None
    
    creator = project.get("creator", {})
    comments = project.get("comments", {})
    env_commitments = project.get("environmentalCommitments", [])
    
    story_raw = project.get("story", "")
    story_clean = clean_story_field(story_raw)
    
    env_commitments_text = " | ".join([
        f"{c.get('commitmentCategory', '')}: {c.get('description', '')}"
        for c in env_commitments if c.get('description')
    ]) if env_commitments else ""
    
    merged = {
        "project_id": discovery.get("project_id"),
        "project_name": discovery.get("project_name"),
        "blurb": discovery.get("blurb"),
        "goal": discovery.get("goal"),
        "pledged": discovery.get("pledged"),
        "usd_pledged": discovery.get("usd_pledged"),
        "backers_count": discovery.get("backers_count"),
        "percent_funded": discovery.get("percent_funded"),
        "state": discovery.get("state"),
        "deadline": discovery.get("deadline"),
        "launched_at": discovery.get("launched_at"),
        "staff_pick": discovery.get("staff_pick"),
        "country": discovery.get("country"),
        "currency": discovery.get("currency"),
        "main_image": discovery.get("main_image"),
        "project_url": discovery.get("project_url"),
        "slug": discovery.get("slug"),
        "creator_name": discovery.get("creator_name"),
        "location": discovery.get("location"),
        
        # GraphQL fields (only missing ones - NO DUPLICATES)
        "creator_id": creator.get("id"),
        "creator_url": creator.get("url", ""),
        "creator_location": creator.get("location", {}).get("displayableName", ""),
        "creator_past_campaigns": creator.get("launchedProjects", {}).get("totalCount", 0),        
        "story_clean": story_clean,
        "risks": project.get("risks", ""),
        "environmental_commitments": env_commitments_text,
        "comments_count": comments.get("totalCount", 0),
    }
    
    return merged


def phase_1_search_fetch_merge_clean(discovered_projects, session=None):
    """Phase 1b & 1c: Fetch details and merge for all projects
    
    Args:
        discovered_projects: List of projects from search phase
        session: Optional curl_cffi Session to reuse warmed Kickstarter session
    """
    logger.info("\n📍 PHASE 1b & 1c: FETCH GRAPHQL & MERGE & CLEAN")
    logger.info("-" * 80)
    
    all_merged = []
    failed = []
    
    for idx, project in enumerate(discovered_projects, 1):
        project_id = project.get("project_id")
        slug = project.get("slug")
        
        logger.info(f"[{idx}/{len(discovered_projects)}] {project.get('project_name')[:50]}...")
        
        try:
            graphql_response = fetch_graphql_with_retry(slug, session=session)
            
            logger.debug(f"[MERGE_DEBUG] graphql_response type: {type(graphql_response)}, value: {graphql_response}")
            
            if graphql_response:
                merged = merge_and_flatten(project, graphql_response)
                if merged:
                    all_merged.append(merged)
                    logger.info(f"    ✅ Merged & Cleaned")
                else:
                    logger.warning(f"    ⚠️  Merge failed")
                    failed.append(project_id)
            else:
                logger.warning(f"    ⚠️  GraphQL fetch failed (returned None)")
                failed.append(project_id)
        
        except Exception as e:
            logger.error(f"    ❌ Error: {e}")
            import traceback
            logger.error(f"[MERGE_EXCEPTION] Traceback: {traceback.format_exc()}")
            failed.append(project_id)
        
        time.sleep(1)
    
    logger.info(f"\n✅ Fetch & Merge complete: {len(all_merged)} projects merged, {len(failed)} failed")
    return all_merged
