# src/tavily_search.py

import logging

from tavily import TavilyClient
import config
import json
import os
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

TAVILY_API_KEY = config.TAVILY_API_KEY
CACHE_FILE = "data/tavily_cache.json"
CACHE_DURATION_HOURS = 24

def _load_cache():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, 'r') as f:
            return json.load(f)
    return {}

def _save_cache(cache):
    os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
    with open(CACHE_FILE, 'w') as f:
        json.dump(cache, f, indent=2)

def get_structured_company_insights(company_name: str) -> dict:
    """
    Performs multiple targeted Tavily searches and returns a structured dictionary of insights.
    This is the most effective method for the AI.
    """
    cache = _load_cache()
    now = datetime.utcnow().isoformat()
    
    if company_name in cache:
        entry = cache[company_name]
        entry_time = datetime.fromisoformat(entry['timestamp'])
        if datetime.utcnow() - entry_time < timedelta(hours=CACHE_DURATION_HOURS):
            logger.info(f"CACHE HIT: Using structured cached results for {company_name}.")
            return entry['results']
            
    logger.info(f"CACHE MISS: Performing new structured search for {company_name}.")
    
    insights = {
        "recent_news": "No information found.",
        "tech_stack": "No information found.",
        "mission_and_values": "No information found."
    }
    
    try:
        tavily = TavilyClient(api_key=TAVILY_API_KEY)
        
        # Define the specific questions we want answers to
        queries = {
            "recent_news": f"What are the latest news, product launches, or funding rounds for {company_name}?",
            "tech_stack": f"What programming languages, frameworks, and cloud technologies does {company_name} use? (e.g., Python, React, AWS)",
            "mission_and_values": f"What is the company mission, vision, or values of {company_name}?"
        }
        
        for key, query in queries.items():
            response = tavily.qna_search(
                query=query,
                search_depth="basic", # qna_search is efficient
                max_results=3
            )
            # qna_search returns a direct answer string
            if response and isinstance(response, str) and "Unable to answer" not in response:
                insights[key] = response
        
        # Save the structured dictionary to the cache
        cache[company_name] = {
            "timestamp": now,
            "results": insights
        }
        _save_cache(cache)
        
        return insights

    except Exception as e:
        logger.error(f"Error during structured Tavily search for {company_name}: {e}")
        return insights # Return the default dictionary on error

# Keep the old function name for compatibility, but have it call the new one
def search_company_background(company_name: str) -> dict:
    """Wrapper to call the new structured search function."""
    return get_structured_company_insights(company_name)
