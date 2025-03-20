#!/usr/bin/env python3
"""
Utility Functions
---------------
Helper functions for the bracket prediction system.
"""

import logging
import re

# Set up logger
logger = logging.getLogger('utils')

def get_round_name(game_id):
    """
    Convert game ID to round name.
    
    Parameters:
    - game_id: Game identifier (e.g., "R1G1")
    
    Returns:
    - Round name as string
    """
    round_map = {
        "R1": "First Round",
        "R2": "Second Round",
        "R3": "Sweet 16",
        "R4": "Elite Eight",
        "R5": "Final Four",
        "R6": "National Championship"
    }
    
    if not game_id or not isinstance(game_id, str):
        logger.warning(f"Invalid game_id: {game_id}")
        return "Unknown Round"
    
    # Extract round number
    match = re.match(r'R(\d+)G\d+', game_id)
    if match:
        round_key = f"R{match.group(1)}"
        return round_map.get(round_key, "Unknown Round")
    else:
        logger.warning(f"Unexpected game_id format: {game_id}")
        return "Unknown Round"

def get_team_by_name(game, team_name):
    """
    Get team data structure by name from a game.
    
    Parameters:
    - game: Game data structure
    - team_name: Name of the team to find
    
    Returns:
    - Team data structure or fallback to higher seed
    """
    if not game or not team_name:
        logger.error(f"Invalid arguments: game={game}, team_name={team_name}")
        return None
    
    if not isinstance(game, dict) or "team1" not in game or "team2" not in game:
        logger.error(f"Invalid game structure: {game}")
        return None
    
    # Try exact match first
    if game["team1"]["name"] == team_name:
        return game["team1"]
    elif game["team2"]["name"] == team_name:
        return game["team2"]
    
    # Try case-insensitive match
    team_lower = team_name.lower()
    if game["team1"]["name"].lower() == team_lower:
        return game["team1"]
    elif game["team2"]["name"].lower() == team_lower:
        return game["team2"]
    
    # Fallback to higher seed if team not found
    logger.warning(f"Team '{team_name}' not found in game {game.get('game_id', 'unknown')}. Defaulting to higher seed.")
    return game["team1"] if game["team1"]["seed"] < game["team2"]["seed"] else game["team2"]

def get_previous_game_id(game_id, bracket):
    """
    Get the ID of the game that would come before this one.
    
    Parameters:
    - game_id: Current game ID
    - bracket: Full bracket data
    
    Returns:
    - Previous game ID
    """
    if not game_id or not bracket:
        logger.warning(f"Invalid arguments: game_id={game_id}, bracket={type(bracket)}")
        return None
    
    try:
        match = re.match(r'R(\d+)G(\d+)', game_id)
        if not match:
            logger.warning(f"Unexpected game_id format: {game_id}")
            return None
            
        round_num = int(match.group(1))
        game_num = int(match.group(2))
        
        # If first game in round, return last game of previous round
        if game_num == 1:
            if round_num == 1:
                # No previous game for first game of first round
                return None
                
            prev_round = round_num - 1
            # Get previous round's games
            if prev_round < 1 or prev_round > len(bracket["rounds"]):
                logger.warning(f"Invalid previous round: {prev_round}")
                return None
                
            prev_round_games = bracket["rounds"][prev_round - 1]["games"]
            if prev_round_games:
                return prev_round_games[-1]["game_id"]
            return None
        else:
            return f"R{round_num}G{game_num - 1}"
    except Exception as e:
        logger.error(f"Error getting previous game ID: {str(e)}")
        return None

def estimate_token_count(text_length):
    """
    Rough estimation of token count for context management.
    
    Parameters:
    - text_length: Length of text in characters
    
    Returns:
    - Estimated token count
    """
    if not isinstance(text_length, (int, float)):
        logger.warning(f"Invalid text_length: {text_length}")
        return 0
        
    # Claude uses about 4 characters per token on average
    return text_length // 4  # Approximate 4 chars per token

def sanitize_team_name(name):
    """
    Sanitize team name for comparison.
    
    Parameters:
    - name: Team name
    
    Returns:
    - Sanitized team name
    """
    if not name:
        return ""
        
    # Remove common suffixes
    suffixes = [" University", " College", " Univ.", " Coll."]
    result = name
    for suffix in suffixes:
        result = result.replace(suffix, "")
    
    # Handle special cases
    if "/" in result:
        # For play-in games, take first team
        result = result.split("/")[0].strip()
    
    # Remove special characters and normalize spaces
    result = re.sub(r'[^\w\s]', '', result)
    result = re.sub(r'\s+', ' ', result).strip()
    
    return result