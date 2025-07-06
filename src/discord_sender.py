#!/usr/bin/env python3
"""
Discord Sender for Claude Code Event Notifier

This module handles sending notifications to Discord via webhook or bot API.
"""

import json
import logging
import traceback
import urllib.request
import urllib.error
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class DiscordNotificationSender:
    """Handles sending notifications to Discord channels."""

    def __init__(
        self,
        webhook_url: Optional[str] = None,
        bot_token: Optional[str] = None,
        channel_id: Optional[str] = None,
    ):
        """
        Initialize the Discord notification sender.

        Args:
            webhook_url: Discord webhook URL (preferred method)
            bot_token: Discord bot token (fallback method)
            channel_id: Discord channel ID (required for bot method)
        """
        self.webhook_url = webhook_url
        self.bot_token = bot_token
        self.channel_id = channel_id

        # User agent header to comply with Discord's requirements
        self.user_agent = "ClaudeCodeEventNotifier/1.0 (https://github.com/user/claude-code-event-notifier)"

    def send_notification(self, message_data: Dict[str, Any]) -> bool:
        """
        Send a notification to Discord using available methods.

        Args:
            message_data: Discord message structure with embeds

        Returns:
            True if notification was sent successfully, False otherwise
        """
        success = False

        # Try webhook first (preferred method)
        if self.webhook_url:
            logger.info("Attempting to send via webhook...")
            success = self._send_webhook_notification(self.webhook_url, message_data)
            logger.info(f"Webhook result: {'success' if success else 'failed'}")

        # Fallback to bot API if webhook fails
        if not success and self.bot_token and self.channel_id:
            logger.info("Attempting to send via bot API...")
            success = self._send_bot_notification(
                self.bot_token, self.channel_id, message_data
            )
            logger.info(f"Bot API result: {'success' if success else 'failed'}")

        if not success:
            logger.error("Failed to send Discord notification via any method")

        return success

    def _send_webhook_notification(
        self, webhook_url: str, message_data: Dict[str, Any]
    ) -> bool:
        """
        Send message to Discord via webhook.

        Args:
            webhook_url: Discord webhook URL
            message_data: Message structure

        Returns:
            True if successful, False otherwise
        """
        logger.info(f"Sending to webhook: {webhook_url[:50]}...")
        logger.debug(f"Message data: {json.dumps(message_data, indent=2)}")

        try:
            data = json.dumps(message_data).encode("utf-8")

            headers = {
                "Content-Type": "application/json",
                "User-Agent": self.user_agent,
            }

            req = urllib.request.Request(webhook_url, data=data, headers=headers)

            with urllib.request.urlopen(req, timeout=10) as response:
                logger.info(f"Webhook response status: {response.status}")
                logger.debug(f"Response headers: {dict(response.headers)}")
                return response.status == 204

        except urllib.error.HTTPError as e:
            logger.error(f"HTTP Error {e.code}: {e.reason}")
            try:
                error_body = e.read().decode("utf-8", errors="ignore")
                logger.debug(f"Error response: {error_body}")

                # Parse Discord error response
                if error_body:
                    try:
                        error_data = json.loads(error_body)
                        logger.error(f"Discord error: {error_data}")
                    except json.JSONDecodeError:
                        logger.debug(f"Could not parse error response as JSON")
            except Exception:
                pass
            return False

        except Exception as e:
            logger.error(f"Webhook error: {type(e).__name__}: {e}")
            logger.debug(traceback.format_exc())
            return False

    def _send_bot_notification(
        self, bot_token: str, channel_id: str, message_data: Dict[str, Any]
    ) -> bool:
        """
        Send message to Discord via bot API.

        Args:
            bot_token: Discord bot token
            channel_id: Target channel ID
            message_data: Message structure

        Returns:
            True if successful, False otherwise
        """
        logger.info(f"Sending via bot API to channel: {channel_id}")
        logger.debug(f"Using bot token: {bot_token[:10]}...")

        try:
            url = f"https://discord.com/api/v10/channels/{channel_id}/messages"
            data = json.dumps(message_data).encode("utf-8")

            headers = {
                "Authorization": f"Bot {bot_token}",
                "Content-Type": "application/json",
                "User-Agent": self.user_agent,
            }

            req = urllib.request.Request(url, data=data, headers=headers)

            with urllib.request.urlopen(req, timeout=10) as response:
                logger.info(f"Bot API response status: {response.status}")
                response_data = response.read().decode("utf-8")
                logger.debug(f"Response data: {response_data}")
                return 200 <= response.status < 300

        except urllib.error.HTTPError as e:
            logger.error(f"HTTP Error {e.code}: {e.reason}")
            try:
                error_body = e.read().decode("utf-8", errors="ignore")
                logger.debug(f"Error response: {error_body}")

                # Parse Discord error response
                if error_body:
                    try:
                        error_data = json.loads(error_body)
                        logger.error(f"Discord error: {error_data}")

                        # Check for specific error codes
                        if error_data.get("code") == 50001:
                            logger.error("Bot lacks access to this channel")
                        elif error_data.get("code") == 50013:
                            logger.error("Bot lacks required permissions")
                        elif error_data.get("code") == 10003:
                            logger.error("Unknown channel - channel ID may be invalid")
                    except json.JSONDecodeError:
                        logger.debug(f"Could not parse error response as JSON")
            except Exception:
                pass
            return False

        except Exception as e:
            logger.error(f"Bot API error: {type(e).__name__}: {e}")
            logger.debug(traceback.format_exc())
            return False

    def test_connection(self) -> Dict[str, bool]:
        """
        Test Discord connections without sending a message.

        Returns:
            Dictionary with connection test results
        """
        results = {
            "webhook_available": bool(self.webhook_url),
            "bot_available": bool(self.bot_token and self.channel_id),
            "webhook_valid": False,
            "bot_valid": False,
        }

        # Test webhook with a simple GET request (should return 405)
        if self.webhook_url:
            try:
                req = urllib.request.Request(
                    self.webhook_url, headers={"User-Agent": self.user_agent}
                )
                urllib.request.urlopen(req, timeout=5)
            except urllib.error.HTTPError as e:
                # 405 Method Not Allowed is expected for GET on webhook
                results["webhook_valid"] = e.code == 405
            except Exception:
                pass

        # Test bot token by checking bot user info
        if self.bot_token:
            try:
                url = "https://discord.com/api/v10/users/@me"
                req = urllib.request.Request(
                    url,
                    headers={
                        "Authorization": f"Bot {self.bot_token}",
                        "User-Agent": self.user_agent,
                    },
                )
                with urllib.request.urlopen(req, timeout=5) as response:
                    results["bot_valid"] = response.status == 200
            except Exception:
                pass

        return results
