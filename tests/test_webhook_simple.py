#!/usr/bin/env python3
"""Simple webhook test"""

import json
import urllib.request

webhook_url = "https://discord.com/api/webhooks/1391303915022188544/2wVrqthPSKQmPceQ3rP-y-1rsbGX-hPFNml_H91ItYDKrHlUzTOWbkBOu7oMlCFDmK5z"

# Test with embeds
message = {
    "embeds": [
        {
            "title": "🎉 Webhook Test Successful!",
            "description": "Discord notifications are working correctly.",
            "color": 0x00FF00,
            "timestamp": "2025-07-06T14:00:00.000Z",
        }
    ]
}

try:
    data = json.dumps(message).encode("utf-8")
    req = urllib.request.Request(
        webhook_url, data=data, headers={"Content-Type": "application/json"}
    )

    with urllib.request.urlopen(req) as response:
        print(f"✅ Success! HTTP {response.status}")
        print("Check your Discord channel for the test message.")
except Exception as e:
    print(f"❌ Failed: {e}")
