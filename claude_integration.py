#!/usr/bin/env python3
"""
Claude Integration Module
------------------------
Handles communication with Claude API for predictions.
"""

import re
import asyncio
import logging
from data_fetcher import search_matchup_multi, fetch_and_analyze_sources
from utils import get_round_name, estimate_token_count
from context import get_upset_factors_by_seed_matchup

# Set up logger
logger = logging.getLogger('claude_integration')

async def predict_game(game_data, anthropic_client, model_name="claude-3-7-sonnet-20250219", use_enhanced_analysis=True):
    """
    Process a single game through Claude to get a prediction.
    
    Parameters:
    - game_data: Dictionary with game information
    - anthropic_client: Initialized Anthropic client
    - model_name: Claude model to use
    - use_enhanced_analysis: If True, use the multi-query, multi-analysis approach
    
    Returns:
    - Prediction result (winner, confidence, reasoning)
    """
    # Extract game information
    team1 = game_data["team1"]["name"]
    team2 = game_data["team2"]["name"]
    seed1 = game_data["team1"]["seed"]
    seed2 = game_data["team2"]["seed"]
    region = game_data["region"]
    round_name = get_round_name(game_data["game_id"])
    
    logger.info(f"Starting prediction for {team1} vs {team2} in {region} region ({round_name})")
    
    # Initialize conversation history
    messages = []
    
    # System prompt
    system_prompt = """You are a basketball analysis expert assisting with March Madness predictions for a complete tournament bracket.

You are being asked to predict all games in a March Madness bracket, including first round games and potential matchups in later rounds. Even if a matchup is in a later round (Sweet 16, Elite 8, etc.), you should analyze and predict the outcome directly, based on the information provided.

Analyze the provided information about each matchup carefully to make accurate predictions. Consider:
1. Team performance statistics and trends
2. Key player matchups and injuries
3. Historical tournament performance
4. Coaching experience and strategy
5. Seed matchup history
6. Expert predictions and consensus views

Your goal is to provide an accurate, well-reasoned prediction based on the available data, regardless of which round the game is in.
"""
    
    # Create initial user message with team records
    try:
        from context import get_team_records
        team1_record = get_team_records(team1) or "record not available"
        team2_record = get_team_records(team2) or "record not available"
        
        initial_message = f"""I need you to analyze the March Madness matchup between {team1} (Seed #{seed1}, {team1_record}) and {team2} (Seed #{seed2}, {team2_record}) in the {region} region during the {round_name}.

This is part of a complete bracket prediction, so please analyze this matchup regardless of which tournament round it occurs in. For games beyond the first round, assume both teams have advanced to this point.

I'll provide detailed information about both teams, historical seed matchups, and expert predictions gathered from multiple sources. Based on this comprehensive analysis, I'd like you to predict which team will win."""
    except Exception as e:
        logger.warning(f"Could not add team records: {str(e)}")
        initial_message = f"""I need you to analyze the March Madness matchup between {team1} (Seed #{seed1}) and {team2} (Seed #{seed2}) in the {region} region during the {round_name}.

This is part of a complete bracket prediction, so please analyze this matchup regardless of which tournament round it occurs in. For games beyond the first round, assume both teams have advanced to this point.

I'll provide detailed information about both teams, historical seed matchups, and expert predictions gathered from multiple sources. Based on this comprehensive analysis, I'd like you to predict which team will win."""
    
    # Add historical seed matchup info
    try:
        upset_factors = get_upset_factors_by_seed_matchup(seed1, seed2)
        upset_rate = upset_factors.get("upset_rate", 0)
        
        if seed1 < seed2:
            # Team1 is the better seed
            lower_seed_team = team1
            higher_seed_team = team2
            lower_seed = seed1
            higher_seed = seed2
        else:
            # Team2 is the better seed
            lower_seed_team = team2
            higher_seed_team = team1
            lower_seed = seed2
            higher_seed = seed1
        
        # Add seed matchup historical data
        initial_message += f"\n\nHistorical Note: In March Madness history, #{higher_seed} seeds upset #{lower_seed} seeds approximately {upset_rate:.0%} of the time."
        
    except Exception as e:
        logger.warning(f"Could not add upset factors: {str(e)}")
    
    user_message = {
        "role": "user",
        "content": [
            {
                "type": "text",
                "text": initial_message
            }
        ]
    }
    
    messages.append(user_message)
    
    # If using enhanced analysis, perform multi-query search and analysis
    if use_enhanced_analysis:
        try:
            # Get multiple search results organized by query type
            logger.info("Starting enhanced multi-query analysis")
            multi_results = await search_matchup_multi(team1, team2, seed1, seed2, region, round_name)
            
            # Log the number of results found for each query type
            for query_type, data in multi_results.items():
                result_count = len(data["results"])
                logger.info(f"Found {result_count} results for {query_type}")
                print(f"Found {result_count} results for {query_type} query")
            
            # Fetch and analyze sources for each query type
            logger.info("Analyzing search results using multiple Claude instances")
            analysis_results = await fetch_and_analyze_sources(multi_results, anthropic_client, model_name)
            
            # Add each analysis to the conversation
            for query_type, data in analysis_results.items():
                summary = data["summary"]
                sources = data["sources"]
                
                # Format title based on query type
                if query_type == "matchup":
                    title = f"Analysis of {team1} vs {team2} Matchup"
                elif query_type.endswith("_analysis"):
                    team_name = query_type.replace("_analysis", "")
                    title = f"Analysis of {team_name}"
                elif query_type == "predictions":
                    title = f"Expert Predictions for {team1} vs {team2}"
                elif query_type == "seed_history":
                    title = f"Historical Analysis of #{seed1} vs #{seed2} Seed Matchups"
                else:
                    title = f"Analysis for {query_type}"
                
                # Add Claude's analysis to the conversation
                assistant_message = {
                    "role": "assistant",
                    "content": [
                        {
                            "type": "text",
                            "text": f"I'll review the {title}."
                        }
                    ]
                }
                
                user_message = {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": f"## {title}\n\n{summary}\n\nSources: {', '.join(sources) if sources else 'No sources available'}"
                        }
                    ]
                }
                
                messages.append(assistant_message)
                messages.append(user_message)
                
            logger.info("All analyses added to conversation")
            
        except Exception as e:
            logger.error(f"Error in enhanced analysis: {str(e)}", exc_info=True)
            print(f"Error in enhanced analysis: {str(e)}")
            # Fall back to standard search if enhanced analysis fails
            await add_standard_search_results(messages, team1, team2, seed1, seed2, region, round_name)
    else:
        # Use standard search approach
        await add_standard_search_results(messages, team1, team2, seed1, seed2, region, round_name)
    
    # Final prompt for prediction
    final_prompt = f"""
Based on all the information I've shared about {team1} and {team2}, please provide your prediction for this March Madness matchup.

Note: It's perfectly acceptable to predict games beyond the first round. This is part of a full bracket prediction, so please analyze this matchup directly regardless of which tournament round this game is in.

You should consider:
1. Team strength and statistics
2. Key player matchups
3. Historical tournament performance
4. Coaching experience and strategy
5. Seed matchup history
6. Expert predictions and consensus views
7. Any other relevant factors

Please format your response as:
PREDICTED WINNER: [Team Name]
CONFIDENCE: [XX]% (a number between 50-100)
REASONING: [2-3 key decisive factors that led to your prediction]

Your response should be concise and focused only on the prediction.
"""
    
    assistant_message = {
        "role": "assistant",
        "content": [
            {
                "type": "text",
                "text": "I've analyzed all the information about this matchup. I'll now provide my prediction."
            }
        ]
    }
    
    user_message = {
        "role": "user",
        "content": [
            {
                "type": "text",
                "text": final_prompt
            }
        ]
    }
    
    messages.append(assistant_message)
    messages.append(user_message)
    
    # Get final prediction from Claude
    try:
        logger.info(f"Sending final prediction request to Claude ({len(messages)} messages)")
        
        # Add retry logic for Claude API calls
        max_retries = 3
        retry_count = 0
        response = None
        
        while retry_count < max_retries:
            try:
                response = anthropic_client.messages.create(
                    model=model_name,
                    max_tokens=1000,
                    messages=messages,
                    system=system_prompt
                )
                break  # If successful, exit the retry loop
            except Exception as e:
                retry_count += 1
                logger.warning(f"Claude API error (attempt {retry_count}/{max_retries}): {str(e)}")
                if retry_count < max_retries:
                    wait_time = 2 ** retry_count  # Exponential backoff
                    logger.info(f"Retrying in {wait_time} seconds...")
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"Max retries reached. Using fallback prediction.")
                    raise  # Re-raise to trigger the fallback
        
        # If we got this far, we have a response
        response_text = response.content[0].text
        logger.debug(f"Claude prediction response: {response_text}")
        
        # Extract prediction using regex
        winner_match = re.search(r"PREDICTED WINNER:\s*(.*?)(?:\n|$)", response_text)
        confidence_match = re.search(r"CONFIDENCE:\s*(\d+)%", response_text)
        reasoning_match = re.search(r"REASONING:\s*(.*?)(?:\n\n|$)", response_text, re.DOTALL)
        
        # Add retry logic for parsing failures
        if not (winner_match and confidence_match and reasoning_match):
            # Try one more time with a more direct prompt
            logger.warning("Failed to parse prediction format. Retrying with a clearer prompt.")
            
            clarification_prompt = """
I couldn't parse your prediction clearly. Please respond ONLY with the following format:

PREDICTED WINNER: [Team Name]
CONFIDENCE: [XX]% (a number between 50-100)
REASONING: [2-3 key decisive factors]
            """
            
            # Add the clarification message
            assistant_message = {
                "role": "assistant",
                "content": [{"type": "text", "text": response_text}]
            }
            
            user_message = {
                "role": "user",
                "content": [{"type": "text", "text": clarification_prompt}]
            }
            
            messages.append(assistant_message)
            messages.append(user_message)
            
            # Try again
            try:
                retry_response = anthropic_client.messages.create(
                    model=model_name,
                    max_tokens=1000,
                    messages=messages,
                    system=system_prompt
                )
                
                response_text = retry_response.content[0].text
                logger.debug(f"Claude retry response: {response_text}")
                
                # Try parsing again
                winner_match = re.search(r"PREDICTED WINNER:\s*(.*?)(?:\n|$)", response_text)
                confidence_match = re.search(r"CONFIDENCE:\s*(\d+)%", response_text)
                reasoning_match = re.search(r"REASONING:\s*(.*?)(?:\n\n|$)", response_text, re.DOTALL)
            except Exception as e:
                logger.error(f"Error in parsing retry: {str(e)}")
        
        if winner_match and confidence_match and reasoning_match:
            raw_confidence = int(confidence_match.group(1))
            winner = winner_match.group(1).strip()
            reasoning = reasoning_match.group(1).strip()
            
            # Apply confidence adjustment based on historical seed matchup data
            try:
                upset_factors = get_upset_factors_by_seed_matchup(seed1, seed2)
                confidence_adjustment = upset_factors.get("confidence_adjustment", 0)
                
                # Apply adjustment, but keep confidence between 50-99
                adjusted_confidence = min(99, max(50, raw_confidence + confidence_adjustment))
                
                if adjusted_confidence != raw_confidence:
                    logger.info(f"Adjusted confidence from {raw_confidence}% to {adjusted_confidence}% based on seed matchup history")
                    
                    # If adjustment was significant, add note to reasoning
                    if abs(adjusted_confidence - raw_confidence) >= 5:
                        if adjusted_confidence < raw_confidence:
                            reasoning_note = f" Note: Confidence reduced due to historical upset patterns in {seed1}-{seed2} seed matchups."
                        else:
                            reasoning_note = f" Note: Confidence increased due to historical reliability of {seed1}-{seed2} seed matchups."
                            
                        # Add note only if it doesn't already contain something similar
                        if "historical" not in reasoning.lower() and "seed" not in reasoning.lower():
                            reasoning += reasoning_note
            except Exception as e:
                logger.warning(f"Could not apply confidence adjustment: {str(e)}")
                adjusted_confidence = raw_confidence
            
            prediction = {
                "predicted_winner": winner,
                "confidence": adjusted_confidence,
                "reasoning": reasoning,
                "sources": extract_sources_from_messages(messages)
            }
            logger.info(f"Successful prediction: {prediction['predicted_winner']} with {prediction['confidence']}% confidence")
            return prediction
        else:
            logger.warning(f"Failed to parse Claude response: {response_text}")
            
            # Fallback if regex parsing fails
            return {
                "predicted_winner": team1 if seed1 < seed2 else team2,  # Default to higher seed
                "confidence": 55,
                "reasoning": "Prediction based on seed difference due to parsing error.",
                "sources": extract_sources_from_messages(messages)
            }
            
    except Exception as e:
        logger.error(f"Error getting prediction from Claude: {str(e)}", exc_info=True)
        
        # Fallback prediction based on seeds
        fallback = {
            "predicted_winner": team1 if seed1 < seed2 else team2,
            "confidence": 55,
            "reasoning": f"Prediction based on seed difference due to API error: {str(e)}",
            "sources": []
        }
        logger.info(f"Using fallback prediction: {fallback['predicted_winner']}")
        return fallback

async def add_standard_search_results(messages, team1, team2, seed1, seed2, region, round_name):
    """
    Add standard search results to the conversation.
    Used as a fallback when enhanced analysis fails.
    
    Parameters:
    - messages: Conversation messages list to append to
    - team1_name, team2_name: Team names
    - seed1, seed2: Team seeds
    - region: Tournament region
    - round_name: Current round name
    """
    # Search for information about the matchup
    try:
        from data_fetcher import search_matchup, fetch_content
        logger.info("Using standard search approach")
        search_results = await search_matchup(team1, team2, seed1, seed2, region, round_name)
        logger.info(f"Found {len(search_results)} articles about {team1} vs {team2}")
        print(f"Found {len(search_results)} articles about the matchup")
    except Exception as e:
        logger.error(f"Error searching for matchup information: {str(e)}")
        search_results = []
    
    # Process each search result to gather content
    fetched_content = []
    for idx, result in enumerate(search_results):
        url = result.get('url')
        
        if not url:
            logger.warning(f"Search result {idx+1} has no URL")
            continue
            
        try:
            # Fetch content
            logger.debug(f"Fetching content from {url}")
            content = await fetch_content(url)
            
            # Add to collected content
            fetched_content.append({
                "source": url,
                "content": content
            })
            
            logger.debug(f"Successfully fetched content from {url} ({len(content)} chars)")
            
            # Send this content to Claude
            assistant_message = {
                "role": "assistant",
                "content": [
                    {
                        "type": "text",
                        "text": f"I'll analyze information from source {idx+1} about {team1} vs {team2}."
                    }
                ]
            }
            
            user_message = {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": f"Source {idx+1}: {url}\n\n{content}"
                    }
                ]
            }
            
            messages.append(assistant_message)
            messages.append(user_message)
            
        except Exception as e:
            logger.error(f"Error fetching {url}: {str(e)}")
            print(f"Error fetching source {idx+1}: {str(e)}")
    
    # If no content was fetched, add a note about that
    if not fetched_content:
        logger.warning("No content was fetched from sources")
        
        assistant_message = {
            "role": "assistant",
            "content": [
                {
                    "type": "text",
                    "text": f"I'll analyze this matchup based on the teams' seeds and general March Madness tournament patterns."
                }
            ]
        }
        
        user_message = {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": f"No specific articles were found about this matchup. Please analyze based on the teams' seeds ({team1}: #{seed1}, {team2}: #{seed2}) and your knowledge of NCAA basketball and March Madness patterns."
                }
            ]
        }
        
        messages.append(assistant_message)
        messages.append(user_message)

def extract_sources_from_messages(messages):
    """
    Extract all source URLs from the conversation messages.
    
    Parameters:
    - messages: List of conversation messages
    
    Returns:
    - List of unique source URLs
    """
    sources = []
    
    # Extract sources from user messages
    for message in messages:
        if message["role"] == "user":
            for content in message["content"]:
                text = content.get("text", "")
                
                # Extract URLs from source declarations
                source_matches = re.findall(r"Source \d+: (https?://[^\s\n]+)", text)
                sources.extend(source_matches)
                
                # Extract URLs from "Sources:" lists
                sources_list_match = re.search(r"Sources: (.*?)(?:\n|$)", text)
                if sources_list_match:
                    sources_list = sources_list_match.group(1)
                    url_matches = re.findall(r"(https?://[^,\s]+)", sources_list)
                    sources.extend(url_matches)
    
    # Remove duplicates while preserving order
    unique_sources = []
    seen = set()
    for source in sources:
        if source not in seen:
            seen.add(source)
            unique_sources.append(source)
    
    return unique_sources