#!/bin/bash
# run_with_resume.sh
# Automatically runs or resumes a bracket prediction, handling checkpoints

# Default values
RUN_NAME="full_run_$(date +%Y%m%d)"
BRACKET="bracket.json"
OUTPUT_DIR="results"
EXTRA_ARGS=""

# Parse command line args
while [[ $# -gt 0 ]]; do
  case $1 in
    --name|--run-name)
      RUN_NAME="$2"
      shift 2
      ;;
    --bracket)
      BRACKET="$2"
      shift 2
      ;;
    --output)
      OUTPUT_DIR="$2"
      shift 2
      ;;
    --dry-run)
      EXTRA_ARGS="$EXTRA_ARGS --dry-run"
      shift
      ;;
    --test)
      EXTRA_ARGS="$EXTRA_ARGS --test"
      shift
      ;;
    --simple-analysis)
      EXTRA_ARGS="$EXTRA_ARGS --simple-analysis"
      shift
      ;;
    --debug|-d)
      EXTRA_ARGS="$EXTRA_ARGS --debug"
      shift
      ;;
    *)
      EXTRA_ARGS="$EXTRA_ARGS $1"
      shift
      ;;
  esac
done

echo "======================================================"
echo "  March Madness Bracket Prediction Resume Script"
echo "======================================================"
echo "Run name:   $RUN_NAME"
echo "Bracket:    $BRACKET"
echo "Output dir: $OUTPUT_DIR"
echo "Extra args: $EXTRA_ARGS"
echo "======================================================"

# Create the run directory if it doesn't exist
mkdir -p "$OUTPUT_DIR/$RUN_NAME"

# Check for latest checkpoint
LATEST_CHECKPOINT=$(find "$OUTPUT_DIR/$RUN_NAME" -name "bracket_checkpoint_*.json" | sort | tail -n 1)

if [ -n "$LATEST_CHECKPOINT" ]; then
  echo "Resuming from checkpoint: $LATEST_CHECKPOINT"
  
  # Run in background with nohup, capturing output
  nohup python main.py --bracket "$BRACKET" --output "$OUTPUT_DIR" --run-name "$RUN_NAME" --checkpoint "$LATEST_CHECKPOINT" $EXTRA_ARGS > "$OUTPUT_DIR/$RUN_NAME/run.log" 2>&1 &
  
  # Get the process ID
  PID=$!
  echo "Process started with PID: $PID"
  echo "PID $PID" > "$OUTPUT_DIR/$RUN_NAME/process.pid"
  echo "Logs will be written to: $OUTPUT_DIR/$RUN_NAME/run.log"
  echo "Follow logs with: tail -f $OUTPUT_DIR/$RUN_NAME/run.log"
else
  echo "Starting new run"
  
  # Run in background with nohup, capturing output
  nohup python main.py --bracket "$BRACKET" --output "$OUTPUT_DIR" --run-name "$RUN_NAME" $EXTRA_ARGS > "$OUTPUT_DIR/$RUN_NAME/run.log" 2>&1 &
  
  # Get the process ID
  PID=$!
  echo "Process started with PID: $PID"
  echo "PID $PID" > "$OUTPUT_DIR/$RUN_NAME/process.pid"
  echo "Logs will be written to: $OUTPUT_DIR/$RUN_NAME/run.log"
  echo "Follow logs with: tail -f $OUTPUT_DIR/$RUN_NAME/run.log"
fi

echo "======================================================"
echo "Run is executing in the background"
echo "To stop the process: kill $(cat $OUTPUT_DIR/$RUN_NAME/process.pid)"
echo "To resume later: just run this script again with the same run name"
echo "======================================================"