# phase3_llm.py - Phase 3: LLM Scoring with OpenAI

import json
import time
from openai import OpenAI


from config import logger, OPENAI_API_KEY

# Initialize client
client = None
if OPENAI_API_KEY:
    client = OpenAI(api_key=OPENAI_API_KEY)


def _prepare_project_input(project):
    """Prepare limited project fields for LLM (no internal analysis)"""
    return {
        "project_name": project.get("project_name"),
        "blurb": project.get("blurb"),
        "story_clean": project.get("story_clean"),
        "percent_funded": project.get("percent_funded"),
        "backers_count": project.get("backers_count"),
        "comments_count": project.get("comments_count"),
        "staff_pick": project.get("staff_pick"),
        "creator_past_campaigns": project.get("creator_past_campaigns"),
    }




def score_with_openai(project_input, brand_voice, extraction_sop):
    """Phase 3: Score a project using OpenAI with ClickUp documents"""
    
    if not client:
        logger.warning("⚠️ OpenAI client not initialized")
        return None
    
    try:
        # SYSTEM message: Rules, SOPs, Voice guidelines
        system_message = f"""You are a product expert evaluating Kickstarter projects for a nomadic lifestyle brand newsletter.

BRAND VOICE GUIDELINES:
{brand_voice}

EXTRACTION & SCORING INSTRUCTIONS:
{extraction_sop}

Follow the instructions above exactly. Return ONLY valid JSON. No markdown, no extra text."""

        # USER message: The actual project data
        user_message = json.dumps(project_input, indent=2)

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_message}
            ],
            temperature=0.7,
            timeout=30
        )
        
        result_text = response.choices[0].message.content.strip()
        result = json.loads(result_text)
        
        return result
    
    except Exception as e:
        logger.error(f"❌ LLM error: {e}")
        return None


def phase_3_llm_scoring(all_projects, brand_voice, extraction_sop):
    """Phase 3: Score all projects with OpenAI"""
    logger.info("\n📍 PHASE 3: LLM SCORING")
    logger.info("-" * 80)
    
    if not brand_voice or not extraction_sop:
        logger.warning("⚠️ Missing ClickUp documents, skipping LLM scoring")
        return all_projects
    
    for idx, project in enumerate(all_projects, 1):
        project_name = project.get('project_name', 'Unknown')[:50]
        logger.info(f"[{idx}/{len(all_projects)}] {project_name}...")
        
        project_input = _prepare_project_input(project)
        llm_result = score_with_openai(project_input, brand_voice, extraction_sop)
        
        if llm_result:
            project.update(llm_result)
            logger.info(f"    ✅ Scored")
        else:
            logger.warning(f"    ⚠️ Failed")
        
        time.sleep(0.5)
    
    logger.info(f"✅ LLM scoring complete")
    return all_projects