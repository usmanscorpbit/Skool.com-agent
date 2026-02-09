"""
LinkedIn Commenter
Posts comments on LinkedIn posts via browser automation
"""

import json
from pathlib import Path
from typing import Optional, List
from datetime import datetime
from playwright.sync_api import Page, BrowserContext

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from shared.types import LinkedInPost, ContentDraft, CommentOpportunity, ApproachType
from .linkedin_browser_auth import get_authenticated_context
from .anti_detection import AntiDetection, RateLimiter

BASE_DIR = Path(__file__).parent.parent.parent
OUTPUT_DIR = BASE_DIR / ".tmp" / "approach2"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


class LinkedInCommenter:
    """
    Posts comments on LinkedIn posts via browser automation.
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

    def post_comment(
        self,
        post_url: str,
        comment: str
    ) -> dict:
        """
        Post a comment on a LinkedIn post.

        Args:
            post_url: URL of the post to comment on
            comment: Comment text

        Returns:
            Dict with success status
        """
        if not self.rate_limiter.can_post_comment():
            return {
                "success": False,
                "error": "Daily comment limit reached"
            }

        page = self.context.new_page()
        result = {
            "success": False,
            "post_url": post_url,
            "error": None,
            "posted_at": None
        }

        try:
            page.goto(post_url, wait_until="domcontentloaded")
            self.anti_detection.long_wait()

            # Find and click comment button/area
            comment_area = self._find_comment_area(page)
            if not comment_area:
                result["error"] = "Could not find comment area"
                return result

            # Click to focus comment input
            comment_area.click()
            self.anti_detection.medium_wait()

            # Find the actual text input
            comment_input = page.locator(
                '.ql-editor[data-placeholder*="Add a comment"], '
                '.comments-comment-box__form-container .ql-editor, '
                '[contenteditable="true"][data-artdeco-is-focused]'
            )

            if comment_input.count() == 0:
                # Try clicking again on a different element
                alt_input = page.locator(
                    'div[role="textbox"], '
                    '.comments-comment-texteditor'
                )
                if alt_input.count() > 0:
                    alt_input.first.click()
                    self.anti_detection.short_wait()
                    comment_input = page.locator('[contenteditable="true"]')

            if comment_input.count() == 0:
                result["error"] = "Could not find comment input field"
                return result

            # Type the comment
            input_el = comment_input.first
            input_el.click()
            self.anti_detection.short_wait()

            for char in comment:
                input_el.type(char, delay=40)

            self.anti_detection.medium_wait()

            # Find and click Post/Submit button
            submit_btn = page.locator(
                'button.comments-comment-box__submit-button, '
                'button[aria-label*="Post comment"], '
                'button:has-text("Post")'
            )

            if submit_btn.count() > 0 and submit_btn.first.is_enabled():
                submit_btn.first.click()
                self.anti_detection.long_wait()

                result["success"] = True
                result["posted_at"] = datetime.now().isoformat()
                self.rate_limiter.record_comment()
            else:
                result["error"] = "Submit button not found or disabled"

        except Exception as e:
            result["error"] = str(e)
        finally:
            page.close()

        return result

    def _find_comment_area(self, page: Page):
        """Find the comment input area on a post page"""
        selectors = [
            '.comments-comment-box-comment__text-editor',
            '.comments-comment-box',
            'div[data-placeholder*="Add a comment"]',
            '.feed-shared-update-v2__commentary-footer button[aria-label*="Comment"]'
        ]

        for selector in selectors:
            el = page.locator(selector)
            if el.count() > 0:
                return el.first

        # If not found, try clicking the comment icon to open comment box
        comment_btn = page.locator(
            'button[aria-label*="Comment"], '
            '.social-actions-button--comment'
        )
        if comment_btn.count() > 0:
            comment_btn.first.click()
            self.anti_detection.short_wait()
            # Try again to find comment area
            for selector in selectors[:3]:
                el = page.locator(selector)
                if el.count() > 0:
                    return el.first

        return None

    def reply_to_comment(
        self,
        post_url: str,
        comment_author: str,
        reply: str
    ) -> dict:
        """
        Reply to a specific comment on a post.

        Args:
            post_url: URL of the post
            comment_author: Name of the comment author to reply to
            reply: Reply text

        Returns:
            Dict with success status
        """
        if not self.rate_limiter.can_post_comment():
            return {
                "success": False,
                "error": "Daily comment limit reached"
            }

        page = self.context.new_page()
        result = {
            "success": False,
            "post_url": post_url,
            "error": None,
            "posted_at": None
        }

        try:
            page.goto(post_url, wait_until="domcontentloaded")
            self.anti_detection.long_wait()

            # Scroll to load comments
            self.anti_detection.scroll_naturally(page, "down", 300)
            self.anti_detection.medium_wait()

            # Find the comment by author
            comments = page.locator('.comments-comment-item, .comments-comments-list__comment')

            target_comment = None
            for i in range(comments.count()):
                comment = comments.nth(i)
                author_el = comment.locator(
                    '.comments-post-meta__profile-link, '
                    '.comments-comment-item__post-meta a'
                )
                if author_el.count() > 0:
                    author_text = author_el.first.inner_text()
                    if comment_author.lower() in author_text.lower():
                        target_comment = comment
                        break

            if not target_comment:
                result["error"] = f"Could not find comment by {comment_author}"
                return result

            # Click Reply button
            reply_btn = target_comment.locator(
                'button[aria-label*="Reply"], '
                'button:has-text("Reply")'
            )
            if reply_btn.count() == 0:
                result["error"] = "Reply button not found"
                return result

            reply_btn.first.click()
            self.anti_detection.medium_wait()

            # Type reply
            reply_input = page.locator(
                '.ql-editor[data-placeholder*="Add a reply"], '
                '[contenteditable="true"]:last-of-type'
            )

            if reply_input.count() == 0:
                result["error"] = "Reply input not found"
                return result

            reply_input.first.click()
            self.anti_detection.short_wait()

            for char in reply:
                reply_input.first.type(char, delay=40)

            self.anti_detection.medium_wait()

            # Submit reply
            submit_btn = page.locator(
                'button.comments-comment-box__submit-button:last-of-type, '
                'button[aria-label*="Post reply"]'
            )

            if submit_btn.count() > 0 and submit_btn.first.is_enabled():
                submit_btn.first.click()
                self.anti_detection.long_wait()

                result["success"] = True
                result["posted_at"] = datetime.now().isoformat()
                self.rate_limiter.record_comment()
            else:
                result["error"] = "Submit button not found or disabled"

        except Exception as e:
            result["error"] = str(e)
        finally:
            page.close()

        return result

    def comment_on_opportunities(
        self,
        opportunities: List[CommentOpportunity],
        comments: List[str],
        max_comments: int = 10
    ) -> List[dict]:
        """
        Comment on multiple opportunity posts.

        Args:
            opportunities: List of comment opportunities
            comments: List of comments to use (cycled through)
            max_comments: Maximum comments to post

        Returns:
            List of results
        """
        results = []

        for i, opp in enumerate(opportunities[:max_comments]):
            if not self.rate_limiter.can_post_comment():
                print("Daily comment limit reached")
                break

            if self.anti_detection.should_take_break():
                print("Taking a break...")
                self.anti_detection.long_wait()
                self.anti_detection.long_wait()

            # Cycle through comments
            comment = comments[i % len(comments)]

            print(f"Commenting on post {i + 1}/{len(opportunities)}: {opp.post.author_name}")
            result = self.post_comment(opp.post.post_url, comment)
            result["post_author"] = opp.post.author_name
            result["opportunity_score"] = opp.score
            results.append(result)

            self.anti_detection.long_wait()

        return results


def post_comment(
    post_url: str,
    comment: str,
    headless: bool = False
) -> dict:
    """
    Main entry point for posting a comment.

    Args:
        post_url: URL of the post
        comment: Comment text
        headless: Run browser in headless mode

    Returns:
        Dict with success status
    """
    playwright, browser, context, auth = get_authenticated_context(headless)

    try:
        commenter = LinkedInCommenter(
            context=context,
            anti_detection=auth.anti_detection,
            rate_limiter=auth.rate_limiter
        )

        result = commenter.post_comment(post_url, comment)

        # Log the action
        log_file = OUTPUT_DIR / "comment_log.json"
        log_entries = []
        if log_file.exists():
            with open(log_file) as f:
                log_entries = json.load(f)

        log_entries.append({
            "post_url": post_url,
            "comment": comment[:100],
            "result": result,
            "timestamp": datetime.now().isoformat()
        })

        with open(log_file, "w") as f:
            json.dump(log_entries, f, indent=2)

        return result

    finally:
        auth.close()


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 3:
        print("Usage: python linkedin_commenter.py <post_url> <comment>")
        print('Example: python linkedin_commenter.py "https://linkedin.com/feed/update/urn:li:activity:123" "Great post!"')
        sys.exit(1)

    post_url = sys.argv[1]
    comment = " ".join(sys.argv[2:])

    print(f"Posting comment on: {post_url}")
    print(f"Comment: {comment}")
    print("WARNING: This will post a real comment!")

    confirm = input("Continue? (yes/no): ")
    if confirm.lower() != "yes":
        print("Cancelled")
    else:
        result = post_comment(post_url, comment, headless=False)
        print(f"Result: {result}")
