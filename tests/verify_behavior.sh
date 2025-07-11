#\!/bin/bash
set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

events=("PreToolUse" "PostToolUse" "Notification" "Stop" "SubagentStop")
test_data='{"session_id":"test123","tool_name":"Bash","tool_input":{"command":"echo test"},"tool_response":{"stdout":"test"},"message":"Test notification"}'

failed=0

for event in "${events[@]}"; do
    echo -n "Testing $event... "
    echo "$test_data"  < /dev/null |  CLAUDE_HOOK_EVENT="$event" uv run --no-sync --python 3.13 python src/discord_notifier.py 2>&1 > "tests/current_${event}.txt" || true
    
    if diff -q "tests/golden_master/${event}.txt" "tests/current_${event}.txt" > /dev/null 2>&1; then
        echo -e "${GREEN}✅ PASS${NC}"
    else
        echo -e "${RED}❌ FAIL${NC}"
        echo "Differences:"
        diff "tests/golden_master/${event}.txt" "tests/current_${event}.txt" || true
        failed=$((failed + 1))
    fi
done

if [ $failed -eq 0 ]; then
    echo -e "\n${GREEN}✅ All behaviors preserved!${NC}"
    exit 0
else
    echo -e "\n${RED}❌ $failed tests failed${NC}"
    exit 1
fi
