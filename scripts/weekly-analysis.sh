#!/bin/bash
# =============================================================================
# Weekly Learning Analysis
# Analyzes task logs and generates insights for AGENT_WISDOM.md
# Run: every Sunday at 23:00 JST (cron) or manually
# =============================================================================
set -e

LOG_DIR="/opt/shared/task-log"
WISDOM_FILE="/opt/shared/AGENT_WISDOM.md"
REPORT_DIR="/opt/shared/reports"
DATE=$(date +%Y-%m-%d)
REPORT_FILE="${REPORT_DIR}/${DATE}_weekly-learning-analysis.md"

echo "=== Weekly Learning Analysis: ${DATE} ==="

# Count logs from the past 7 days
RECENT_LOGS=$(find "${LOG_DIR}" -name "*.md" -not -name "HOW_TO_LOG.md" -mtime -7 2>/dev/null | wc -l)
TOTAL_LOGS=$(find "${LOG_DIR}" -name "*.md" -not -name "HOW_TO_LOG.md" 2>/dev/null | wc -l)

# Count successes and failures
SUCCESS_COUNT=0
FAILURE_COUNT=0
PARTIAL_COUNT=0

for log in $(find "${LOG_DIR}" -name "*.md" -not -name "HOW_TO_LOG.md" -mtime -7 2>/dev/null); do
    if grep -qi "result: success" "$log" 2>/dev/null; then
        SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
    elif grep -qi "result: failure" "$log" 2>/dev/null; then
        FAILURE_COUNT=$((FAILURE_COUNT + 1))
    elif grep -qi "result: partial" "$log" 2>/dev/null; then
        PARTIAL_COUNT=$((PARTIAL_COUNT + 1))
    fi
done

echo ""
echo "--- Generating Report ---"

cat > "${REPORT_FILE}" << REPORT
# Weekly Learning Analysis - ${DATE}

## Summary
- Logs this week: ${RECENT_LOGS}
- Total logs: ${TOTAL_LOGS}
- Success: ${SUCCESS_COUNT} | Partial: ${PARTIAL_COUNT} | Failure: ${FAILURE_COUNT}
REPORT

# Calculate success rate
if [ "$RECENT_LOGS" -gt 0 ]; then
    RATE=$(( (SUCCESS_COUNT * 100) / RECENT_LOGS ))
    echo "- Success rate: ${RATE}%" >> "${REPORT_FILE}"
else
    echo "- Success rate: N/A (no logs)" >> "${REPORT_FILE}"
fi

# Append failure details
echo "" >> "${REPORT_FILE}"
echo "## Failures This Week" >> "${REPORT_FILE}"

for log in $(find "${LOG_DIR}" -name "*.md" -not -name "HOW_TO_LOG.md" -mtime -7 2>/dev/null); do
    if grep -qi "result: failure\|result: partial" "$log" 2>/dev/null; then
        echo "### $(basename "$log")" >> "${REPORT_FILE}"
        grep -A 5 "What didn" "$log" >> "${REPORT_FILE}" 2>/dev/null || true
        echo "" >> "${REPORT_FILE}"
    fi
done

# Append new knowledge
echo "## New Knowledge Gained" >> "${REPORT_FILE}"
for log in $(find "${LOG_DIR}" -name "*.md" -not -name "HOW_TO_LOG.md" -mtime -7 2>/dev/null); do
    knowledge=$(grep -A 3 "New knowledge" "$log" 2>/dev/null | grep "^- " || true)
    if [ -n "$knowledge" ]; then
        echo "From $(basename "$log"):" >> "${REPORT_FILE}"
        echo "$knowledge" >> "${REPORT_FILE}"
        echo "" >> "${REPORT_FILE}"
    fi
done

echo "" >> "${REPORT_FILE}"
echo "## Action Items for Neo" >> "${REPORT_FILE}"
echo "1. Review failures above and add lessons to AGENT_WISDOM.md" >> "${REPORT_FILE}"
echo "2. Update KNOWN_MISTAKES.md if any new patterns found" >> "${REPORT_FILE}"
echo "3. Check if any success patterns should be documented as best practices" >> "${REPORT_FILE}"
echo "4. Search externally for solutions to recurring problems" >> "${REPORT_FILE}"

echo ""
echo "Report saved to: ${REPORT_FILE}"
echo "Neo should read this report and update AGENT_WISDOM.md accordingly."
