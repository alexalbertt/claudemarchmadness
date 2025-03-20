#!/usr/bin/env python3
"""
Context Module
------------
Provides additional context and data for bracket predictions.
"""

import json
import os
import logging

# Set up logger
logger = logging.getLogger('context')

# Global cache for team records
_team_records = None

def load_team_records(bracket_file_path=None):
    """
    Load team records from the bracket JSON file.
    
    Parameters:
    - bracket_file_path: Path to the bracket JSON file
    
    Returns:
    - Dictionary of team records
    """
    global _team_records
    
    # If records are already loaded, return them
    if _team_records is not None:
        return _team_records
    
    # If no file path is provided, try default
    if bracket_file_path is None:
        bracket_file_path = os.path.join(os.getcwd(), "bracket.json")
    
    try:
        with open(bracket_file_path, 'r') as f:
            bracket = json.load(f)
            
        if "team_records" in bracket:
            logger.debug(f"Loaded {len(bracket['team_records'])} team records from {bracket_file_path}")
            _team_records = bracket["team_records"]
            return _team_records
        else:
            logger.warning(f"No team_records found in {bracket_file_path}")
            return {}
    except Exception as e:
        logger.error(f"Error loading team records: {str(e)}")
        return {}

def get_team_records(team_name):
    """
    Get the record for a specific team.
    
    Parameters:
    - team_name: Name of the team
    
    Returns:
    - Team record string or None if not found
    """
    # Ensure records are loaded
    records = load_team_records()
    
    # Try exact match
    if team_name in records:
        return records[team_name]
    
    # Try case-insensitive match
    team_lower = team_name.lower()
    for name, record in records.items():
        if name.lower() == team_lower:
            return record
    
    # Try partial match for teams with / in their name
    if '/' in team_name:
        parts = team_name.split('/')
        for part in parts:
            part = part.strip()
            if part in records:
                return records[part]
    
    logger.warning(f"No record found for team {team_name}")
    return None

def get_upset_factors_by_seed_matchup(seed1, seed2):
    """
    Get historical upset factors for specific seed matchups.
    
    Parameters:
    - seed1: Seed of first team (typically lower number)
    - seed2: Seed of second team (typically higher number)
    
    Returns:
    - Dictionary with upset data and confidence adjustment
    """
    # Ensure lower seed is first
    if seed1 > seed2:
        seed1, seed2 = seed2, seed1
    
    # Dictionary of historical upset data for each seed matchup
    # Format: {(lower_seed, higher_seed): {upset_rate, confidence_adjustment}}
    upset_data = {
        # 1 vs 16: Only one upset in history (UMBC over Virginia in 2018)
        (1, 16): {"upset_rate": 0.01, "confidence_adjustment": 10},
        
        # 2 vs 15: Few upsets but they happen (FGCU, Middle Tennessee, etc)
        (2, 15): {"upset_rate": 0.06, "confidence_adjustment": 5},
        
        # 3 vs 14: Occasional upsets
        (3, 14): {"upset_rate": 0.13, "confidence_adjustment": 0},
        
        # 4 vs 13: More common upset territory
        (4, 13): {"upset_rate": 0.21, "confidence_adjustment": -3},
        
        # 5 vs 12: Famous upset territory - "12-5 upset" is a March Madness tradition
        (5, 12): {"upset_rate": 0.36, "confidence_adjustment": -8},
        
        # 6 vs 11: Very common upset zone
        (6, 11): {"upset_rate": 0.38, "confidence_adjustment": -7},
        
        # 7 vs 10: Nearly even matchups
        (7, 10): {"upset_rate": 0.40, "confidence_adjustment": -10},
        
        # 8 vs 9: Technically not "upsets" - nearly even odds
        (8, 9): {"upset_rate": 0.48, "confidence_adjustment": -15},
    }
    
    # Get the matchup data or provide default
    key = (seed1, seed2) if seed1 <= seed2 else (seed2, seed1)
    
    if key in upset_data:
        return upset_data[key]
    
    # For matchups not explicitly defined, use a formula
    lower_seed, higher_seed = key
    seed_diff = higher_seed - lower_seed
    
    # Estimate upset rate based on seed difference
    if seed_diff > 4:
        upset_rate = 0.05 * seed_diff / 10
    else:
        upset_rate = 0.5 - (seed_diff * 0.05)
        
    # Cap the upset rate between 0.01 and 0.5
    upset_rate = max(0.01, min(0.5, upset_rate))
    
    # Calculate confidence adjustment based on upset rate
    # More likely upsets = lower confidence
    confidence_adjustment = -20 if upset_rate > 0.4 else \
                            -10 if upset_rate > 0.3 else \
                            -5 if upset_rate > 0.2 else \
                            0 if upset_rate > 0.1 else 5
    
    return {
        "upset_rate": upset_rate,
        "confidence_adjustment": confidence_adjustment
    }

def get_team_seed_history(team_name):
    """
    Get historical tournament performance for a team based on their seed.
    This is mock data, but could be expanded with real historical data.
    
    Parameters:
    - team_name: Name of the team
    
    Returns:
    - Dictionary with historical performance data
    """
    # This would be expanded with real historical data in a production system
    seed_performance = {
        1: {"sweet_16_pct": 0.90, "elite_8_pct": 0.70, "final_four_pct": 0.40, "championship_pct": 0.25, "champion_pct": 0.15},
        2: {"sweet_16_pct": 0.80, "elite_8_pct": 0.50, "final_four_pct": 0.25, "championship_pct": 0.15, "champion_pct": 0.07},
        3: {"sweet_16_pct": 0.70, "elite_8_pct": 0.40, "final_four_pct": 0.15, "championship_pct": 0.08, "champion_pct": 0.03},
        4: {"sweet_16_pct": 0.60, "elite_8_pct": 0.30, "final_four_pct": 0.10, "championship_pct": 0.05, "champion_pct": 0.02},
        5: {"sweet_16_pct": 0.50, "elite_8_pct": 0.20, "final_four_pct": 0.07, "championship_pct": 0.02, "champion_pct": 0.01},
        6: {"sweet_16_pct": 0.40, "elite_8_pct": 0.15, "final_four_pct": 0.05, "championship_pct": 0.01, "champion_pct": 0.005},
        7: {"sweet_16_pct": 0.30, "elite_8_pct": 0.10, "final_four_pct": 0.03, "championship_pct": 0.01, "champion_pct": 0.003},
        8: {"sweet_16_pct": 0.20, "elite_8_pct": 0.08, "final_four_pct": 0.02, "championship_pct": 0.005, "champion_pct": 0.001},
        9: {"sweet_16_pct": 0.20, "elite_8_pct": 0.07, "final_four_pct": 0.02, "championship_pct": 0.003, "champion_pct": 0.001},
        10: {"sweet_16_pct": 0.15, "elite_8_pct": 0.05, "final_four_pct": 0.01, "championship_pct": 0.002, "champion_pct": 0.0005},
        11: {"sweet_16_pct": 0.10, "elite_8_pct": 0.04, "final_four_pct": 0.01, "championship_pct": 0.001, "champion_pct": 0.0003},
        12: {"sweet_16_pct": 0.08, "elite_8_pct": 0.03, "final_four_pct": 0.005, "championship_pct": 0.0005, "champion_pct": 0.0001},
        13: {"sweet_16_pct": 0.05, "elite_8_pct": 0.01, "final_four_pct": 0.003, "championship_pct": 0.0003, "champion_pct": 0.00005},
        14: {"sweet_16_pct": 0.03, "elite_8_pct": 0.005, "final_four_pct": 0.001, "championship_pct": 0.0001, "champion_pct": 0.00001},
        15: {"sweet_16_pct": 0.01, "elite_8_pct": 0.003, "final_four_pct": 0.0005, "championship_pct": 0.00005, "champion_pct": 0.000001},
        16: {"sweet_16_pct": 0.005, "elite_8_pct": 0.001, "final_four_pct": 0.0001, "championship_pct": 0.00001, "champion_pct": 0.000001},
    }
    
    # Find the team's seed from the bracket
    bracket_file_path = os.path.join(os.getcwd(), "bracket.json")
    try:
        with open(bracket_file_path, 'r') as f:
            bracket = json.load(f)
            
        # Search for the team in the first round
        for game in bracket["rounds"][0]["games"]:
            if game["team1"]["name"] == team_name:
                seed = game["team1"]["seed"]
                return seed_performance.get(seed, {})
            elif game["team2"]["name"] == team_name:
                seed = game["team2"]["seed"]
                return seed_performance.get(seed, {})
                
        logger.warning(f"Could not find seed for team {team_name}")
        return {}
    except Exception as e:
        logger.error(f"Error getting seed history: {str(e)}")
        return {}