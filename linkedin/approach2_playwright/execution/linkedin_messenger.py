"""
LinkedIn Messenger
Sends personalized messages and connection requests via browser automation
"""

import json
from pathlib import Path
from typing import Optional, List
from datetime import datetime
from playwright.sync_api import Page, BrowserContext

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from shared.types import LinkedInProfile, ContentDraft, ApproachType
from .linkedin_browser_auth import get_authenticated_context
from .anti_detection import AntiDetection, RateLimiter

BASE_DIR = Path(__file__).parent.parent.parent
OUTPUT_DIR = BASE_DIR / ".tmp" / "approach2"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


class LinkedInMessenger:
    """
    Sends messages and connection requests on LinkedIn.
    """

    def __init__(
        self,
        context: BrowserContext,
        anti_detection: AntiDetection,
        rate_limiter: RateLimiter
    ):
        self.context = context
        self.anti_detection = anti_detection
        self.rate_limiter = rate_limiter

    def send_connection_request(
        self,
        profile_url: str,
        note: Optional[str] = None
    ) -> dict:
        """
        Send a connection request with optional note.

        Args:
            profile_url: Profile URL to connect with
            note: Optional personalized note (max 300 chars)

        Returns:
            Dict with success status
        """
        if not self.rate_limiter.can_send_message():
            return {
                "success": False,
                "error": "Daily message limit reached"
            }

        page = self.context.new_page()
        result = {
            "success": False,
            "profile_url": profile_url,
            "error": None,
            "sent_at": None
        }

        try:
            page.goto(profile_url, wait_until="domcontentloaded")
            self.anti_detection.long_wait()

            # Scroll to ensure page is loaded, then back to top
            page.mouse.wheel(0, 500)
            self.anti_detection.short_wait()
            page.evaluate("window.scrollTo(0, 0)")
            self.anti_detection.short_wait()

            # Check for pending first
            pending_btn = page.locator('button:has-text("Pending")')
            if pending_btn.count() > 0:
                result["error"] = "Connection request already pending"
                return result

            # Check if already connected
            message_btn = page.locator('button:has-text("Message")')
            if message_btn.count() > 0 and message_btn.first.is_visible():
                result["error"] = "Already connected"
                return result

            # Find Connect button - prefer visible ones in main content area
            connect_selectors = [
                # Main profile buttons area
                '.pv-top-card-v2-ctas button:has-text("Connect")',
                'section.artdeco-card button:has-text("Connect")',
                # Aria-label based
                'main button[aria-label*="Invite"][aria-label*="connect"]',
                'button[aria-label*="Invite"][aria-label*="connect"]',
                # Text based
                'button:has-text("Connect"):not(:has-text("Pending"))',
            ]

            connect_btn = None
            for selector in connect_selectors:
                try:
                    btn = page.locator(selector)
                    if btn.count() > 0:
                        # Find a visible button
                        for i in range(min(btn.count(), 3)):
                            try:
                                if btn.nth(i).is_visible():
                                    connect_btn = btn.nth(i)
                                    break
                            except:
                                continue
                        if connect_btn:
                            break
                except:
                    continue

            # If no visible button found, try force-clicking the first one
            if not connect_btn:
                for selector in connect_selectors:
                    try:
                        btn = page.locator(selector)
                        if btn.count() > 0:
                            connect_btn = btn.first
                            break
                    except:
                        continue

            if not connect_btn:
                result["error"] = "Connect button not found"
                return result

            # Click with force if needed
            try:
                connect_btn.scroll_into_view_if_needed()
                self.anti_detection.short_wait()
                connect_btn.click()
            except:
                # Force click as fallback
                connect_btn.click(force=True)
            self.anti_detection.medium_wait()

            # Handle connection modal
            if note:
                # Click "Add a note" button
                add_note_btn = page.locator(
                    'button[aria-label*="Add a note"], '
                    'button:has-text("Add a note")'
                )
                if add_note_btn.count() > 0:
                    add_note_btn.first.click()
                    self.anti_detection.short_wait()

                    # Type the note
                    note_input = page.locator(
                        'textarea[name="message"], '
                        '#custom-message, '
                        'textarea[placeholder*="Add a note"]'
                    )
                    if note_input.count() > 0:
                        # Truncate note to 300 chars
                        truncated_note = note[:300]
                        note_input.first.fill(truncated_note)
                        self.anti_detection.short_wait()

            # Click Send/Done button
            send_btn = page.locator(
                'button[aria-label*="Send"], '
                'button:has-text("Send")'
            )
            if send_btn.count() > 0:
                send_btn.first.click()
                self.anti_detection.medium_wait()

                result["success"] = True
                result["sent_at"] = datetime.now().isoformat()
                self.rate_limiter.record_message()

        except Exception as e:
            result["error"] = str(e)
        finally:
            page.close()

        return result

    def send_message(
        self,
        profile_url: str,
        message: str
    ) -> dict:
        """
        Send a direct message to an existing connection.

        Args:
            profile_url: Profile URL of the connection
            message: Message content

        Returns:
            Dict with success status
        """
        if not self.rate_limiter.can_send_message():
            return {
                "success": False,
                "error": "Daily message limit reached"
            }

        page = self.context.new_page()
        result = {
            "success": False,
            "profile_url": profile_url,
            "error": None,
            "sent_at": None
        }

        try:
            page.goto(profile_url, wait_until="domcontentloaded")
            self.anti_detection.long_wait()

            # Scroll down to make sticky header appear
            page.mouse.wheel(0, 800)
            self.anti_detection.medium_wait()

            # Find Message button
            message_btns = page.locator('button[aria-label*="Message"]')

            if message_btns.count() == 0:
                result["error"] = "Message button not found - may not be connected"
                return result

            # Click with force=True (handles sticky header visibility)
            message_btns.first.click(force=True)

            self.anti_detection.long_wait()

            # Wait for message modal/overlay
            msg_input = page.locator(
                '.msg-form__contenteditable, '
                '[contenteditable="true"][data-artdeco-is-focused], '
                'div[role="textbox"]'
            )

            if msg_input.count() == 0:
                result["error"] = "Message input not found"
                return result

            # Type message
            msg_input.first.click()
            self.anti_detection.short_wait()

            for char in message:
                msg_input.first.type(char, delay=30)

            self.anti_detection.short_wait()

            # Click Send
            send_btn = page.locator(
                'button[type="submit"], '
                'button.msg-form__send-button, '
                'button[aria-label="Send"]'
            )
            if send_btn.count() > 0:
                send_btn.first.click()
                self.anti_detection.medium_wait()

                result["success"] = True
                result["sent_at"] = datetime.now().isoformat()
                self.rate_limiter.record_message()

        except Exception as e:
            result["error"] = str(e)
        finally:
            page.close()

        return result

    def send_message_from_draft(
        self,
        draft: ContentDraft
    ) -> dict:
        """
        Send a message from a ContentDraft.

        Args:
            draft: ContentDraft with recipient and message

        Returns:
            Dict with success status
        """
        if not draft.recipient_profile:
            return {"success": False, "error": "No recipient in draft"}

        return self.send_message(
            profile_url=draft.recipient_profile.profile_url,
            message=draft.body
        )

    def send_bulk_connection_requests(
        self,
        profiles: List[LinkedInProfile],
        note_template: Optional[str] = None,
        max_requests: int = 25
    ) -> List[dict]:
        """
        Send connection requests to multiple profiles.

        Args:
            profiles: List of profiles to connect with
            note_template: Note template with {name} placeholder
            max_requests: Maximum requests to send

        Returns:
            List of results for each request
        """
        results = []

        for i, profile in enumerate(profiles[:max_requests]):
            if not self.rate_limiter.can_send_message():
                print("Daily message limit reached")
                break

            if self.anti_detection.should_take_break():
                print("Taking a break...")
                self.anti_detection.long_wait()
                self.anti_detection.long_wait()

            # Personalize note if template provided
            note = None
            if note_template:
                first_name = profile.name.split()[0] if profile.name else "there"
                note = note_template.replace("{name}", first_name)
                note = note.replace("{company}", profile.company or "your company")
                note = note.replace("{title}", profile.title or "your role")

            print(f"Sending connection request {i + 1}/{len(profiles)}: {profile.name}")
            result = self.send_connection_request(profile.profile_url, note)
            result["profile_name"] = profile.name
            results.append(result)

            self.anti_detection.long_wait()

        return results


def send_connection_request(
    profile_url: str,
    note: Optional[str] = None,
    headless: bool = False
) -> dict:
    """
    Main entry point for sending a connection request.

    Args:
        profile_url: Profile URL
        note: Optional personalized note
        headless: Run browser in headless mode

    Returns:
        Dict with success status
    """
    playwright, browser, context, auth = get_authenticated_context(headless)

    try:
        messenger = LinkedInMessenger(
            context=context,
            anti_detection=auth.anti_detection,
            rate_limiter=auth.rate_limiter
        )

        result = messenger.send_connection_request(profile_url, note)

        # Log the action
        _log_message_action("connection_request", profile_url, result)

        return result

    finally:
        auth.close()


def send_message(
    profile_url: str,
    message: str,
    headless: bool = False
) -> dict:
    """
    Main entry point for sending a direct message.

    Args:
        profile_url: Profile URL
        message: Message content
        headless: Run browser in headless mode

    Returns:
        Dict with success status
    """
    playwright, browser, context, auth = get_authenticated_context(headless)

    try:
        messenger = LinkedInMessenger(
            context=context,
            anti_detection=auth.anti_detection,
            rate_limiter=auth.rate_limiter
        )

        result = messenger.send_message(profile_url, message)

        # Log the action
        _log_message_action("direct_message", profile_url, result)

        return result

    finally:
        auth.close()


def _log_message_action(action_type: str, profile_url: str, result: dict):
    """Log message action to file"""
    log_file = OUTPUT_DIR / "message_log.json"
    log_entries = []
    if log_file.exists():
        with open(log_file) as f:
            log_entries = json.load(f)

    log_entries.append({
        "action_type": action_type,
        "profile_url": profile_url,
        "result": result,
        "timestamp": datetime.now().isoformat()
    })

    with open(log_file, "w") as f:
        json.dump(log_entries, f, indent=2)


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage:")
        print("  Send connection: python linkedin_messenger.py connect <profile_url> [note]")
        print("  Send message: python linkedin_messenger.py message <profile_url> <message>")
        sys.exit(1)

    action = sys.argv[1]

    if action == "connect" and len(sys.argv) >= 3:
        profile_url = sys.argv[2]
        note = sys.argv[3] if len(sys.argv) > 3 else None
        result = send_connection_request(profile_url, note, headless=False)
        print(f"Result: {result}")

    elif action == "message" and len(sys.argv) >= 4:
        profile_url = sys.argv[2]
        message = " ".join(sys.argv[3:])
        result = send_message(profile_url, message, headless=False)
        print(f"Result: {result}")

    else:
        print("Invalid arguments")
