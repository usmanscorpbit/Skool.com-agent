"""
LinkedIn Post Finder
Finds posts in feed and by hashtag for engagement opportunities
"""

import json
import re
from pathlib import Path
from typing import List, Optional
from datetime import datetime
from playwright.sync_api import Page, BrowserContext

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from shared.types import LinkedInPost, ApproachType, ScrapingResult
from shared.profile_analyzer import ProfileAnalyzer
from .linkedin_browser_auth import get_authenticated_context
from .anti_detection import AntiDetection, RateLimiter

BASE_DIR = Path(__file__).parent.parent.parent
OUTPUT_DIR = BASE_DIR / ".tmp" / "approach2"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


class LinkedInPostFinder:
    """
    Finds and scrapes LinkedIn posts for engagement.
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
        self.profile_analyzer = ProfileAnalyzer()

    def find_posts_by_hashtag(
        self,
        hashtag: str,
        max_posts: int = 20
    ) -> List[LinkedInPost]:
        """
        Find posts by hashtag.

        Args:
            hashtag: Hashtag to search (with or without #)
            max_posts: Maximum posts to retrieve

        Returns:
            List of LinkedInPost objects
        """
        hashtag = hashtag.lstrip('#')
        url = f"https://www.linkedin.com/feed/hashtag/{hashtag}/"

        page = self.context.new_page()
        posts = []

        try:
            page.goto(url, wait_until="domcontentloaded")
            self.anti_detection.long_wait()

            # Scroll to load more posts
            posts = self._scrape_feed_posts(page, max_posts)

        except Exception as e:
            print(f"Error finding posts by hashtag {hashtag}: {e}")
        finally:
            page.close()

        return posts

    def find_posts_in_feed(self, max_posts: int = 20) -> List[LinkedInPost]:
        """
        Find posts in the main feed.

        Args:
            max_posts: Maximum posts to retrieve

        Returns:
            List of LinkedInPost objects
        """
        page = self.context.new_page()
        posts = []

        try:
            page.goto("https://www.linkedin.com/feed/", wait_until="domcontentloaded")
            self.anti_detection.long_wait()

            posts = self._scrape_feed_posts(page, max_posts)

        except Exception as e:
            print(f"Error finding posts in feed: {e}")
        finally:
            page.close()

        return posts

    def find_posts_by_keyword(
        self,
        keyword: str,
        max_posts: int = 20
    ) -> List[LinkedInPost]:
        """
        Search for posts by keyword.

        Args:
            keyword: Search keyword
            max_posts: Maximum posts to retrieve

        Returns:
            List of LinkedInPost objects
        """
        # URL encode the keyword
        from urllib.parse import quote
        encoded_keyword = quote(keyword)
        url = f"https://www.linkedin.com/search/results/content/?keywords={encoded_keyword}"

        page = self.context.new_page()
        posts = []

        try:
            page.goto(url, wait_until="domcontentloaded")
            self.anti_detection.long_wait()

            posts = self._scrape_search_results(page, max_posts)

        except Exception as e:
            print(f"Error searching posts for '{keyword}': {e}")
        finally:
            page.close()

        return posts

    def _scrape_feed_posts(self, page: Page, max_posts: int) -> List[LinkedInPost]:
        """Scrape posts from feed or hashtag page"""
        posts = []
        scroll_count = 0
        max_scrolls = max_posts // 3 + 3

        # Wait for page to load, then scroll to trigger content
        self.anti_detection.long_wait()
        page.mouse.wheel(0, 300)
        self.anti_detection.short_wait()

        # Try to wait for feed elements (but don't fail if timeout)
        try:
            page.wait_for_selector('.feed-shared-update-v2, [data-urn*="activity"], .occludable-update, .scaffold-finite-scroll', timeout=15000)
        except:
            # Continue anyway - might still find posts
            pass

        while len(posts) < max_posts and scroll_count < max_scrolls:
            # Find post containers with multiple selectors
            container_selectors = [
                '.feed-shared-update-v2',
                '[data-urn*="urn:li:activity"]',
                '.occludable-update',
                'div[data-id*="urn:li:activity"]',
                '.update-components-actor',
            ]

            post_containers = None
            for selector in container_selectors:
                containers = page.locator(selector)
                if containers.count() > 0:
                    post_containers = containers
                    break

            if not post_containers or post_containers.count() == 0:
                scroll_count += 1
                self.anti_detection.scroll_naturally(page, "down", 500)
                self.anti_detection.random_scroll_pause()
                continue

            for i in range(min(post_containers.count(), max_posts - len(posts))):
                if len(posts) >= max_posts:
                    break

                try:
                    container = post_containers.nth(i)
                    post = self._extract_post_data(container)
                    if post and post.id not in [p.id for p in posts]:
                        posts.append(post)
                        self.rate_limiter.record_action()
                except Exception as e:
                    continue

            # Scroll for more
            self.anti_detection.scroll_naturally(page, "down", 500)
            self.anti_detection.random_scroll_pause()
            scroll_count += 1

        return posts

    def _scrape_search_results(self, page: Page, max_posts: int) -> List[LinkedInPost]:
        """Scrape posts from search results"""
        posts = []
        scroll_count = 0
        max_scrolls = max_posts // 3 + 2

        while len(posts) < max_posts and scroll_count < max_scrolls:
            # Search result containers
            result_containers = page.locator(
                '.search-results__cluster-content .reusable-search__result-container, '
                '.entity-result'
            )

            for i in range(result_containers.count()):
                if len(posts) >= max_posts:
                    break

                try:
                    container = result_containers.nth(i)
                    post = self._extract_search_result_post(container)
                    if post and post.id not in [p.id for p in posts]:
                        posts.append(post)
                except Exception:
                    continue

            # Scroll for more
            self.anti_detection.scroll_naturally(page, "down", 500)
            self.anti_detection.random_scroll_pause()
            scroll_count += 1

        return posts

    def _extract_post_data(self, container) -> Optional[LinkedInPost]:
        """Extract post data from a feed post container"""
        try:
            # Extract post ID from data-urn
            post_id = ""
            urn = container.get_attribute("data-urn")
            if urn:
                match = re.search(r'activity:(\d+)', urn)
                if match:
                    post_id = match.group(1)
            if not post_id:
                post_id = str(hash(container.inner_text()[:100]))

            # Author info
            author_name = ""
            author_url = ""
            author_headline = ""

            author_link = container.locator('.update-components-actor__title a, .feed-shared-actor__name a')
            if author_link.count() > 0:
                author_name = author_link.first.inner_text().strip()
                author_url = author_link.first.get_attribute("href") or ""

            headline_el = container.locator('.update-components-actor__description, .feed-shared-actor__description')
            if headline_el.count() > 0:
                author_headline = headline_el.first.inner_text().strip()

            # Post content
            content = ""
            content_el = container.locator(
                '.feed-shared-update-v2__description, '
                '.update-components-text, '
                '.feed-shared-text'
            )
            if content_el.count() > 0:
                content = content_el.first.inner_text().strip()

            # Post URL - try multiple selectors
            post_url = ""
            url_selectors = [
                'a[href*="/feed/update/"]',
                'a[href*="activity"]',
                '.feed-shared-actor__sub-description a',
                '.update-components-actor__sub-description a',
                'a[data-urn*="activity"]',
                '.feed-shared-social-action-bar a',
            ]

            for selector in url_selectors:
                try:
                    link = container.locator(selector)
                    if link.count() > 0:
                        href = link.first.get_attribute("href")
                        if href and ('activity' in href or 'update' in href):
                            post_url = href
                            break
                except:
                    continue

            # If no URL found but we have an activity ID, construct the URL
            if not post_url and post_id and post_id.isdigit():
                post_url = f"https://www.linkedin.com/feed/update/urn:li:activity:{post_id}/"

            # Engagement metrics
            likes, comments, shares = self._extract_engagement(container)

            # Posted time
            posted_relative = ""
            time_el = container.locator('.update-components-actor__sub-description, .feed-shared-actor__sub-description')
            if time_el.count() > 0:
                posted_relative = time_el.first.inner_text().strip()
                # Clean up (often contains "• ")
                posted_relative = re.sub(r'^[•·]\s*', '', posted_relative)

            # Extract hashtags
            hashtags = re.findall(r'#(\w+)', content)

            return LinkedInPost(
                id=post_id,
                author_name=author_name,
                author_profile_url=author_url,
                author_headline=author_headline,
                content=content,
                post_url=post_url,
                likes=likes,
                comments=comments,
                shares=shares,
                posted_relative=posted_relative,
                hashtags=hashtags,
                source_approach=ApproachType.PLAYWRIGHT,
                scraped_at=datetime.now()
            )

        except Exception as e:
            print(f"Error extracting post: {e}")
            return None

    def _extract_search_result_post(self, container) -> Optional[LinkedInPost]:
        """Extract post data from search result"""
        try:
            # Similar extraction but different selectors for search results
            post_id = str(hash(container.inner_text()[:100]))

            # Author
            author_name = ""
            author_url = ""
            author_el = container.locator('.entity-result__title-text a')
            if author_el.count() > 0:
                author_name = author_el.first.inner_text().strip()
                author_url = author_el.first.get_attribute("href") or ""

            # Content snippet
            content = ""
            content_el = container.locator('.entity-result__summary')
            if content_el.count() > 0:
                content = content_el.first.inner_text().strip()

            # Try to get full content link
            post_url = ""
            link_el = container.locator('a[href*="/posts/"], a[href*="/pulse/"]')
            if link_el.count() > 0:
                post_url = link_el.first.get_attribute("href") or ""

            hashtags = re.findall(r'#(\w+)', content)

            return LinkedInPost(
                id=post_id,
                author_name=author_name,
                author_profile_url=author_url,
                content=content,
                post_url=post_url,
                hashtags=hashtags,
                source_approach=ApproachType.PLAYWRIGHT,
                scraped_at=datetime.now()
            )

        except Exception:
            return None

    def _extract_engagement(self, container) -> tuple:
        """Extract likes, comments, shares counts"""
        likes = 0
        comments = 0
        shares = 0

        # Reactions count
        reactions_el = container.locator(
            '.social-details-social-counts__reactions-count, '
            '.reactions-count'
        )
        if reactions_el.count() > 0:
            text = reactions_el.first.inner_text()
            likes = self._parse_count(text)

        # Comments count
        comments_el = container.locator(
            '.social-details-social-counts__comments, '
            'button[aria-label*="comment"]'
        )
        if comments_el.count() > 0:
            text = comments_el.first.inner_text()
            comments = self._parse_count(text)

        # Reposts/shares count
        shares_el = container.locator(
            '.social-details-social-counts__reposts, '
            'button[aria-label*="repost"]'
        )
        if shares_el.count() > 0:
            text = shares_el.first.inner_text()
            shares = self._parse_count(text)

        return likes, comments, shares

    def _parse_count(self, text: str) -> int:
        """Parse engagement count from text"""
        if not text:
            return 0
        text = text.strip().lower()
        numbers = re.findall(r'[\d,]+', text)
        if not numbers:
            return 0
        num = int(numbers[0].replace(',', ''))
        if 'k' in text:
            num *= 1000
        elif 'm' in text:
            num *= 1000000
        return num


def find_posts(
    hashtags: List[str] = None,
    keywords: List[str] = None,
    include_feed: bool = True,
    max_per_source: int = 10,
    headless: bool = False
) -> ScrapingResult:
    """
    Main entry point for finding posts.

    Args:
        hashtags: List of hashtags to search
        keywords: List of keywords to search
        include_feed: Include posts from main feed
        max_per_source: Max posts per source
        headless: Run browser in headless mode

    Returns:
        ScrapingResult with posts
    """
    playwright, browser, context, auth = get_authenticated_context(headless)
    all_posts = []
    errors = []

    try:
        finder = LinkedInPostFinder(
            context=context,
            anti_detection=auth.anti_detection,
            rate_limiter=auth.rate_limiter
        )

        # Search hashtags
        if hashtags:
            for tag in hashtags:
                print(f"Searching hashtag: #{tag}")
                posts = finder.find_posts_by_hashtag(tag, max_per_source)
                all_posts.extend(posts)
                auth.anti_detection.medium_wait()

        # Search keywords
        if keywords:
            for keyword in keywords:
                print(f"Searching keyword: {keyword}")
                posts = finder.find_posts_by_keyword(keyword, max_per_source)
                all_posts.extend(posts)
                auth.anti_detection.medium_wait()

        # Get feed posts
        if include_feed:
            print("Scanning feed...")
            posts = finder.find_posts_in_feed(max_per_source)
            all_posts.extend(posts)

        # Deduplicate
        seen_ids = set()
        unique_posts = []
        for post in all_posts:
            if post.id not in seen_ids:
                seen_ids.add(post.id)
                unique_posts.append(post)

        # Save results
        output_file = OUTPUT_DIR / "found_posts.json"
        with open(output_file, "w") as f:
            json.dump([p.to_dict() for p in unique_posts], f, indent=2)
        print(f"Saved {len(unique_posts)} posts to {output_file}")

        return ScrapingResult(
            success=len(unique_posts) > 0,
            approach=ApproachType.PLAYWRIGHT,
            posts=unique_posts,
            errors=errors,
            metadata={
                "hashtags_searched": hashtags or [],
                "keywords_searched": keywords or [],
                "include_feed": include_feed,
                "total_found": len(unique_posts)
            }
        )

    finally:
        auth.close()


if __name__ == "__main__":
    import sys

    # Default: search feed and some hashtags
    hashtags = sys.argv[1:] if len(sys.argv) > 1 else ["entrepreneur", "startup"]

    print(f"Searching for posts with hashtags: {hashtags}")
    result = find_posts(hashtags=hashtags, include_feed=True, headless=False)

    print(f"\nFound {len(result.posts)} posts")
    for post in result.posts[:5]:
        print(f"\n{post.author_name}: {post.content[:100]}...")
        print(f"  Likes: {post.likes}, Comments: {post.comments}")
