"""
LinkedIn Browser Authentication
Handles login and session persistence for LinkedIn via Playwright
"""

import os
import json
from pathlib import Path
from typing import Tuple, Optional
from playwright.sync_api import sync_playwright, Browser, BrowserContext, Page
from dotenv import load_dotenv

from .anti_detection import AntiDetection, RateLimiter

# Load approach-specific env if exists, fallback to main .env
APPROACH_DIR = Path(__file__).parent.parent
BASE_DIR = APPROACH_DIR.parent.parent
ENV_FILE = APPROACH_DIR / ".env.approach2"

if ENV_FILE.exists():
    load_dotenv(ENV_FILE)
else:
    load_dotenv(BASE_DIR / ".env")

# Paths
SESSION_FILE = BASE_DIR / ".tmp" / "approach2" / "linkedin_session.json"
SESSION_FILE.parent.mkdir(parents=True, exist_ok=True)


class LinkedInAuth:
    """
    Manages LinkedIn browser authentication with session persistence.
    """

    def __init__(self, headless: bool = False):
        """
        Initialize LinkedIn auth handler.

        Args:
            headless: Run browser in headless mode (default False for safety)
        """
        self.headless = headless
        self.anti_detection = AntiDetection()
        self.rate_limiter = RateLimiter(
            actions_per_hour=int(os.getenv("ACTIONS_PER_HOUR", "20")),
            profiles_per_session=int(os.getenv("PROFILES_PER_SESSION", "50")),
            messages_per_day=int(os.getenv("MESSAGES_PER_DAY", "25")),
            comments_per_day=int(os.getenv("COMMENTS_PER_DAY", "30"))
        )

        self._playwright = None
        self._browser = None
        self._context = None

    def get_authenticated_context(self) -> Tuple["sync_playwright", Browser, BrowserContext]:
        """
        Get an authenticated browser context.

        Returns:
            Tuple of (playwright, browser, context)
        """
        email = os.getenv("LINKEDIN_EMAIL")
        password = os.getenv("LINKEDIN_PASSWORD")

        if not email or not password:
            raise ValueError(
                "LINKEDIN_EMAIL and LINKEDIN_PASSWORD must be set in .env.approach2 or .env"
            )

        self._playwright = sync_playwright().start()

        # Launch with anti-detection settings
        viewport = self.anti_detection.get_viewport_size()
        self._browser = self._playwright.chromium.launch(
            headless=self.headless,
            args=self.anti_detection.get_browser_args()
        )

        # Try existing session first
        if SESSION_FILE.exists():
            try:
                self._context = self._browser.new_context(
                    storage_state=str(SESSION_FILE),
                    viewport={"width": viewport[0], "height": viewport[1]},
                    user_agent=self.anti_detection.user_agent
                )

                if self._verify_session():
                    print("Reusing existing LinkedIn session")
                    return self._playwright, self._browser, self._context

                self._context.close()
            except Exception as e:
                print(f"Session invalid: {e}")

        # Fresh login required
        self._context = self._browser.new_context(
            viewport={"width": viewport[0], "height": viewport[1]},
            user_agent=self.anti_detection.user_agent
        )

        self._perform_login(email, password)
        return self._playwright, self._browser, self._context

    def _verify_session(self) -> bool:
        """Verify if the current session is still valid"""
        page = self._context.new_page()
        try:
            page.goto("https://www.linkedin.com/feed/", wait_until="domcontentloaded")
            self.anti_detection.medium_wait()

            # Check if we're on the feed (logged in) or redirected to login
            if "/login" in page.url or "/authwall" in page.url:
                return False

            # Look for feed elements that indicate logged in state
            feed_indicators = [
                '[data-test-id="feed-shared-update"]',
                '.feed-shared-update-v2',
                '.scaffold-layout__main',
                'div[data-urn*="activity"]'
            ]

            for indicator in feed_indicators:
                if page.locator(indicator).count() > 0:
                    return True

            return False
        except Exception:
            return False
        finally:
            page.close()

    def _perform_login(self, email: str, password: str):
        """Perform fresh login to LinkedIn"""
        page = self._context.new_page()

        try:
            print("Logging in to LinkedIn...")
            page.goto("https://www.linkedin.com/login", wait_until="domcontentloaded")
            self.anti_detection.medium_wait()

            # Fill email
            email_input = page.locator('#username')
            email_input.click()
            self.anti_detection.short_wait()
            email_input.fill(email)

            self.anti_detection.short_wait()

            # Fill password
            password_input = page.locator('#password')
            password_input.click()
            self.anti_detection.short_wait()
            password_input.fill(password)

            self.anti_detection.short_wait()

            # Click login button
            page.locator('button[type="submit"]').click()

            # Wait for navigation
            self.anti_detection.long_wait()

            # Check for challenges
            if self._handle_login_challenges(page):
                print("Login challenge detected - may need manual intervention")

            # Verify login success
            max_attempts = 15
            for _ in range(max_attempts):
                current_url = page.url
                if "/feed" in current_url or "/mynetwork" in current_url:
                    break
                if "/login" not in current_url and "/checkpoint" not in current_url:
                    break
                self.anti_detection.short_wait()

            if "/login" in page.url:
                raise Exception("Login failed - check credentials or handle challenge manually")

            # Save session
            self._context.storage_state(path=str(SESSION_FILE))
            print(f"LinkedIn session saved to {SESSION_FILE}")

        finally:
            page.close()

    def _handle_login_challenges(self, page: Page) -> bool:
        """
        Handle potential login challenges (2FA, captcha, verification).

        Returns:
            True if a challenge was detected
        """
        challenge_indicators = [
            '/checkpoint/',
            'security-verification',
            'challenge',
            '/uas/consumer-email-challenge'
        ]

        for indicator in challenge_indicators:
            if indicator in page.url:
                print(f"Challenge detected: {indicator}")
                print("Please complete the challenge manually in the browser...")
                # Wait for user to complete challenge
                input("Press Enter after completing the challenge...")
                return True

        # Check for CAPTCHA
        if page.locator('iframe[title*="captcha"]').count() > 0:
            print("CAPTCHA detected - please solve manually")
            input("Press Enter after solving CAPTCHA...")
            return True

        return False

    def warm_up_session(self, page: Page):
        """
        Warm up the session with natural browsing behavior.
        Do this before performing automated actions.
        """
        print("Warming up session...")

        # Go to feed
        page.goto("https://www.linkedin.com/feed/")
        self.anti_detection.long_wait()

        # Scroll through feed naturally
        for _ in range(3):
            self.anti_detection.scroll_naturally(page, "down")
            self.anti_detection.random_scroll_pause()

        # Maybe check notifications
        if self.anti_detection.human_delay(1) > 1.5:
            try:
                page.goto("https://www.linkedin.com/notifications/")
                self.anti_detection.medium_wait()
            except Exception:
                pass

        print("Session warm-up complete")

    def close(self):
        """Clean up browser resources"""
        if self._context:
            self._context.close()
        if self._browser:
            self._browser.close()
        if self._playwright:
            self._playwright.stop()

    def __enter__(self):
        return self.get_authenticated_context()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


def get_authenticated_context(headless: bool = False) -> Tuple:
    """
    Convenience function to get authenticated context.

    Returns:
        Tuple of (playwright, browser, context, auth_handler)
    """
    auth = LinkedInAuth(headless=headless)
    playwright, browser, context = auth.get_authenticated_context()
    return playwright, browser, context, auth


def clear_session():
    """Clear saved session (force fresh login next time)"""
    if SESSION_FILE.exists():
        SESSION_FILE.unlink()
        print("LinkedIn session cleared")


if __name__ == "__main__":
    # Test authentication
    try:
        playwright, browser, context, auth = get_authenticated_context(headless=False)
        page = context.new_page()

        # Warm up
        auth.warm_up_session(page)

        print(f"Current URL: {page.url}")
        print("Authentication test successful!")
        print(f"Rate limit status: {auth.rate_limiter.get_status()}")

        input("Press Enter to close browser...")

        page.close()
        auth.close()
    except Exception as e:
        print(f"Authentication failed: {e}")
        raise
