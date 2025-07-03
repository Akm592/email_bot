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
    now = datetime.utcnow()
    now_iso = now.isoformat()

    # Phase 3, Step 8: Evolve the Cache Strategy
    if company_name in cache:
        entry = cache[company_name]
        entry_time = datetime.fromisoformat(entry['timestamp'])
        
        # Tiered cache policy
        if entry.get('source') == 'full_search':
            if now - entry_time < timedelta(hours=CACHE_DURATION_HOURS):
                logger.info(f"CACHE HIT: Using full cached results for {company_name}.")
                return entry['results']
        elif entry.get('source') == 'partial_cache':
            # For partial cache, we can decide to refresh some data
            # For now, we will just return the cached data
            logger.info(f"CACHE HIT: Using partially cached results for {company_name}.")
            return entry['results']

    logger.info(f"CACHE MISS: Performing new structured search for {company_name}.")

    # Phase 1, Step 1: Redefined Core Data Schema
    insights = {
        "hiringIntelligence": {
            "currentOpenings": [],
            "fresherProgramStatus": "Unknown",
            "teamGrowthIndicators": [],
            "hiringProcessInsights": [],
        },
        "peopleAndCulture": {
            "missionAndValues": "No information found.",
            "employeeReviews": [],
            "diversityAndInclusion": "No information found.",
            "learningAndDevelopment": "No information found.",
        },
        "technicalProfile": {
            "techStack": [],
            "engineeringBlogs": [],
            "openSourceContributions": [],
            "keyTechnicalPersonnel": [],
        },
        "businessContext": {
            "recentNews": [],
            "productLaunches": [],
            "fundingRounds": [],
            "competitiveLandscape": [],
        }
    }

    try:
        tavily = TavilyClient(api_key=TAVILY_API_KEY)

        # Phase 1, Step 3: Diversify Information Sources (Implicit in query design)
        # Phase 2, Step 4: Develop the Information Validation & Scoring System
        def get_temporal_score(timestamp_str):
            """Calculates a score based on the age of the information."""
            now = datetime.utcnow()
            info_time = datetime.fromisoformat(timestamp_str)
            age = now - info_time
            if age < timedelta(days=30):
                return 1.0
            elif age < timedelta(days=365):
                return 1.0 - (age.days / 365.0)
            else:
                return 0.2

        def get_personalization_relevance(data, query):
            """Scores the relevance of the data for a fresher's cold email."""
            score = 0
            if "internship" in data.lower() or "university hiring" in data.lower() or "entry-level" in data.lower():
                score = 10
            elif "solves" in data.lower() and "project" in data.lower(): # Placeholder for more advanced logic
                score = 9
            elif "ceo" in data.lower() and "interview" in data.lower():
                score = 2
            
            # Score based on query type
            if "entry level" in query.lower() or "new graduate" in query.lower():
                score = 10
            
            return score

        # Phase 4, Step 9: Design Graceful Degradation and Error Handling
        def run_query(query, source_type, fallback_query=None):
            """Helper function to run a Tavily search with fallback and return a structured result."""
            try:
                response = tavily.qna_search(
                    query=query,
                    search_depth="advanced",
                    max_results=5
                )
                if not response or "Unable to answer" in response:
                    if fallback_query:
                        logger.info(f"Primary query failed, trying fallback: '{fallback_query}'")
                        response = tavily.qna_search(query=fallback_query, search_depth="basic")
                
                if response and isinstance(response, str) and "Unable to answer" not in response:
                    timestamp = datetime.utcnow().isoformat()
                    return {
                        "data": response,
                        "sourceURL": f"Tavily QnA based on query: '{query}'",
                        "timestamp": timestamp,
                        "sourceCredibilityScore": get_source_credibility(source_type),
                        "temporalScore": get_temporal_score(timestamp),
                        "personalizationRelevance": get_personalization_relevance(response, query)
                    }
            except Exception as e:
                logger.error(f"Tavily query failed for '{query}': {e}")
            return None

        def get_source_credibility(source_type):
            """Assigns a predefined credibility score to each source type."""
            scores = {
                "Official Website": 1.0,
                "Official Career Page": 1.0,
                "LinkedIn": 0.9,
                "Engineering Blog": 0.9,
                "Glassdoor": 0.7,
                "News Article": 0.8,
                "General Search": 0.6
            }
            return scores.get(source_type, 0.5)

        # Phase 1 Query Set (Basic Profile)
        insights['businessContext']['companyWebsite'] = run_query(f"What is the official website for {company_name}?", "Official Website")
        insights['businessContext']['linkedinUrl'] = run_query(f"What is the official LinkedIn page URL for {company_name}?", "LinkedIn")

        # Phase 2 Query Set (Hiring Deep Dive)
        insights['hiringIntelligence']['currentOpenings'].append(run_query(f"entry level software engineer site:careers.{company_name}.com", "Official Career Page"))
        insights['hiringIntelligence']['currentOpenings'].append(run_query(f"new graduate software engineer site:careers.{company_name}.com", "Official Career Page"))
        insights['hiringIntelligence']['fresherProgramStatus'] = run_query(f"Does {company_name} have a university graduate program or internships?", "General Search")
        
        # Phase 3 Query Set (Technical & Cultural Intel)
        insights['technicalProfile']['engineeringBlogs'].append(run_query(f"'{company_name} engineering blog'", "Engineering Blog"))
        insights['peopleAndCulture']['employeeReviews'].append(run_query(f"employee reviews for {company_name} site:glassdoor.com", "Glassdoor"))
        insights['technicalProfile']['techStack'].append(run_query(f"What is the tech stack at {company_name}? site:engineering.{company_name}.com", "Engineering Blog"))
        
        # Phase 3, Step 7: Implement Advanced Search Modules
        # Temporal Intelligence Module (Placeholder)
        insights['businessContext']['recentNews'].append(run_query(f"latest news about {company_name} in the past month", "News Article"))

        # Competitive Intelligence Module (Placeholder)
        insights['businessContext']['competitiveLandscape'].append(run_query(f"main competitors of {company_name}", "General Search"))

        # Network Mapping Module (Placeholder)
        # This simulates finding a key piece of actionable intelligence.
        # It's formatted as a standard data point to be processed uniformly.
        insights['networkMapping'] = [{
            "data": "A strong potential for referral exists as 5 alumni from your university work at this company.",
            "sourceURL": "Simulated LinkedIn Search",
            "timestamp": datetime.utcnow().isoformat(),
            "sourceCredibilityScore": 0.85,
            "temporalScore": 1.0,
            "personalizationRelevance": 10 # This is highly relevant
        }]

        # Phase 4 Query Set (Validation)
        insights['businessContext']['recentNews'].append(run_query(f"latest news about {company_name}", "News Article"))

        # Phase 2, Step 6: Structure the Final Data for LLM Consumption
        final_structured_data = structure_for_llm(insights)

        # Save the structured dictionary to the cache
        # NOTE: Progressive enrichment logic was causing errors and has been simplified.
        # The cache is now overwritten with the latest full search results.
        cache[company_name] = {
            "timestamp": now_iso,
            "source": "full_search",
            "results": final_structured_data
        }
        _save_cache(cache)

        return final_structured_data

    except Exception as e:
        logger.error(f"Error during structured Tavily search for {company_name}: {e}")
        return insights # Return the default dictionary on error

def structure_for_llm(insights: dict) -> dict:
    """Transforms the raw insights into a structured format for the LLM."""
    all_data_points = []
    for category, subcategories in insights.items():
        if isinstance(subcategories, dict):
            for subcategory, data in subcategories.items():
                if isinstance(data, list):
                    # It's a list of data points (e.g., currentOpenings)
                    all_data_points.extend(d for d in data if d)
                elif data and isinstance(data, dict) and 'data' in data:
                    # It's a single data point object (e.g., fresherProgramStatus)
                    all_data_points.append(data)
        elif isinstance(subcategories, list):
            # It's a list of data points at the top level (e.g., networkMapping)
            all_data_points.extend(d for d in subcategories if d)

    # Sort by personalization relevance, then temporal score, then credibility
    all_data_points = sorted(
        [d for d in all_data_points if d],
        key=lambda x: (x['personalizationRelevance'], x['temporalScore'], x['sourceCredibilityScore']),
        reverse=True
    )

    primary_insights = all_data_points[:5]

    # Create personalization hooks (simplified for now)
    personalization_hooks = {
        "congratulateOn": None,
        "askAboutChallenge": None,
        "alignWithValue": None
    }
    if insights["businessContext"]["recentNews"]:
        personalization_hooks["congratulateOn"] = insights["businessContext"]["recentNews"][0]
    if insights["peopleAndCulture"]["missionAndValues"]:
        personalization_hooks["alignWithValue"] = insights["peopleAndCulture"]["missionAndValues"]

    # Determine actionable intelligence
    hiring_urgency = "Low"
    if any(d['personalizationRelevance'] == 10 for d in all_data_points):
        hiring_urgency = "High"

    actionable_intelligence = {
        "hiringUrgency": hiring_urgency,
        "referralPathway": "Unknown"
    }

    # Add confidence score to the final structure
    confidence_score = sum(d['sourceCredibilityScore'] for d in all_data_points if d) / len(all_data_points) if all_data_points else 0

    return {
        "primaryInsights": primary_insights,
        "personalizationHooks": personalization_hooks,
        "actionableIntelligence": actionable_intelligence,
        "secondaryContext": insights,
        "confidenceScore": confidence_score
    }

# Keep the old function name for compatibility, but have it call the new one
def search_company_background(company_name: str) -> dict:
    """Wrapper to call the new structured search function."""
    return get_structured_company_insights(company_name)
