"""
LinkedIn Content Poster
Creates and posts content via browser automation
"""

import json
from pathlib import Path
from typing import Optional, List
from datetime import datetime
from playwright.sync_api import Page, BrowserContext

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from shared.types import ContentDraft, ApproachType
from .linkedin_browser_auth import get_authenticated_context
from .anti_detection import AntiDetection, RateLimiter

BASE_DIR = Path(__file__).parent.parent.parent
OUTPUT_DIR = BASE_DIR / ".tmp" / "approach2"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


class LinkedInContentPoster:
    """
    Posts content to LinkedIn via browser automation.
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

    def create_post(
        self,
        content: str,
        hashtags: List[str] = None,
        media_paths: List[str] = None
    ) -> dict:
        """
        Create a new LinkedIn post.

        Args:
            content: Post body text
            hashtags: List of hashtags (without #)
            media_paths: Local paths to images/videos to attach

        Returns:
            Dict with success status and post info
        """
        page = self.context.new_page()
        result = {
            "success": False,
            "post_url": None,
            "error": None,
            "posted_at": None
        }

        try:
            # Navigate to feed
            page.goto("https://www.linkedin.com/feed/", wait_until="domcontentloaded")
            self.anti_detection.long_wait()

            # Scroll up to make sure we're at the top where the post box is
            page.evaluate("window.scrollTo(0, 0)")
            self.anti_detection.short_wait()

            # Click "Start a post" button/area - try multiple approaches
            start_post_selectors = [
                # The main share box area
                '.share-box-feed-entry__top-bar',
                '.share-box-feed-entry__trigger',
                # Button with "Start a post" text
                'button:has-text("Start a post")',
                'button[aria-label*="Start a post"]',
                'button[aria-label*="Create a post"]',
                # The avatar area that triggers post
                '.share-box-feed-entry__avatar-trigger',
                # Generic clickable area
                '.share-box-feed-entry__closed-share-box',
                '.share-box__open',
                # Any placeholder text
                '[placeholder*="Start a post"]',
                '[data-placeholder*="Start a post"]',
            ]

            clicked = False
            for selector in start_post_selectors:
                try:
                    btn = page.locator(selector)
                    if btn.count() > 0:
                        btn.first.scroll_into_view_if_needed()
                        self.anti_detection.short_wait()
                        if btn.first.is_visible():
                            btn.first.click()
                            clicked = True
                            print(f"  Clicked: {selector}")
                            break
                except:
                    continue

            # If still not clicked, try clicking on any visible text that says "Start a post"
            if not clicked:
                try:
                    start_text = page.get_by_text("Start a post", exact=False)
                    if start_text.count() > 0:
                        start_text.first.scroll_into_view_if_needed()
                        self.anti_detection.short_wait()
                        start_text.first.click()
                        clicked = True
                        print("  Clicked: 'Start a post' text")
                except:
                    pass

            # Last resort: try clicking on any element that looks like a post composer
            if not clicked:
                try:
                    # Look for the post input area directly
                    post_input = page.locator('.share-box-feed-entry__top-bar, .feed-shared-update-v2__content')
                    if post_input.count() > 0:
                        post_input.first.click()
                        clicked = True
                        print("  Clicked: post input area")
                except:
                    pass

            if not clicked:
                result["error"] = "Could not find 'Start a post' button"
                return result

            self.anti_detection.medium_wait()

            # Wait for post modal to appear
            self.anti_detection.medium_wait()

            modal_selectors = [
                '.share-box_dropdown',
                '.share-creation-state__text-editor',
                '[data-test-share-box-form]',
                '.ql-editor',
                '.editor-content',
                '[role="dialog"]',
                '.share-box--open',
                '[contenteditable="true"]',
            ]

            modal_found = False
            for _ in range(5):  # Try up to 5 times
                for selector in modal_selectors:
                    try:
                        el = page.locator(selector)
                        if el.count() > 0 and el.first.is_visible():
                            modal_found = True
                            print(f"  Modal found: {selector}")
                            break
                    except:
                        continue
                if modal_found:
                    break
                self.anti_detection.short_wait()

            if not modal_found:
                result["error"] = "Post modal did not appear"
                return result

            # Append hashtags to content
            full_content = content
            if hashtags:
                hashtag_text = " ".join([f"#{tag}" for tag in hashtags])
                full_content = f"{content}\n\n{hashtag_text}"

            # Find and click the editor
            editor_selectors = [
                '.ql-editor',
                '[contenteditable="true"]',
                '.editor-content',
                '[data-placeholder]',
                '[role="textbox"]',
            ]

            editor = None
            for selector in editor_selectors:
                try:
                    el = page.locator(selector)
                    if el.count() > 0 and el.first.is_visible():
                        editor = el.first
                        print(f"  Editor found: {selector}")
                        break
                except:
                    continue

            if not editor:
                result["error"] = "Could not find editor"
                return result

            editor.click()
            self.anti_detection.short_wait()

            # Type with human-like speed
            for char in full_content:
                editor.type(char, delay=50)
                if char == '\n':
                    self.anti_detection.short_wait()

            self.anti_detection.medium_wait()

            # Handle media upload if provided
            if media_paths:
                self._upload_media(page, media_paths)

            # Click Post button
            post_btn_selectors = [
                'button[aria-label*="Post"]:not([aria-label*="Start"])',
                'button.share-actions__primary-action',
                '[data-control-name="share.post"]',
                'button:has-text("Post"):not(:has-text("Start"))',
                'button.share-box__button--primary',
            ]

            posted = False
            for selector in post_btn_selectors:
                try:
                    btn = page.locator(selector)
                    if btn.count() > 0 and btn.first.is_enabled():
                        btn.first.click()
                        posted = True
                        print(f"  Post clicked: {selector}")
                        break
                except:
                    continue

            if not posted:
                result["error"] = "Could not find or click Post button"
                return result

            # Wait for post to complete
            self.anti_detection.long_wait()
            self.anti_detection.medium_wait()

            # Verify post was created (check for success indicators)
            if "feed" in page.url:
                result["success"] = True
                result["posted_at"] = datetime.now().isoformat()
                self.rate_limiter.record_action()

        except Exception as e:
            result["error"] = str(e)
        finally:
            page.close()

        return result

    def _upload_media(self, page: Page, media_paths: List[str]):
        """Upload media files to post"""
        try:
            # Click add media button
            media_btn = page.locator(
                'button[aria-label*="Add media"], '
                'button[aria-label*="Add a photo"]'
            )
            if media_btn.count() > 0:
                media_btn.first.click()
                self.anti_detection.short_wait()

            # Upload files
            file_input = page.locator('input[type="file"]')
            if file_input.count() > 0:
                for path in media_paths:
                    file_input.set_input_files(path)
                    self.anti_detection.medium_wait()

        except Exception as e:
            print(f"Error uploading media: {e}")

    def create_post_from_draft(self, draft: ContentDraft) -> dict:
        """
        Create a post from a ContentDraft object.

        Args:
            draft: ContentDraft object with post content

        Returns:
            Dict with success status and post info
        """
        return self.create_post(
            content=draft.body,
            hashtags=draft.hashtags,
            media_paths=draft.media_urls if draft.media_urls else None
        )

    def schedule_post(
        self,
        content: str,
        schedule_time: datetime,
        hashtags: List[str] = None
    ) -> dict:
        """
        Schedule a post for later.
        Note: LinkedIn's native scheduling has limited availability.
        This implementation saves the post for manual scheduling.

        Args:
            content: Post content
            schedule_time: When to post
            hashtags: Hashtags to include

        Returns:
            Dict with scheduled post info
        """
        # Save to scheduled posts file
        scheduled_file = OUTPUT_DIR / "scheduled_posts.json"

        scheduled_posts = []
        if scheduled_file.exists():
            with open(scheduled_file) as f:
                scheduled_posts = json.load(f)

        scheduled_posts.append({
            "content": content,
            "hashtags": hashtags or [],
            "scheduled_for": schedule_time.isoformat(),
            "created_at": datetime.now().isoformat(),
            "status": "pending"
        })

        with open(scheduled_file, "w") as f:
            json.dump(scheduled_posts, f, indent=2)

        return {
            "success": True,
            "scheduled_for": schedule_time.isoformat(),
            "note": "Post saved for scheduled posting. Run post_scheduled_content() at the scheduled time."
        }


def create_post(
    content: str,
    hashtags: List[str] = None,
    media_paths: List[str] = None,
    headless: bool = False
) -> dict:
    """
    Main entry point for creating a post.

    Args:
        content: Post body text
        hashtags: List of hashtags (without #)
        media_paths: Local paths to images/videos
        headless: Run browser in headless mode

    Returns:
        Dict with success status
    """
    playwright, browser, context, auth = get_authenticated_context(headless)

    try:
        poster = LinkedInContentPoster(
            context=context,
            anti_detection=auth.anti_detection,
            rate_limiter=auth.rate_limiter
        )

        result = poster.create_post(content, hashtags, media_paths)

        # Log the post
        log_file = OUTPUT_DIR / "post_log.json"
        log_entries = []
        if log_file.exists():
            with open(log_file) as f:
                log_entries = json.load(f)

        log_entries.append({
            "content": content[:200],
            "hashtags": hashtags,
            "result": result,
            "timestamp": datetime.now().isoformat()
        })

        with open(log_file, "w") as f:
            json.dump(log_entries, f, indent=2)

        return result

    finally:
        auth.close()


if __name__ == "__main__":
    # Test post creation
    test_content = """Testing LinkedIn automation post.

This is a test post created via browser automation.

Delete this after testing!"""

    print("Creating test post...")
    print("WARNING: This will create a real post on LinkedIn!")

    confirm = input("Continue? (yes/no): ")
    if confirm.lower() != "yes":
        print("Cancelled")
    else:
        result = create_post(
            content=test_content,
            hashtags=["test", "automation"],
            headless=False
        )
        print(f"Result: {result}")
