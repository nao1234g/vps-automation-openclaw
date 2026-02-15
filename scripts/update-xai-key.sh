#!/bin/bash
# Update xAI API Key in OpenClaw
# Usage: ./update-xai-key.sh

set -e

NEW_XAI_KEY="${XAI_API_KEY:?Set XAI_API_KEY environment variable first}"

echo "🔑 Updating xAI API Key in OpenClaw..."

# Update .env file in OpenClaw container
docker exec openclaw-agent sh -c "
  if grep -q '^XAI_API_KEY=' /home/appuser/.openclaw/.env; then
    sed -i 's|^XAI_API_KEY=.*|XAI_API_KEY=$NEW_XAI_KEY|' /home/appuser/.openclaw/.env
    echo '✅ Updated existing XAI_API_KEY'
  else
    echo 'XAI_API_KEY=$NEW_XAI_KEY' >> /home/appuser/.openclaw/.env
    echo '✅ Added new XAI_API_KEY'
  fi
"

# Verify the update
echo ""
echo "📝 Verifying update..."
docker exec openclaw-agent sh -c "grep XAI_API_KEY /home/appuser/.openclaw/.env | sed 's/xai-[a-zA-Z0-9]*/xai-***MASKED***/'"

echo ""
echo "✅ xAI API Key updated successfully!"
echo ""
echo "Next steps:"
echo "1. Restart OpenClaw: docker restart openclaw-agent"
echo "2. Update CodeX model to o4-mini"
