#!/usr/bin/env python3
"""
Bracket Manager Module
---------------------
Handles bracket structure and management.
"""

import os
import json
import asyncio
import logging
import random
from datetime import datetime
from claude_integration import predict_game
from utils import get_round_name, get_team_by_name, get_previous_game_id

# Set up logger
logger = logging.getLogger('bracket_manager')

async def process_bracket(bracket_file_path, output_path, anthropic_client, model_name="claude-3-5-sonnet-20241022", 
                         test_mode=False, dry_run=False, debug_level=0, use_enhanced_analysis=True):
    """
    Process an entire March Madness bracket.
    
    Parameters:
    - bracket_file_path: Path to initial bracket JSON file
    - output_path: Directory to save results and checkpoints
    - anthropic_client: Initialized Anthropic client
    - model_name: Claude model to use
    - test_mode: If True, only process first two games
    - dry_run: If True, use mock predictions without making API calls
    - debug_level: Logging verbosity level
    - use_enhanced_analysis: If True, use the multi-query, multi-analysis approach
    
    Returns:
    - Path to completed bracket file
    """
    logger.info(f"Loading bracket from {bracket_file_path}")
    
    # Load initial bracket
    try:
        with open(bracket_file_path, 'r') as f:
            bracket = json.load(f)
        logger.debug(f"Bracket loaded successfully: {bracket['tournament_name']}")
    except Exception as e:
        logger.error(f"Failed to load bracket: {str(e)}")
        raise
    
    # Create a timestamp for this run
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Save a copy of the initial bracket
    initial_bracket_path = os.path.join(output_path, f"initial_bracket_{timestamp}.json")
    with open(initial_bracket_path, 'w') as f:
        json.dump(bracket, f, indent=2)
    logger.debug(f"Initial bracket saved to {initial_bracket_path}")
    
    # Process each round
    for round_idx, round_data in enumerate(bracket["rounds"]):
        # Skip if this round doesn't have games yet
        if not round_data["games"]:
            logger.debug(f"Skipping {round_data['round_name']} (no games)")
            continue
            
        round_number = round_data["round_number"]
        round_name = round_data["round_name"]
        
        logger.info(f"Processing {round_name} ({len(round_data['games'])} games)")
        print(f"\nProcessing {round_name} ({len(round_data['games'])} games)")
        
        # Process each game in the round
        game_count = 0
        for game_idx, game in enumerate(round_data["games"]):
            game_id = game["game_id"]
            
            # Skip already predicted games (for resuming)
            if game.get("predicted_winner") is not None:
                logger.info(f"Skipping game {game_id} (already predicted)")
                print(f"Skipping game {game_id} (already predicted)")
                continue
                
            # Check if we should start from this game (resuming)
            if bracket["last_completed_game_id"] is not None:
                prev_game_id = get_previous_game_id(game_id, bracket)
                if prev_game_id and bracket["last_completed_game_id"] != prev_game_id:
                    logger.debug(f"Skipping game {game_id} (resuming from later game)")
                    continue
            
            team1 = game["team1"]["name"]
            team2 = game["team2"]["name"]
            
            logger.info(f"Predicting game {game_id}: {team1} vs {team2}")
            print(f"\nPredicting game {game_id}: {team1} (Seed #{game['team1']['seed']}) vs {team2} (Seed #{game['team2']['seed']})")
            
            # In test mode, only process first two games
            game_count += 1
            if test_mode and game_count > 2:
                logger.info("Test mode: stopping after two games")
                break
            
            # Get prediction for this game
            try:
                if dry_run:
                    # Use mock prediction without API calls
                    logger.debug("Dry run mode: using mock prediction")
                    prediction = _generate_mock_prediction(game)
                    # Simulate API call delay
                    await asyncio.sleep(1)
                else:
                    # Get real prediction using either enhanced or standard analysis
                    prediction = await predict_game(
                        game, 
                        anthropic_client, 
                        model_name,
                        use_enhanced_analysis=use_enhanced_analysis
                    )
                
                # Debug the prediction
                logger.debug(f"Prediction for {game_id}: {prediction}")
                
                # Update game with prediction
                game["predicted_winner"] = prediction["predicted_winner"]
                game["confidence"] = prediction["confidence"]
                game["reasoning"] = prediction["reasoning"]
                game["sources"] = prediction["sources"]
                
                # Update last_completed_game_id
                bracket["last_completed_game_id"] = game_id
                
                # Save checkpoint after each game
                checkpoint_path = os.path.join(output_path, f"bracket_checkpoint_{game_id}.json")
                with open(checkpoint_path, 'w') as f:
                    json.dump(bracket, f, indent=2)
                
                logger.info(f"Predicted winner: {prediction['predicted_winner']} (Confidence: {prediction['confidence']}%)")
                print(f"Predicted winner: {prediction['predicted_winner']} (Confidence: {prediction['confidence']}%)")
                print(f"Reasoning: {prediction['reasoning']}")
                
            except Exception as e:
                logger.error(f"Error predicting game {game_id}: {str(e)}", exc_info=True)
                print(f"Error predicting game {game_id}: {str(e)}")
                
                # Create a checkpoint with error info
                error_checkpoint_path = os.path.join(output_path, f"error_checkpoint_{game_id}.json")
                bracket["error"] = {
                    "game_id": game_id,
                    "error_message": str(e),
                    "timestamp": datetime.now().isoformat()
                }
                with open(error_checkpoint_path, 'w') as f:
                    json.dump(bracket, f, indent=2)
                
                # Re-raise if in debug mode, otherwise continue
                if debug_level > 1:
                    raise
        
        # After completing this round, generate next round matchups
        if round_number < len(bracket["rounds"]):
            next_round_idx = round_number
            next_round = bracket["rounds"][next_round_idx]
            
            # Only generate next round if all games in current round are predicted
            all_predicted = all(game.get("predicted_winner") is not None for game in round_data["games"])
            
            if all_predicted:
                logger.info(f"Generating matchups for {next_round['round_name']}")
                print(f"\nGenerating matchups for {next_round['round_name']}")
                
                try:
                    next_round["games"] = generate_next_round_games(round_data["games"], next_round["round_number"])
                    
                    # Update bracket with new games
                    bracket["rounds"][next_round_idx] = next_round
                    bracket["current_round"] = next_round["round_number"]
                    
                    # Save checkpoint after generating next round
                    checkpoint_path = os.path.join(output_path, f"bracket_checkpoint_round_{round_number}.json")
                    with open(checkpoint_path, 'w') as f:
                        json.dump(bracket, f, indent=2)
                    
                    logger.info(f"Generated {len(next_round['games'])} games for {next_round['round_name']}")
                    
                    # In test mode, only process first round
                    if test_mode:
                        logger.info("Test mode: stopping after first round")
                        break
                        
                except Exception as e:
                    logger.error(f"Error generating next round: {str(e)}", exc_info=True)
                    print(f"Error generating next round: {str(e)}")
                    
                    # Re-raise if in debug mode
                    if debug_level > 1:
                        raise
            else:
                logger.warning(f"Not all games in {round_name} have predictions. Skipping next round generation.")
                print(f"Warning: Not all games in {round_name} have predictions. Skipping next round generation.")
                break
    
    # Save final bracket
    final_path = os.path.join(output_path, f"final_bracket_{timestamp}.json")
    with open(final_path, 'w') as f:
        json.dump(bracket, f, indent=2)
    
    # Also save as standard final_bracket.json
    standard_final_path = os.path.join(output_path, "final_bracket.json")
    with open(standard_final_path, 'w') as f:
        json.dump(bracket, f, indent=2)
    
    logger.info(f"Final bracket saved to {final_path}")
    return standard_final_path

def _generate_mock_prediction(game):
    """Generate a mock prediction for testing without API calls."""
    team1 = game["team1"]
    team2 = game["team2"]
    
    # Mock logic: higher seed has better chance of winning
    seed_diff = abs(team1["seed"] - team2["seed"])
    
    # Base probability for higher seed
    if team1["seed"] < team2["seed"]:
        higher_seed_team = team1
        lower_seed_team = team2
        # Higher seed has better chance
        p_higher_seed_wins = 0.5 + (seed_diff * 0.05)
    else:
        higher_seed_team = team2
        lower_seed_team = team1
        # Higher seed has better chance
        p_higher_seed_wins = 0.5 + (seed_diff * 0.05)
    
    # Cap probability between 0.55 and 0.95
    p_higher_seed_wins = min(0.95, max(0.55, p_higher_seed_wins))
    
    # Determine winner with randomness
    if random.random() < p_higher_seed_wins:
        winner = higher_seed_team["name"]
        confidence = int(p_higher_seed_wins * 100)
        reasoning = f"Superior ranking as a #{higher_seed_team['seed']} seed compared to #{lower_seed_team['seed']} seed, with stronger overall performance this season."
    else:
        winner = lower_seed_team["name"]
        confidence = int((1 - p_higher_seed_wins) * 100)
        reasoning = f"Despite being a lower #{lower_seed_team['seed']} seed, they have momentum and matchup advantages against #{higher_seed_team['seed']} seed."
    
    # Create mock prediction
    return {
        "predicted_winner": winner,
        "confidence": confidence,
        "reasoning": reasoning,
        "sources": ["https://example.com/mock-data-source"]
    }

def generate_next_round_games(current_round_games, next_round_number):
    """
    Generate matchups for the next round based on current round results.
    
    Parameters:
    - current_round_games: List of games from current round with predictions
    - next_round_number: Number of the next round
    
    Returns:
    - List of games for the next round
    """
    logger.debug(f"Generating games for round {next_round_number}")
    next_round_games = []
    
    # Process pairs of games to create next round matchups
    for i in range(0, len(current_round_games), 2):
        # Ensure we have a pair
        if i + 1 >= len(current_round_games):
            logger.warning(f"Odd number of games in round: {len(current_round_games)}")
            break
            
        game1 = current_round_games[i]
        game2 = current_round_games[i + 1]
        
        # Validate predictions exist
        if not game1.get("predicted_winner") or not game2.get("predicted_winner"):
            logger.error(f"Missing prediction for game {game1.get('game_id')} or {game2.get('game_id')}")
            raise ValueError(f"Cannot generate next round: missing prediction for one or more games")
        
        # Get winners
        winner1 = get_team_by_name(game1, game1["predicted_winner"])
        winner2 = get_team_by_name(game2, game2["predicted_winner"])
        
        # Determine region for the new game
        if next_round_number == 5:
            # For the Final Four, the regions are combined
            if game1["region"] in ["South", "East"]:
                region = "South/East"
            else:
                region = "West/Midwest"
        elif next_round_number == 6:
            # Championship game has no region
            region = "Championship"
        else:
            # Regular rounds keep the same region
            region = game1["region"]
        
        # Create new game
        new_game = {
            "game_id": f"R{next_round_number}G{len(next_round_games) + 1}",
            "region": region,
            "team1": winner1,
            "team2": winner2,
            "predicted_winner": None,
            "confidence": None,
            "reasoning": None,
            "sources": []
        }
        
        logger.debug(f"Created new game {new_game['game_id']}: {winner1['name']} vs {winner2['name']}")
        next_round_games.append(new_game)
    
    return next_round_games