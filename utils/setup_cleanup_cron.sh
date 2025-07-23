#!/bin/bash
# Setup automatic cleanup cron job for Claude Code Event Notifier

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLEANUP_SCRIPT="$SCRIPT_DIR/cleanup_logs.py"

# Check if cleanup script exists
if [ ! -f "$CLEANUP_SCRIPT" ]; then
    echo "❌ Error: cleanup_logs.py not found!"
    exit 1
fi

# Create cron job (runs daily at 3:00 AM)
CRON_JOB="0 3 * * * /usr/bin/python3 $CLEANUP_SCRIPT > /dev/null 2>&1"

# Check if cron job already exists
if crontab -l 2>/dev/null | grep -q "$CLEANUP_SCRIPT"; then
    echo "✅ Cleanup cron job already exists"
else
    # Add cron job
    (crontab -l 2>/dev/null; echo "$CRON_JOB") | crontab -
    echo "✅ Added cleanup cron job (runs daily at 3:00 AM)"
fi

echo ""
echo "To view current cron jobs:"
echo "  crontab -l"
echo ""
echo "To remove the cleanup cron job:"
echo "  crontab -e  # then delete the line containing cleanup_logs.py"