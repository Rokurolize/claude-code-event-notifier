#!/usr/bin/env python3
"""
Discord Authentication Troubleshooting Script

This script tests Discord webhook and bot API authentication with proper headers
to diagnose and fix 403 Forbidden errors (error code 1010).

The error code 1010 indicates Cloudflare protection is blocking requests due to
missing or invalid User-Agent headers.
"""

import json
import logging
import os
import sys
import traceback
import urllib.request
import urllib.error
import urllib.parse
from datetime import datetime
from pathlib import Path
import time
import ssl


# Configure logging
def setup_logging():
    """Set up comprehensive logging to file and console."""
    log_file = Path("/home/ubuntu/human-in-the-loop/discord_auth_debug.log")

    # Create formatter
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s"
    )

    # File handler
    file_handler = logging.FileHandler(log_file, mode="a")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)

    # Configure root logger
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger


# Global logger
logger = setup_logging()


def load_discord_config():
    """Load Discord configuration from .env.discord file."""
    logger.info("Loading Discord configuration...")
    config = {}

    env_file = Path("/home/ubuntu/.claude/hooks/.env.discord")
    if not env_file.exists():
        logger.error(f"Configuration file not found: {env_file}")
        return None

    try:
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if "=" in line and not line.startswith("#"):
                    key, value = line.split("=", 1)
                    # Remove quotes if present
                    value = value.strip('"').strip("'")
                    config[key] = value
                    logger.debug(f"Loaded {key}")

        required_keys = ["DISCORD_WEBHOOK_URL", "DISCORD_TOKEN", "DISCORD_CHANNEL_ID"]
        for key in required_keys:
            if key not in config:
                logger.warning(f"Missing configuration: {key}")

        return config
    except Exception as e:
        logger.error(f"Error loading config: {e}")
        logger.debug(traceback.format_exc())
        return None


def create_test_embed():
    """Create a test embed message."""
    return {
        "embeds": [
            {
                "title": "🔧 Discord Authentication Test",
                "description": f"Testing at {datetime.now().isoformat()}",
                "color": 0x00FF00,  # Green
                "fields": [
                    {
                        "name": "Test Type",
                        "value": "Authentication Troubleshooting",
                        "inline": True,
                    },
                    {
                        "name": "User-Agent",
                        "value": "Properly configured",
                        "inline": True,
                    },
                ],
                "footer": {"text": "discord_auth_troubleshoot.py"},
                "timestamp": datetime.now().isoformat(),
            }
        ]
    }


class HTTPDebugHandler(urllib.request.HTTPHandler):
    """Custom HTTP handler for debugging requests."""

    def http_open(self, req):
        logger.debug(f"Request URL: {req.full_url}")
        logger.debug(f"Request Method: {req.get_method()}")
        logger.debug(f"Request Headers: {dict(req.headers)}")
        if req.data:
            logger.debug(f"Request Body: {req.data.decode('utf-8', errors='ignore')}")
        return super().http_open(req)


class HTTPSDebugHandler(urllib.request.HTTPSHandler):
    """Custom HTTPS handler for debugging requests."""

    def https_open(self, req):
        logger.debug(f"HTTPS Request URL: {req.full_url}")
        logger.debug(f"HTTPS Request Method: {req.get_method()}")
        logger.debug(f"HTTPS Request Headers: {dict(req.headers)}")
        if req.data:
            logger.debug(
                f"HTTPS Request Body: {req.data.decode('utf-8', errors='ignore')}"
            )
        return super().https_open(req)


def test_webhook_with_headers(webhook_url, message_data):
    """Test webhook with proper headers and detailed logging."""
    logger.info("=" * 60)
    logger.info("Testing Discord Webhook with Enhanced Headers")
    logger.info("=" * 60)

    try:
        # Prepare request data
        data = json.dumps(message_data).encode("utf-8")

        # Create request with proper headers
        req = urllib.request.Request(
            webhook_url,
            data=data,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "DiscordBot (https://github.com/human-in-the-loop, 1.0)",
                "Accept": "application/json",
                "Accept-Language": "en-US,en;q=0.9",
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            },
        )

        # Log request details
        logger.info(f"Request URL: {webhook_url[:50]}...")
        logger.debug(f"Full URL: {webhook_url}")
        logger.debug(f"Request Headers: {dict(req.headers)}")
        logger.debug(f"Request Body: {json.dumps(message_data, indent=2)}")

        # Create opener with debug handlers
        opener = urllib.request.build_opener(HTTPDebugHandler(), HTTPSDebugHandler())

        # Send request
        start_time = time.time()
        with opener.open(req, timeout=10) as response:
            elapsed_time = time.time() - start_time

            # Log response details
            logger.info(f"✅ Success! Status: {response.status}")
            logger.info(f"Response Time: {elapsed_time:.2f}s")
            logger.debug(f"Response Headers: {dict(response.headers)}")

            # Read response body
            response_body = response.read().decode("utf-8", errors="ignore")
            if response_body:
                logger.debug(f"Response Body: {response_body}")

            return True, f"Success: {response.status}"

    except urllib.error.HTTPError as e:
        logger.error(f"❌ HTTP Error {e.code}: {e.reason}")

        # Log detailed error information
        logger.debug(f"Error Headers: {dict(e.headers)}")
        try:
            error_body = e.read().decode("utf-8", errors="ignore")
            logger.error(f"Error Response: {error_body}")

            # Try to parse Cloudflare error
            if "error code:" in error_body:
                error_code = error_body.split("error code:")[1].strip().split()[0]
                logger.error(f"Cloudflare Error Code: {error_code}")

                if error_code == "1010":
                    logger.error(
                        "Error 1010: Access denied by Cloudflare - Browser signature banned"
                    )
                    logger.info(
                        "This indicates the User-Agent header is being rejected"
                    )

        except Exception as parse_error:
            logger.debug(f"Error parsing response: {parse_error}")

        return False, f"HTTP {e.code}: {e.reason}"

    except urllib.error.URLError as e:
        logger.error(f"❌ URL Error: {e.reason}")
        return False, f"URL Error: {e.reason}"

    except Exception as e:
        logger.error(f"❌ Unexpected Error: {type(e).__name__}: {e}")
        logger.debug(traceback.format_exc())
        return False, f"Error: {type(e).__name__}: {e}"


def test_bot_api_with_headers(bot_token, channel_id, message_data):
    """Test bot API with proper headers and detailed logging."""
    logger.info("=" * 60)
    logger.info("Testing Discord Bot API with Enhanced Headers")
    logger.info("=" * 60)

    try:
        # Discord API endpoint
        url = f"https://discord.com/api/v10/channels/{channel_id}/messages"

        # Prepare request data
        data = json.dumps(message_data).encode("utf-8")

        # Create request with proper headers
        req = urllib.request.Request(
            url,
            data=data,
            headers={
                "Authorization": f"Bot {bot_token}",
                "Content-Type": "application/json",
                "User-Agent": "DiscordBot (https://github.com/human-in-the-loop, 1.0)",
                "Accept": "application/json",
                "Accept-Language": "en-US,en;q=0.9",
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            },
        )

        # Log request details
        logger.info(f"Request URL: {url}")
        logger.debug(f"Bot Token: {bot_token[:20]}...")
        logger.debug(f"Channel ID: {channel_id}")
        logger.debug(f"Request Headers: {dict(req.headers)}")
        logger.debug(f"Request Body: {json.dumps(message_data, indent=2)}")

        # Create opener with debug handlers
        opener = urllib.request.build_opener(HTTPDebugHandler(), HTTPSDebugHandler())

        # Send request
        start_time = time.time()
        with opener.open(req, timeout=10) as response:
            elapsed_time = time.time() - start_time

            # Log response details
            logger.info(f"✅ Success! Status: {response.status}")
            logger.info(f"Response Time: {elapsed_time:.2f}s")
            logger.debug(f"Response Headers: {dict(response.headers)}")

            # Read response body
            response_body = response.read().decode("utf-8", errors="ignore")
            if response_body:
                logger.debug(f"Response Body: {response_body}")
                # Parse message ID if available
                try:
                    response_json = json.loads(response_body)
                    if "id" in response_json:
                        logger.info(f"Message ID: {response_json['id']}")
                except:
                    pass

            return True, f"Success: {response.status}"

    except urllib.error.HTTPError as e:
        logger.error(f"❌ HTTP Error {e.code}: {e.reason}")

        # Log detailed error information
        logger.debug(f"Error Headers: {dict(e.headers)}")
        try:
            error_body = e.read().decode("utf-8", errors="ignore")
            logger.error(f"Error Response: {error_body}")

            # Parse Discord API error
            try:
                error_json = json.loads(error_body)
                if "code" in error_json:
                    logger.error(f"Discord Error Code: {error_json['code']}")
                if "message" in error_json:
                    logger.error(f"Discord Error Message: {error_json['message']}")
            except:
                # Check for Cloudflare error
                if "error code:" in error_body:
                    error_code = error_body.split("error code:")[1].strip().split()[0]
                    logger.error(f"Cloudflare Error Code: {error_code}")

                    if error_code == "1010":
                        logger.error(
                            "Error 1010: Access denied by Cloudflare - Browser signature banned"
                        )

        except Exception as parse_error:
            logger.debug(f"Error parsing response: {parse_error}")

        return False, f"HTTP {e.code}: {e.reason}"

    except Exception as e:
        logger.error(f"❌ Unexpected Error: {type(e).__name__}: {e}")
        logger.debug(traceback.format_exc())
        return False, f"Error: {type(e).__name__}: {e}"


def test_different_user_agents(config, message_data):
    """Test different User-Agent strings to find working configuration."""
    logger.info("=" * 60)
    logger.info("Testing Different User-Agent Headers")
    logger.info("=" * 60)

    user_agents = [
        "DiscordBot (https://github.com/human-in-the-loop, 1.0)",
        "DiscordBot (https://example.com, 1.0)",
        "Mozilla/5.0 (compatible; DiscordBot/1.0; +https://github.com/human-in-the-loop)",
        "Python/3.9 discord.py/2.0",
        "Claude-Code-Hooks/1.0",
        "DiscordWebhook/1.0",
    ]

    results = []

    for ua in user_agents:
        logger.info(f"\nTesting User-Agent: {ua}")

        # Test webhook
        if config.get("DISCORD_WEBHOOK_URL"):
            try:
                data = json.dumps(message_data).encode("utf-8")
                req = urllib.request.Request(
                    config["DISCORD_WEBHOOK_URL"],
                    data=data,
                    headers={"Content-Type": "application/json", "User-Agent": ua},
                )

                with urllib.request.urlopen(req, timeout=5) as response:
                    logger.info(f"  ✅ Webhook Success with: {ua}")
                    results.append((ua, "webhook", True))

            except urllib.error.HTTPError as e:
                logger.error(f"  ❌ Webhook Failed: {e.code}")
                results.append((ua, "webhook", False))
            except Exception as e:
                logger.error(f"  ❌ Webhook Error: {type(e).__name__}")
                results.append((ua, "webhook", False))

    return results


def generate_summary_report(webhook_result, bot_result, config):
    """Generate a summary report of test results."""
    logger.info("\n" + "=" * 60)
    logger.info("SUMMARY REPORT")
    logger.info("=" * 60)

    logger.info(f"Test Time: {datetime.now()}")
    logger.info(f"Configuration Source: /home/ubuntu/.claude/hooks/.env.discord")

    logger.info("\nTest Results:")
    logger.info(
        f"  Webhook Test: {'✅ PASSED' if webhook_result[0] else '❌ FAILED'} - {webhook_result[1]}"
    )
    logger.info(
        f"  Bot API Test: {'✅ PASSED' if bot_result[0] else '❌ FAILED'} - {bot_result[1]}"
    )

    logger.info("\nConfiguration:")
    logger.info(
        f"  Webhook URL: {'Configured' if config.get('DISCORD_WEBHOOK_URL') else 'Not configured'}"
    )
    logger.info(
        f"  Bot Token: {'Configured' if config.get('DISCORD_TOKEN') else 'Not configured'}"
    )
    logger.info(f"  Channel ID: {config.get('DISCORD_CHANNEL_ID', 'Not configured')}")

    logger.info("\nRecommendations:")
    if not webhook_result[0] and not bot_result[0]:
        logger.info("  1. Both methods failed - likely a Cloudflare/User-Agent issue")
        logger.info("  2. Consider using discord.py library as alternative")
        logger.info("  3. Check if webhook/token are valid and not expired")
        logger.info("  4. Verify bot has proper permissions in the Discord channel")
    elif webhook_result[0] and not bot_result[0]:
        logger.info("  1. Webhook works but bot API fails")
        logger.info("  2. Check bot token validity")
        logger.info("  3. Verify bot is in the server and has permissions")
    elif not webhook_result[0] and bot_result[0]:
        logger.info("  1. Bot API works but webhook fails")
        logger.info("  2. Webhook might be deleted or invalid")
        logger.info("  3. Use bot API method instead of webhook")
    else:
        logger.info("  ✅ All tests passed! Discord integration is working correctly.")

    logger.info("\nLog file: /home/ubuntu/human-in-the-loop/discord_auth_debug.log")
    logger.info("=" * 60)


def main():
    """Main function to run all tests."""
    logger.info("Starting Discord Authentication Troubleshooting")
    logger.info(f"Script Version: 1.0")
    logger.info(f"Python Version: {sys.version}")

    # Load configuration
    config = load_discord_config()
    if not config:
        logger.error("Failed to load configuration. Exiting.")
        return 1

    # Create test message
    message_data = create_test_embed()

    # Test webhook
    webhook_result = (False, "Not tested")
    if config.get("DISCORD_WEBHOOK_URL"):
        webhook_result = test_webhook_with_headers(
            config["DISCORD_WEBHOOK_URL"], message_data
        )
    else:
        logger.warning("No webhook URL configured, skipping webhook test")

    # Small delay between tests
    time.sleep(1)

    # Test bot API
    bot_result = (False, "Not tested")
    if config.get("DISCORD_TOKEN") and config.get("DISCORD_CHANNEL_ID"):
        # For bot API, we need a simpler message format
        bot_message = {
            "content": "🔧 **Discord Bot API Test**\nTesting authentication with proper headers.",
            "embeds": message_data["embeds"],
        }
        bot_result = test_bot_api_with_headers(
            config["DISCORD_TOKEN"], config["DISCORD_CHANNEL_ID"], bot_message
        )
    else:
        logger.warning("No bot token or channel ID configured, skipping bot API test")

    # Test different user agents if both methods failed
    if not webhook_result[0] and not bot_result[0]:
        logger.info("\nBoth methods failed. Testing different User-Agent headers...")
        ua_results = test_different_user_agents(config, message_data)

        logger.info("\nUser-Agent Test Results:")
        for ua, method, success in ua_results:
            logger.info(f"  {ua}: {'✅' if success else '❌'}")

    # Generate summary report
    generate_summary_report(webhook_result, bot_result, config)

    return 0 if (webhook_result[0] or bot_result[0]) else 1


if __name__ == "__main__":
    sys.exit(main())
