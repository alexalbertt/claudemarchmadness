#!/usr/bin/env python3
"""
Data Fetcher Module
------------------
Handles fetching data about basketball teams and matchups.
"""

import os
import asyncio
import aiohttp
import logging
import json
import random
from datetime import datetime

# Set up logger
logger = logging.getLogger('data_fetcher')

def generate_search_queries(team1_name, team2_name, seed1, seed2, region, round_name):
    """
    Generate multiple search queries for a matchup to gather diverse information.
    
    Parameters:
    - team1_name, team2_name: Team names
    - seed1, seed2: Team seeds
    - region: Tournament region
    - round_name: Current round name
    
    Returns:
    - List of search query strings
    """
    # Base query focusing on the matchup
    base_query = f"{team1_name} vs {team2_name} NCAA March Madness basketball 2025 {region} region {round_name}"
    
    # Additional query variations to capture different aspects
    queries = [
        base_query,  # The general matchup
        f"{team1_name} basketball team statistics 2025 analysis strengths weaknesses",  # Team 1 analysis
        f"{team2_name} basketball team statistics 2025 analysis strengths weaknesses",  # Team 2 analysis
        f"{team1_name} vs {team2_name} basketball prediction odds March Madness 2025",  # Predictions
        f"#{seed1} seed vs #{seed2} seed historical NCAA tournament matchup statistics",  # Seed matchup history
    ]
    
    logger.info(f"Generated {len(queries)} search queries for {team1_name} vs {team2_name}")
    return queries

async def search_matchup_multi(team1_name, team2_name, seed1, seed2, region, round_name):
    """
    Perform multiple searches for a matchup using various query strategies.
    
    Parameters:
    - team1_name, team2_name: Team names
    - seed1, seed2: Team seeds
    - region: Tournament region
    - round_name: Current round name
    
    Returns:
    - Dictionary mapping query types to search results
    """
    queries = generate_search_queries(team1_name, team2_name, seed1, seed2, region, round_name)
    
    # Execute all searches in parallel
    search_tasks = []
    for query in queries:
        search_tasks.append(search_with_query(query))
    
    # Wait for all searches to complete
    results = await asyncio.gather(*search_tasks)
    
    # Combine results with query information
    combined_results = {}
    for i, query in enumerate(queries):
        # Create a short name for this query type
        if i == 0:
            query_type = "matchup"
        elif i == 1:
            query_type = f"{team1_name}_analysis"
        elif i == 2:
            query_type = f"{team2_name}_analysis"
        elif i == 3:
            query_type = "predictions"
        elif i == 4:
            query_type = "seed_history"
        else:
            query_type = f"query_{i+1}"
            
        combined_results[query_type] = {
            "query": query,
            "results": results[i]
        }
    
    return combined_results

async def search_with_query(query):
    """
    Execute a single search query using Exa API.
    
    Parameters:
    - query: Search query string
    
    Returns:
    - List of search results
    """
    try:
        # Get API key from environment
        api_key = os.environ.get("EXA_API_KEY")
        if not api_key:
            logger.error("Missing EXA_API_KEY environment variable")
            return []
            
        logger.debug("Using Exa API key: [MASKED]")
        
        # Set up the API request
        url = "https://api.exa.ai/search"
        headers = {
            "x-api-key": api_key,
            "Content-Type": "application/json"
        }
        data = {"query": query}
        
        # Make the request
        timeout = aiohttp.ClientTimeout(total=30)  # 30 second timeout
        async with aiohttp.ClientSession(timeout=timeout) as session:
            logger.debug(f"Sending request to Exa API: {url}")
            logger.debug(f"Query: {query}")
            
            async with session.post(url, headers=headers, json=data) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"Exa API error: Status {response.status}, Response: {error_text}")
                    return []
                
                # Parse the response
                response_text = await response.text()
                search_results = json.loads(response_text)
                
                # Format results to match our expected structure
                formatted_results = []
                
                # If the API response structure changes, adjust parsing here
                if 'results' in search_results:
                    for result in search_results['results']:
                        formatted_result = {
                            'url': result.get('url', ''),
                            'title': result.get('title', ''),
                            'publishedDate': result.get('publishedDate', ''),
                            'snippet': result.get('snippet', '')
                        }
                        formatted_results.append(formatted_result)
                
                # Log results for debugging
                logger.debug(f"Found {len(formatted_results)} search results for query: {query[:50]}...")
                
                # Return top 3 most recent results for each query to avoid overwhelming Claude
                sorted_results = sorted(
                    formatted_results,
                    key=lambda x: x.get("publishedDate", ""),
                    reverse=True
                )
                
                return sorted_results[:3]
                
    except Exception as e:
        logger.error(f"Error in Exa search: {str(e)}", exc_info=True)
        # Return empty list on error
        return []

async def search_matchup(team1_name, team2_name, seed1, seed2, region, round_name):
    """
    Legacy method for compatibility - uses the multi-search approach but returns flattened results.
    
    Parameters:
    - team1_name, team2_name: Team names
    - seed1, seed2: Team seeds
    - region: Tournament region
    - round_name: Current round name
    
    Returns:
    - List of search results (URLs and metadata)
    """
    multi_results = await search_matchup_multi(team1_name, team2_name, seed1, seed2, region, round_name)
    
    # Flatten results from all queries
    flattened_results = []
    for query_type, data in multi_results.items():
        flattened_results.extend(data["results"])
    
    # Deduplicate by URL
    unique_urls = set()
    unique_results = []
    
    for result in flattened_results:
        url = result.get('url', '')
        if url and url not in unique_urls:
            unique_urls.add(url)
            unique_results.append(result)
    
    # Return top 5 most recent results
    sorted_results = sorted(
        unique_results,
        key=lambda x: x.get("publishedDate", ""),
        reverse=True
    )
    
    return sorted_results[:5]

async def fetch_content(url):
    """
    Fetch and extract content from a URL.
    
    Parameters:
    - url: URL to fetch
    
    Returns:
    - Extracted and processed content
    """
    max_content_length = 8000  # Characters per source
    
    logger.debug(f"Fetching content from URL: {url}")
    
    try:
        timeout = aiohttp.ClientTimeout(total=30)  # 30 second timeout
        
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url) as response:
                if response.status != 200:
                    error_msg = f"Error: Could not fetch content (Status code: {response.status})"
                    logger.error(error_msg)
                    return error_msg
                
                logger.debug(f"Successfully fetched URL (status code: {response.status})")
                html_content = await response.text()
                
                # Simple HTML content extraction
                # In a production system, use a proper HTML parsing library like BeautifulSoup
                # or a readability library like newspaper3k or trafilatura
                
                import re
                
                # Remove script and style tags and their contents
                html_content = re.sub(r'<script[^>]*>.*?</script>', '', html_content, flags=re.DOTALL)
                html_content = re.sub(r'<style[^>]*>.*?</style>', '', html_content, flags=re.DOTALL)
                
                # Remove all HTML tags
                text_content = re.sub(r'<[^>]*>', ' ', html_content)
                
                # Replace multiple whitespace with single space
                text_content = re.sub(r'\s+', ' ', text_content).strip()
                
                content_length = len(text_content)
                logger.debug(f"Extracted text content: {content_length} characters")
                
                # Truncate content if too long, prioritizing beginning and end
                if content_length > max_content_length:
                    # Keep first 60% and last 40% of max length
                    first_part_length = int(max_content_length * 0.6)
                    last_part_length = max_content_length - first_part_length
                    first_part = text_content[:first_part_length]
                    last_part = text_content[-last_part_length:]
                    text_content = first_part + "\n...[content truncated]...\n" + last_part
                    logger.debug(f"Content truncated: {content_length} -> {len(text_content)} characters")
                
                return text_content
    except aiohttp.ClientError as e:
        error_msg = f"Error fetching URL: {str(e)}"
        logger.error(error_msg)
        return error_msg
    except Exception as e:
        error_msg = f"Unexpected error processing URL: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return error_msg

async def fetch_and_analyze_sources(multi_results, anthropic_client, model_name):
    """
    Fetch and analyze sources from multiple search queries.
    
    Parameters:
    - multi_results: Dictionary of search results by query type
    - anthropic_client: Initialized Anthropic client
    - model_name: Claude model to use
    
    Returns:
    - Dictionary of analysis results by query type
    """
    analysis_results = {}
    
    # Process each query type
    for query_type, data in multi_results.items():
        query = data["query"]
        results = data["results"]
        
        if not results:
            logger.warning(f"No results for query type: {query_type}")
            analysis_results[query_type] = {
                "summary": f"No data found for {query_type}.",
                "sources": []
            }
            continue
        
        # Fetch content for each result
        sources = []
        for result in results:
            url = result.get('url')
            if url:
                try:
                    content = await fetch_content(url)
                    sources.append({
                        "url": url,
                        "title": result.get('title', ''),
                        "content": content
                    })
                except Exception as e:
                    logger.error(f"Error fetching content for {url}: {str(e)}")
        
        # Analyze sources for this query type
        if sources:
            summary = await analyze_sources_for_query(query_type, query, sources, anthropic_client, model_name)
            analysis_results[query_type] = {
                "summary": summary,
                "sources": [s["url"] for s in sources]
            }
        else:
            analysis_results[query_type] = {
                "summary": f"Could not retrieve any content for {query_type}.",
                "sources": []
            }
    
    return analysis_results

async def analyze_sources_for_query(query_type, query, sources, anthropic_client, model_name):
    """
    Use Claude to analyze sources for a specific query type.
    
    Parameters:
    - query_type: Type of query (matchup, team analysis, etc.)
    - query: The search query used
    - sources: List of source dictionaries with url, title, and content
    - anthropic_client: Initialized Anthropic client
    - model_name: Claude model to use
    
    Returns:
    - Summary of the analysis
    """
    logger.info(f"Analyzing {len(sources)} sources for query type: {query_type}")
    
    # Prepare system prompt based on query type
    if query_type == "matchup":
        system_prompt = """You are a basketball analysis expert. Analyze the provided information about this matchup and extract key insights. Focus on relevant factors that would influence the outcome of this game."""
    elif query_type.endswith("_analysis"):
        team_name = query_type.replace("_analysis", "")
        system_prompt = f"""You are a basketball analysis expert. Analyze the provided information about {team_name} and extract key insights about their strengths, weaknesses, recent performance, key players, and other relevant factors."""
    elif query_type == "predictions":
        system_prompt = """You are a basketball analysis expert. Analyze the provided information about predictions and betting odds for this matchup. Summarize expert predictions and identify consensus views if they exist."""
    elif query_type == "seed_history":
        system_prompt = """You are a basketball analysis expert. Analyze the historical data about NCAA tournament matchups between these seed numbers. Identify patterns and historical precedents that might inform predictions."""
    else:
        system_prompt = """You are a basketball analysis expert. Analyze the provided information and extract key insights relevant to predicting the outcome of this matchup."""
    
    # Initialize conversation
    messages = []
    
    # Create initial user message
    user_message = {
        "role": "user",
        "content": [
            {
                "type": "text",
                "text": f"I'm researching the following: {query}\n\nI'll share information from several sources. Please analyze this information and provide a concise summary of the key insights."
            }
        ]
    }
    
    messages.append(user_message)
    
    # Process each source
    for idx, source in enumerate(sources):
        source_text = f"Source {idx+1}: {source['url']}\nTitle: {source['title']}\n\n{source['content']}"
        
        assistant_message = {
            "role": "assistant",
            "content": [
                {
                    "type": "text",
                    "text": f"I'll analyze source {idx+1}."
                }
            ]
        }
        
        user_message = {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": source_text
                }
            ]
        }
        
        messages.append(assistant_message)
        messages.append(user_message)
    
    # Final prompt for summary
    assistant_message = {
        "role": "assistant",
        "content": [
            {
                "type": "text",
                "text": "I've reviewed all the sources. I'll now provide a concise summary of the key insights."
            }
        ]
    }
    
    user_message = {
        "role": "user",
        "content": [
            {
                "type": "text",
                "text": """Based on all the information I've shared, please provide a concise summary (250-300 words) of the key insights. 
                
Focus on information that would be most valuable for predicting the outcome of this matchup. If the sources contain conflicting information, please note this in your summary.

Your summary should be factual and analytical, avoiding subjective judgments unless they are explicitly supported by the sources."""
            }
        ]
    }
    
    messages.append(assistant_message)
    messages.append(user_message)
    
    # Get summary from Claude
    try:
        response = anthropic_client.messages.create(
            model=model_name,
            max_tokens=1000,
            messages=messages,
            system=system_prompt
        )
        
        summary = response.content[0].text
        logger.debug(f"Generated summary for {query_type} ({len(summary)} chars)")
        return summary
        
    except Exception as e:
        logger.error(f"Error getting analysis from Claude: {str(e)}")
        return f"Error analyzing sources: {str(e)}"

async def fetch_team_stats(team_name):
    """
    Fetch statistics for a specific team.
    
    Parameters:
    - team_name: Name of the team
    
    Returns:
    - Dictionary of team statistics
    """
    # This would normally call a sports stats API
    # For this implementation, we'll return mock data
    logger.debug(f"Generating mock stats for {team_name}")
    
    # Simulate API call delay
    await asyncio.sleep(0.5)
    
    # Generate a consistent hash value for the team name
    def team_hash(name):
        return sum(ord(c) for c in name) % 100
    
    # Mock stats - in a real implementation, this would come from an API
    team_hash_value = team_hash(team_name)
    mock_stats = {
        "team_name": team_name,
        "stats": {
            "points_per_game": round(70 + team_hash_value % 20, 1),
            "rebounds_per_game": round(30 + team_hash_value % 15, 1),
            "assists_per_game": round(10 + team_hash_value % 10, 1),
            "field_goal_percentage": round(40 + team_hash_value % 10, 1),
            "three_point_percentage": round(30 + team_hash_value % 10, 1),
            "free_throw_percentage": round(65 + team_hash_value % 20, 1),
            "turnover_margin": round(-3 + team_hash_value % 6, 1),
        }
    }
    
    logger.debug(f"Mock stats for {team_name}: {mock_stats}")
    return mock_stats