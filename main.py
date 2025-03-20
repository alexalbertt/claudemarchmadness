#!/usr/bin/env python3
"""
March Madness Bracket Prediction System
---------------------------------------
Main execution module for the prediction system.
"""

import os
import json
import asyncio
import argparse
import logging
import sys
from datetime import datetime
from dotenv import load_dotenv

from bracket_manager import process_bracket
from reporting import generate_report, generate_html_bracket
from anthropic import Anthropic

# Configure logging
def setup_logging(debug_level, log_dir):
    """Configure logging based on debug level."""
    log_levels = {
        0: logging.WARNING,
        1: logging.INFO,
        2: logging.DEBUG
    }
    log_level = log_levels.get(debug_level, logging.DEBUG)
    
    # Ensure log directory exists
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, 'bracket_prediction.log')
    
    # Configure root logger
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(log_file, mode='w')
        ]
    )
    
    # Return logger for main module
    return logging.getLogger('main')

async def main():
    """Main execution function."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="March Madness Bracket Predictor")
    parser.add_argument("--bracket", required=True, help="Path to initial bracket JSON file")
    parser.add_argument("--output", required=True, help="Directory to save results")
    parser.add_argument("--checkpoint", help="Path to checkpoint file to resume from")
    parser.add_argument("--model", help="Claude model to use")
    parser.add_argument("--debug", "-d", action="count", default=0, 
                        help="Debug level (use multiple times for higher levels: -d, -dd)")
    parser.add_argument("--test", action="store_true", 
                        help="Test mode: Only process first two games with mock data")
    parser.add_argument("--dry-run", action="store_true",
                        help="Dry run: Don't make actual API calls, use placeholder predictions")
    parser.add_argument("--run-name", help="Custom name for this run")
    parser.add_argument("--simple-analysis", action="store_true",
                        help="Use simple analysis instead of enhanced multi-query approach")
    args = parser.parse_args()
    
    # Create a run-specific subfolder in the output directory
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_name = args.run_name or f"run_{timestamp}"
    run_dir = os.path.join(args.output, run_name)
    
    # Create output directories
    os.makedirs(args.output, exist_ok=True)
    os.makedirs(run_dir, exist_ok=True)
    
    # Set up logging
    logger = setup_logging(args.debug, run_dir)
    logger.info(f"Starting March Madness bracket prediction system (Run: {run_name})")
    
    # Determine analysis mode
    use_enhanced_analysis = not args.simple_analysis
    analysis_mode = "SIMPLE" if args.simple_analysis else "ENHANCED (with multi-query approach)"
    
    # Print run info
    print(f"\n========== March Madness Bracket Prediction ==========")
    print(f"Run: {run_name}")
    print(f"Output directory: {run_dir}")
    if args.test:
        print("Mode: TEST (limited to first two games)")
    elif args.dry_run:
        print("Mode: DRY RUN (using mock predictions)")
    else:
        print("Mode: FULL RUN")
    print(f"Analysis: {analysis_mode}")
    print(f"========================================================\n")
    
    # Load environment variables
    load_dotenv()
    logger.debug("Environment variables loaded")
    
    # Check for required API keys
    required_keys = ["ANTHROPIC_API_KEY", "EXA_API_KEY"]
    missing_keys = [key for key in required_keys if not os.environ.get(key)]
    if missing_keys:
        logger.error(f"Missing required environment variables: {', '.join(missing_keys)}")
        print(f"Error: Missing required environment variables: {', '.join(missing_keys)}")
        return
    
    # Set model from args or environment
    model = args.model or os.environ.get("CLAUDE_MODEL", "claude-3-5-sonnet-20241022")
    logger.info(f"Using Claude model: {model}")
    
    # Initialize Anthropic client
    try:
        anthropic_api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not anthropic_api_key:
            logger.error("Missing ANTHROPIC_API_KEY environment variable")
            print("Error: Missing ANTHROPIC_API_KEY environment variable")
            return
            
        anthropic_client = Anthropic(api_key=anthropic_api_key)
        logger.debug("Anthropic client initialized with API key: [MASKED]")
    except Exception as e:
        logger.error(f"Failed to initialize Anthropic client: {str(e)}")
        print(f"Error: Failed to initialize Anthropic client: {str(e)}")
        return
    
    # Verify bracket file exists
    bracket_path = args.checkpoint if args.checkpoint else args.bracket
    if not os.path.exists(bracket_path):
        logger.error(f"Bracket file not found: {bracket_path}")
        print(f"Error: Bracket file not found: {bracket_path}")
        return
    
    # Copy the input bracket to the run directory for reference
    try:
        with open(bracket_path, 'r') as src:
            input_bracket = json.load(src)
            input_bracket_path = os.path.join(run_dir, "input_bracket.json")
            with open(input_bracket_path, 'w') as dest:
                json.dump(input_bracket, dest, indent=2)
        logger.debug(f"Copied input bracket to {input_bracket_path}")
    except Exception as e:
        logger.warning(f"Could not copy input bracket: {str(e)}")
    
    # Process the bracket
    try:
        logger.info(f"Processing bracket from: {bracket_path}")
        
        final_path = await process_bracket(
            bracket_path, 
            run_dir,  # Use run-specific directory
            anthropic_client, 
            model,
            test_mode=args.test,
            dry_run=args.dry_run,
            debug_level=args.debug,
            use_enhanced_analysis=use_enhanced_analysis
        )
        
        logger.info(f"Bracket processing complete")
        print(f"\nBracket prediction complete! Final bracket saved to: {final_path}")
        
        # Generate reports
        logger.info("Generating reports")
        report_path = generate_report(final_path, run_dir)
        html_path = generate_html_bracket(final_path, run_dir)
        
        # Print final paths
        print(f"Report generated at: {report_path}")
        print(f"HTML visualization at: {html_path}")
        
        # Create a symlink to the latest run in the parent directory
        latest_link = os.path.join(args.output, "latest")
        try:
            if os.path.exists(latest_link) and os.path.islink(latest_link):
                os.unlink(latest_link)
            os.symlink(run_dir, latest_link, target_is_directory=True)
            logger.debug(f"Created 'latest' symlink to {run_dir}")
        except Exception as e:
            logger.warning(f"Could not create 'latest' symlink: {str(e)}")
        
        print(f"\nAll results saved to: {run_dir}")
        print(f"Access via 'latest' link: {latest_link}")
        
    except Exception as e:
        logger.error(f"Error processing bracket: {str(e)}", exc_info=True)
        print(f"Error: {str(e)}. See log file for details.")

if __name__ == "__main__":
    asyncio.run(main())