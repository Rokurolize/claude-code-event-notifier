#\!/bin/bash
set -e

events=("PreToolUse" "PostToolUse" "Notification" "Stop" "SubagentStop")
test_data='{"session_id":"test123","tool_name":"Bash","tool_input":{"command":"echo test"},"tool_response":{"stdout":"test"},"message":"Test notification"}'

for event in "${events[@]}"; do
    echo "Creating golden master for $event..."
    echo "$test_data"  < /dev/null |  CLAUDE_HOOK_EVENT="$event" uv run --no-sync --python 3.13 python src/discord_notifier.py 2>&1 > "tests/golden_master/${event}.txt" || true
done

echo "✅ Golden master files created"
