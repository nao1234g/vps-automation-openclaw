#!/bin/bash
# Neo → Jarvis Bridge Script
# Checks for new tasks from Neo and sends them to Jarvis

set -e

NEW_DIR="/opt/shared/neo-tasks/new"
PROCESSING_DIR="/opt/shared/neo-tasks/processing"
DONE_DIR="/opt/shared/neo-tasks/done"
LOG_FILE="/opt/shared/neo-tasks/bridge.log"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Checking for new tasks..." >> "$LOG_FILE"

# Check for new task files
for task_file in "$NEW_DIR"/*.md; do
  # Skip if no files found
  [ -e "$task_file" ] || continue

  filename=$(basename "$task_file")
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] Found task: $filename" >> "$LOG_FILE"

  # Move to processing
  mv "$task_file" "$PROCESSING_DIR/$filename"

  # Read task content
  task_content=$(cat "$PROCESSING_DIR/$filename")

  # Send to Jarvis via OpenClaw
  docker exec openclaw-agent openclaw agent \
    --agent jarvis-cso \
    --message "$task_content" \
    --deliver \
    --channel telegram \
    --json > "$DONE_DIR/result_${filename%.md}_$(date +%Y%m%d_%H%M%S).json" 2>&1

  # Move task to done
  mv "$PROCESSING_DIR/$filename" "$DONE_DIR/$filename"

  echo "[$(date '+%Y-%m-%d %H:%M:%S')] Task completed: $filename" >> "$LOG_FILE"
done

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Check completed" >> "$LOG_FILE"
