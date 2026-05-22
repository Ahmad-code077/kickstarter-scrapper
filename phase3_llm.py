# phase3_llm.py - Phase 3: LLM Scoring with OpenAI

import json
import time
import openai

from config import logger, OPENAI_API_KEY

# Set OpenAI API key
if OPENAI_API_KEY:
    openai.api_key = OPENAI_API_KEY


# =========================
# PHASE 3: LLM SCORING
# =========================

def score_with_openai(project, voice_guidelines):
    """Phase 3: Score a project using OpenAI with ClickUp voice guidelines"""
    
    if not OPENAI_API_KEY:
        logger.warning("⚠️  OpenAI API key not set, skipping LLM scoring")
        return None
    
    try:
        prompt = f"""You are a product expert evaluating Kickstarter projects for a nomadic lifestyle brand.

VOICE & SCORING GUIDELINES:
{voice_guidelines}

PROJECT DATA:
{json.dumps(project, indent=2)}

Based on the guidelines above, evaluate this project. Return a JSON object with:
- score (0-100)
- fit_rating (excellent/good/fair/poor)
- key_strengths (array of strings)
- concerns (array of strings)
- recommendation (string: why nomads would/wouldn't like it)

Return ONLY valid JSON, no markdown, no extra text."""

        logger.debug(f"[LLM] Scoring project {project.get('project_id')}")
        
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a JSON API. Return only valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            timeout=30
        )
        
        result_text = response["choices"][0]["message"]["content"].strip()
        result = json.loads(result_text)
        
        logger.info(f"    ✅ Scored: {result.get('fit_rating', 'N/A')} ({result.get('score', 0)}/100)")
        
        return result
    
    except Exception as e:
        logger.error(f"    ❌ LLM error: {e}")
        return None


def phase_3_llm_scoring(all_projects, voice_guidelines):
    """Phase 3: Score all projects with OpenAI"""
    logger.info("\n📍 PHASE 3: LLM SCORING")
    logger.info("-" * 80)
    
    if not voice_guidelines:
        logger.warning("⚠️  No voice guidelines, skipping LLM scoring")
        return all_projects
    


    
    for idx, project in enumerate(all_projects, 1):
        logger.info(f"[{idx}/{len(all_projects)}] {project.get('project_name')[:50]}...")
        
        llm_result = score_with_openai(project, voice_guidelines)
        
        if llm_result:
            # Add LLM results to project
            project["llm_score"] = llm_result.get("score")
            project["llm_fit_rating"] = llm_result.get("fit_rating")
            project["llm_strengths"] = llm_result.get("key_strengths", [])
            project["llm_concerns"] = llm_result.get("concerns", [])
            project["llm_recommendation"] = llm_result.get("recommendation")
        
        time.sleep(0.5)  # Be nice to OpenAI
    
    logger.info(f"✅ LLM scoring complete")
    return all_projects
