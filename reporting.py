#!/usr/bin/env python3
"""
Reporting Module
--------------
Generates reports and summaries from bracket predictions.
"""

import os
import json
from datetime import datetime

def generate_report(bracket_file_path, output_path):
    """
    Generate a summary report from the final bracket.
    
    Parameters:
    - bracket_file_path: Path to the final bracket JSON file
    - output_path: Directory to save the report
    
    Returns:
    - Path to the generated report
    """
    # Load the bracket
    with open(bracket_file_path, 'r') as f:
        bracket = json.load(f)
    
    # Initialize the report
    report = []
    report.append(f"# {bracket['tournament_name']} Prediction Report")
    report.append(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # Add tournament winner
    championship_round = bracket["rounds"][-1]
    if championship_round["games"] and championship_round["games"][0]["predicted_winner"]:
        champion = championship_round["games"][0]["predicted_winner"]
        confidence = championship_round["games"][0]["confidence"]
        reasoning = championship_round["games"][0]["reasoning"]
        
        report.append(f"## Tournament Champion: {champion}")
        report.append(f"Confidence: {confidence}%")
        report.append(f"Reasoning: {reasoning}\n")
    
    # Add Final Four teams
    final_four_round = bracket["rounds"][4]  # Round 5 is Final Four
    if final_four_round["games"]:
        report.append("## Final Four Teams")
        for game in final_four_round["games"]:
            team1 = game["team1"]["name"]
            team2 = game["team2"]["name"]
            winner = game["predicted_winner"] if game.get("predicted_winner") else "TBD"
            report.append(f"- {team1} vs {team2} - Winner: {winner}")
        report.append("")
    
    # Collect upset predictions (lower seed beating higher seed)
    upsets = []
    for round_data in bracket["rounds"]:
        for game in round_data["games"]:
            if game.get("predicted_winner"):
                team1_seed = game["team1"]["seed"]
                team2_seed = game["team2"]["seed"]
                winner = game["predicted_winner"]
                
                # Check if an upset occurred
                if (winner == game["team1"]["name"] and team1_seed > team2_seed) or \
                   (winner == game["team2"]["name"] and team2_seed > team1_seed):
                    
                    # Determine the underdog and favorite
                    if winner == game["team1"]["name"]:
                        underdog = game["team1"]
                        favorite = game["team2"]
                    else:
                        underdog = game["team2"]
                        favorite = game["team1"]
                    
                    upsets.append({
                        "round": round_data["round_name"],
                        "underdog": underdog["name"],
                        "underdog_seed": underdog["seed"],
                        "favorite": favorite["name"],
                        "favorite_seed": favorite["seed"],
                        "confidence": game["confidence"],
                        "reasoning": game["reasoning"]
                    })
    
    # Add upset predictions to report
    if upsets:
        report.append("## Predicted Upsets")
        
        # Sort upsets by seed differential (biggest upsets first)
        upsets.sort(key=lambda x: x["favorite_seed"] - x["underdog_seed"], reverse=True)
        
        for upset in upsets:
            report.append(f"### {upset['underdog']} (#{upset['underdog_seed']}) over {upset['favorite']} (#{upset['favorite_seed']})")
            report.append(f"Round: {upset['round']}")
            report.append(f"Confidence: {upset['confidence']}%")
            report.append(f"Reasoning: {upset['reasoning']}\n")
    
    # Add region winners
    report.append("## Region Winners")
    elite_eight = bracket["rounds"][3]  # Round 4 is Elite Eight
    regions = set(game["region"] for game in elite_eight["games"] if "region" in game)
    
    for region in regions:
        region_games = [game for game in elite_eight["games"] if game.get("region") == region]
        if region_games and region_games[0].get("predicted_winner"):
            region_winner = region_games[0]["predicted_winner"]
            report.append(f"- {region} Region: {region_winner}")
    report.append("")
    
    # Add round-by-round summary
    report.append("## Round-by-Round Summary")
    for round_data in bracket["rounds"]:
        if round_data["games"]:
            report.append(f"### {round_data['round_name']}")
            for game in round_data["games"]:
                team1 = game["team1"]["name"]
                team2 = game["team2"]["name"]
                if game.get("predicted_winner"):
                    report.append(f"- {team1} vs {team2} - Winner: {game['predicted_winner']} (Confidence: {game['confidence']}%)")
                else:
                    report.append(f"- {team1} vs {team2} - Winner: TBD")
            report.append("")
    
    # Write the report to a file
    report_path = os.path.join(output_path, "bracket_prediction_report.md")
    with open(report_path, 'w') as f:
        f.write("\n".join(report))
    
    print(f"Report generated at: {report_path}")
    return report_path

def generate_html_bracket(bracket_file_path, output_path):
    """
    Generate an HTML visualization of the bracket.
    
    Parameters:
    - bracket_file_path: Path to the bracket JSON file
    - output_path: Directory to save the HTML file
    
    Returns:
    - Path to the generated HTML file
    """
    # Load the bracket
    with open(bracket_file_path, 'r') as f:
        bracket = json.load(f)
    
    # Basic HTML template
    html = []
    html.append("<!DOCTYPE html>")
    html.append("<html lang='en'>")
    html.append("<head>")
    html.append("    <meta charset='UTF-8'>")
    html.append("    <meta name='viewport' content='width=device-width, initial-scale=1.0'>")
    html.append(f"    <title>{bracket['tournament_name']} Predictions</title>")
    html.append("    <style>")
    html.append("        body { font-family: Arial, sans-serif; margin: 20px; }")
    html.append("        .bracket { display: flex; overflow-x: auto; padding: 20px; }")
    html.append("        .round { margin-right: 40px; min-width: 220px; }")
    html.append("        .game { border: 1px solid #ccc; margin-bottom: 15px; padding: 10px; }")
    html.append("        .team { padding: 5px; }")
    html.append("        .winner { font-weight: bold; background-color: #e8f4e8; }")
    html.append("        .seed { display: inline-block; width: 25px; text-align: center; margin-right: 5px; }")
    html.append("        h1, h2 { color: #333; }")
    html.append("        .confidence { font-size: 0.8em; color: #666; }")
    html.append("    </style>")
    html.append("</head>")
    html.append("<body>")
    html.append(f"    <h1>{bracket['tournament_name']} Predictions</h1>")
    html.append("    <div class='bracket'>")
    
    # Add each round
    for round_data in bracket["rounds"]:
        html.append(f"        <div class='round'>")
        html.append(f"            <h2>{round_data['round_name']}</h2>")
        
        for game in round_data["games"]:
            html.append(f"            <div class='game'>")
            
            # Team 1
            winner_class = " winner" if game.get("predicted_winner") == game["team1"]["name"] else ""
            html.append(f"                <div class='team{winner_class}'>")
            html.append(f"                    <span class='seed'>{game['team1']['seed']}</span>")
            html.append(f"                    {game['team1']['name']}")
            html.append(f"                </div>")
            
            # Team 2
            winner_class = " winner" if game.get("predicted_winner") == game["team2"]["name"] else ""
            html.append(f"                <div class='team{winner_class}'>")
            html.append(f"                    <span class='seed'>{game['team2']['seed']}</span>")
            html.append(f"                    {game['team2']['name']}")
            html.append(f"                </div>")
            
            # Add prediction information if available
            if game.get("predicted_winner"):
                html.append(f"                <div class='confidence'>")
                html.append(f"                    Confidence: {game['confidence']}%")
                html.append(f"                </div>")
            
            html.append(f"            </div>")
        
        html.append(f"        </div>")
    
    html.append("    </div>")
    html.append("</body>")
    html.append("</html>")
    
    # Write the HTML to a file
    html_path = os.path.join(output_path, "bracket_visualization.html")
    with open(html_path, 'w') as f:
        f.write("\n".join(html))
    
    print(f"HTML visualization generated at: {html_path}")
    return html_path