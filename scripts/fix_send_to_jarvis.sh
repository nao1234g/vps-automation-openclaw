#!/bin/bash
# Fix send-to-jarvis.sh script

cat > /opt/claude-code-telegram/send-to-jarvis.sh << 'SCRIPT_END'
#!/bin/bash
# Neo → Jarvis Bridge
# Usage: ./send-to-jarvis.sh 'メッセージ内容'
# Usage: ./send-to-jarvis.sh --agent alice-research 'メッセージ'

set -e

AGENT='jarvis-cso'
DELIVER='--deliver'
MESSAGE=''

# Parse optional --agent flag
while [[ $# -gt 0 ]]; do
  case $1 in
    --agent) AGENT="$2"; shift 2;;
    --no-deliver) DELIVER=''; shift;;
    *) MESSAGE="$1"; shift;;
  esac
done

if [ -z "$MESSAGE" ]; then
  echo 'Usage: send-to-jarvis.sh [--agent agent-id] "message"'
  echo 'Agents: jarvis-cso, alice-research, codex-developer, pixel-designer,'
  echo '        luna-writer, scout-data, guard-security, hawk-xresearch'
  exit 1
fi

docker exec openclaw-agent openclaw agent \
  --agent "$AGENT" \
  --message "$MESSAGE" \
  --channel telegram \
  $DELIVER \
  --json 2>&1
SCRIPT_END

chmod +x /opt/claude-code-telegram/send-to-jarvis.sh
echo "Fixed send-to-jarvis.sh"
