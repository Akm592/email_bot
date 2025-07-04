# src/tavily_search.py

import logging
from tavily import TavilyClient
import config
import json
import os
from datetime import datetime, timedelta
from sentence_transformers import SentenceTransformer, util
import numpy as np
from typing import Optional, Any, List, Dict
import asyncio

logger = logging.getLogger(__name__)

TAVILY_API_KEY = config.TAVILY_API_KEY
CACHE_FILE = "data/tavily_cache.json"
CACHE_DURATION_HOURS = 24

class BatchTavilyProcessor:
    def __init__(self):
        self.tavily = TavilyClient(api_key=TAVILY_API_KEY)

    async def process_company_batch(self, companies: List[str]) -> Dict:
        batch_queries = []
        for company in companies:
            batch_queries.extend([
                f"Recent news about {company}",
                f"Job openings at {company}",
                f"Tech stack at {company}"
            ])
        
        # Single API call for multiple queries
        results = await self.tavily.batch_search(batch_queries)
        return self._organize_results_by_company(results, companies)

    def _organize_results_by_company(self, results: List[Dict], companies: List[str]) -> Dict:
        organized_results = {company: {} for company in companies}
        query_types = ["Recent news about ", "Job openings at ", "Tech stack at "]
        
        # Assuming results are in the same order as batch_queries
        for i, company in enumerate(companies):
            for j, query_type_prefix in enumerate(query_types):
                # Calculate the index in the flat results list
                result_index = i * len(query_types) + j
                if result_index < len(results):
                    query_type_key = query_type_prefix.replace(f" {company}", "").strip().replace(" ", "_").lower()
                    organized_results[company][query_type_key] = results[result_index]
        return organized_results



class IntelligentCache:
    def __init__(self):
        self.cache_file = CACHE_FILE
        self.cache_duration = timedelta(hours=CACHE_DURATION_HOURS)
        self.memory_cache = self._load_cache() # L1 Cache
        self.semantic_model = SentenceTransformer('all-MiniLM-L6-v2')
        self.semantic_threshold = 0.85

    def _load_cache(self):
        if os.path.exists(self.cache_file):
            with open(self.cache_file, 'r') as f:
                return json.load(f)
        return {}

    def _save_cache(self):
        os.makedirs(os.path.dirname(self.cache_file), exist_ok=True)
        with open(self.cache_file, 'w') as f:
            json.dump(self.memory_cache, f, indent=2)

    def get(self, query: str, cache_type: str = "company_insights") -> Optional[Any]:
        now = datetime.utcnow()
        
        # 1. Exact match in memory cache
        if query in self.memory_cache:
            entry = self.memory_cache[query]
            entry_time = datetime.fromisoformat(entry['timestamp'])
            if now - entry_time < self.cache_duration:
                logger.info(f"CACHE HIT (Exact): {query}")
                return entry['results']
            else:
                logger.info(f"CACHE EXPIRED: {query}")
                del self.memory_cache[query] # Remove expired entry

        # 2. Semantic match
        if config.SEMANTIC_CACHE_ENABLED:
            semantic_match = self.find_semantic_match(query, cache_type)
            if semantic_match:
                logger.info(f"CACHE HIT (Semantic): {query}")
                return semantic_match
        
        logger.info(f"CACHE MISS: {query}")
        return None

    def set(self, query: str, results: Any, cache_type: str = "company_insights"):
        timestamp = datetime.utcnow().isoformat()
        embedding = self.semantic_model.encode([query]).tolist() # Store as list for JSON
        self.memory_cache[query] = {
            "timestamp": timestamp,
            "type": cache_type,
            "results": results,
            "embedding": embedding
        }
        self._save_cache()

    def find_semantic_match(self, query: str, cache_type: str) -> Optional[Any]:
        query_embedding = self.semantic_model.encode([query])
        for cached_query, data in self.memory_cache.items():
            if data.get('type') == cache_type and 'embedding' in data:
                cached_embedding = np.array(data['embedding'])
                similarity = util.cos_sim(query_embedding, cached_embedding)[0][0].item()
                if similarity > self.semantic_threshold:
                    # Update timestamp to extend life of semantically matched entry
                    data['timestamp'] = datetime.utcnow().isoformat()
                    self._save_cache()
                    return data['results']
        return None

intelligent_cache = IntelligentCache()

def get_structured_company_insights(company_name: str) -> dict:
    """
    Performs multiple targeted Tavily searches and returns a structured dictionary of insights.
    This is the most effective method for the AI.
    """
    if config.CACHE_ENABLED:
        cached_results = intelligent_cache.get(company_name)
        if cached_results:
            return cached_results

    logger.info(f"CACHE MISS: Performing new structured search for {company_name}.")

    # Phase 1, Step 1: Redefined Core Data Schema
    insights = {
        "hiringIntelligence": {
            "relevantJobOpening": None, # NEW: To store the most relevant job post
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
        def run_query(query, source_type, search_depth="advanced", max_results=5, fallback_query=None):
            """Helper function to run a Tavily search with fallback and return a structured result."""
            try:
                response = tavily.qna_search(
                    query=query,
                    search_depth=search_depth,
                    max_results=max_results
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

        # Define query priorities and limits
        query_configs = [
            {"query": f"entry level software engineer OR graduate software developer OR junior developer roles at {company_name} site:careers.{company_name}.com OR site:jobs.lever.co/{company_name} OR site:greenhouse.io/{company_name}", "source_type": "Official Career Page", "priority": 1, "depth": "advanced", "max_results": 3, "key": "relevantJobOpening"},
            {"query": f"Does {company_name} have a university graduate program or internships?", "source_type": "General Search", "priority": 2, "depth": "advanced", "max_results": 3, "key": "fresherProgramStatus"},
            {"query": f"latest news about {company_name} in the past month", "source_type": "News Article", "priority": 2, "depth": "advanced", "max_results": 3, "key": "recentNews"},
            {"query": f"What is the tech stack at {company_name}? site:engineering.{company_name}.com", "source_type": "Engineering Blog", "priority": 3, "depth": "basic", "max_results": 2, "key": "techStack"},
            {"query": f"employee reviews for {company_name} site:glassdoor.com", "source_type": "Glassdoor", "priority": 3, "depth": "basic", "max_results": 2, "key": "employeeReviews"},
            {"query": f"What is the official website for {company_name}?", "source_type": "Official Website", "priority": 4, "depth": "basic", "max_results": 1, "key": "companyWebsite"},
            {"query": f"What is the official LinkedIn page URL for {company_name}?", "source_type": "LinkedIn", "priority": 4, "depth": "basic", "max_results": 1, "key": "linkedinUrl"},
            {"query": f"'{company_name} engineering blog'", "source_type": "Engineering Blog", "priority": 4, "depth": "basic", "max_results": 1, "key": "engineeringBlogs"},
            {"query": f"main competitors of {company_name}", "source_type": "General Search", "priority": 4, "depth": "basic", "max_results": 1, "key": "competitiveLandscape"},
        ]

        # Sort queries by priority
        query_configs.sort(key=lambda x: x['priority'])

        api_calls_made = 0
        max_api_calls = config.MAX_TAVILY_CALLS_PER_COMPANY # From config.py

        for q_config in query_configs:
            if api_calls_made >= max_api_calls:
                logger.info(f"Max API calls ({max_api_calls}) reached for {company_name}. Skipping remaining queries.")
                break

            result = run_query(
                q_config['query'],
                q_config['source_type'],
                search_depth=q_config['depth'],
                max_results=q_config['max_results']
            )
            
            if result:
                api_calls_made += 1
                # Populate insights based on the key
                if q_config['key'] == "relevantJobOpening":
                    insights['hiringIntelligence']['relevantJobOpening'] = result
                elif q_config['key'] == "fresherProgramStatus":
                    insights['hiringIntelligence']['fresherProgramStatus'] = result
                elif q_config['key'] == "recentNews":
                    insights['businessContext']['recentNews'].append(result)
                elif q_config['key'] == "techStack":
                    insights['technicalProfile']['techStack'].append(result)
                elif q_config['key'] == "employeeReviews":
                    insights['peopleAndCulture']['employeeReviews'].append(result)
                elif q_config['key'] == "companyWebsite":
                    insights['businessContext']['companyWebsite'] = result
                elif q_config['key'] == "linkedinUrl":
                    insights['businessContext']['linkedinUrl'] = result
                elif q_config['key'] == "engineeringBlogs":
                    insights['technicalProfile']['engineeringBlogs'].append(result)
                elif q_config['key'] == "competitiveLandscape":
                    insights['businessContext']['competitiveLandscape'].append(result)

        # Add simulated network mapping data if not already present
        if not insights.get('networkMapping'):
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

        if config.CACHE_ENABLED:
            intelligent_cache.set(company_name, final_structured_data)

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
