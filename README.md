# March Madness Bracket Prediction System

A Python-based system for predicting NCAA March Madness tournament outcomes using Claude AI and Exa for data retrieval.

## Overview

This system uses Claude to analyze basketball matchups and predict the outcomes of March Madness games. It processes the tournament bracket round by round, searching for information about each matchup, and generates predictions with confidence levels and reasoning.

## Features

- Automated prediction of entire March Madness bracket
- Multiple search strategies to gather comprehensive information
- Parallel analysis of different information types (team stats, matchup history, expert predictions)
- Enhanced multi-query approach that combines multiple analyses
- Web search for up-to-date information on teams and matchups
- Claude AI integration for intelligent analysis and predictions
- Historical upset pattern analysis with seed-based confidence adjustment
- Robust retry logic for API calls and prediction parsing
- Checkpoint system for resuming predictions
- Resumable execution with automatic background processing
- Detailed prediction reports with upset alerts and region winners
- HTML bracket visualization
- Run-specific results folder for easy organization

## Installation

1. Clone the repository
2. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Set up environment variables in a `.env` file:
   ```
   ANTHROPIC_API_KEY=your_anthropic_api_key
   EXA_API_KEY=your_exa_api_key
   CLAUDE_MODEL=claude-3-7-sonnet-20250219 # optional, defaults to Claude 3.7 Sonnet
   ```

## Usage

Basic usage:
```
python main.py --bracket bracket.json --output results
```

This will create a timestamped subfolder in the `results` directory with all outputs from this run.

### Command Line Arguments

- `--bracket`: Path to the initial bracket JSON file (required)
- `--output`: Directory to save results (required)
- `--checkpoint`: Path to a checkpoint file to resume from (optional)
- `--model`: Claude model to use (optional, defaults to env var or claude-3-5-sonnet)
- `--debug` or `-d`: Increase debug output level (use `-dd` for maximum debug info)
- `--test`: Test mode - only process first two games
- `--dry-run`: Don't make actual API calls, use mock predictions
- `--run-name`: Custom name for this run (defaults to timestamp)
- `--simple-analysis`: Use simple analysis instead of enhanced multi-query approach

### Example Commands

Test run with only 2 games:
```
python main.py --bracket bracket.json --output results --test --run-name test_run
```

Debug mode with detailed logging:
```
python main.py --bracket bracket.json --output results -dd
```

Dry run with mock predictions (no API calls):
```
python main.py --bracket bracket.json --output results --dry-run
```

Use simple analysis mode (faster but less comprehensive):
```
python main.py --bracket bracket.json --output results --simple-analysis
```

Resume from a checkpoint:
```
python main.py --bracket bracket.json --output results --checkpoint results/latest/bracket_checkpoint_R1G4.json
```

### Resumable Execution Script

The `run_with_resume.sh` script provides a convenient way to run predictions in the background and automatically resume from the latest checkpoint:

```
./run_with_resume.sh --name my_run
```

This runs the prediction process in the background with nohup, saving the process ID for easy management. If you run the script again with the same name, it will automatically find the latest checkpoint and resume from there.

Options:
- `--name`: Run name (required)
- `--bracket`: Path to bracket file (defaults to bracket.json)
- `--output`: Output directory (defaults to results)
- `--dry-run`: Use dry run mode
- `--test`: Use test mode
- `--simple-analysis`: Use simple analysis mode
- `--debug`: Enable debug logging

To stop a running process:
```
kill $(cat results/your_run_name/process.pid)
```

## Enhanced Analysis Mode

By default, the system uses an enhanced multi-query approach to gather and analyze information:

1. **Multiple search queries**: For each matchup, the system generates 5 different queries:
   - General matchup information
   - Team 1 analysis and statistics
   - Team 2 analysis and statistics
   - Predictions and betting odds
   - Historical seed matchup data

2. **Parallel processing**: Searches and content fetching happen in parallel

3. **Distributed analysis**: Each search category gets analyzed separately by Claude

4. **Combined final analysis**: All separate analyses are combined for the final prediction

This approach provides more comprehensive information but uses more API calls. Use `--simple-analysis` for a faster, less intensive approach.

## Historical Upset Pattern Analysis

The system includes a sophisticated confidence adjustment mechanism based on historical seed matchup data:

1. **Seed-based upset patterns**: The system analyzes historical upset rates between different seeds (e.g., the famous 5-12 matchups have a ~36% upset rate)

2. **Confidence adjustment**: Adjusts Claude's raw confidence score based on historical patterns:
   - Reduces confidence for matchups prone to upsets (e.g., 5-12, 6-11, 7-10)
   - Increases confidence for historically reliable matchups (e.g., 1-16)
   
3. **Reasoning enhancement**: When significant adjustments are made, the system adds a note to the reasoning explaining the historical context

This feature ensures predictions account for the specific dynamics of March Madness tournament history.

## File Structure

- `main.py`: Main execution module
- `bracket_manager.py`: Handles bracket progression and game generation
- `claude_integration.py`: Communication with Claude API
- `data_fetcher.py`: Retrieves data about teams and matchups
- `context.py`: Provides context information like team records
- `utils.py`: Utility functions
- `reporting.py`: Generates reports and visualizations

## Output

The system produces several outputs in each run-specific directory:

1. `input_bracket.json`: Copy of the initial bracket
2. `bracket_checkpoint_*.json`: Checkpoint files after each game prediction
3. `final_bracket.json`: Complete bracket with all predictions
4. `bracket_prediction_report.md`: Markdown report with analysis of predictions
5. `bracket_visualization.html`: Interactive HTML visualization of the bracket
6. `bracket_prediction.log`: Detailed log file for debugging

The `latest` symlink in the output directory always points to the most recent run.

## License

MIT