#!/bin/bash
# View Neo's conversation history from VPS

VPS_HOST="163.44.124.123"
SSH_KEY="~/.ssh/id_ed25519"
SHARED_FILE="/opt/shared/neo_conversation_history.md"

echo "=== Neo (Claude Brain) Conversation History ==="
echo ""

# Fetch and display the conversation history
ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no root@"$VPS_HOST" "cat $SHARED_FILE" 2>/dev/null

if [ $? -ne 0 ]; then
    echo "[ERROR] Failed to fetch Neo's conversation history"
    exit 1
fi
