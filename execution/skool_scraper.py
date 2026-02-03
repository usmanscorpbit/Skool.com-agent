"""
Skool Post Scraper
Scrapes posts, comments, and engagement data from Skool communities
"""

import os
import json
import csv
import re
from datetime import datetime
from pathlib import Path
from typing import Optional
from playwright.sync_api import Page, BrowserContext
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).parent.parent
OUTPUT_DIR = BASE_DIR / ".tmp"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def parse_relative_time(time_str: str) -> datetime:
    """Convert relative time strings like '2h', '3d', '1w' to datetime"""
    now = datetime.now()
    time_str = time_str.lower().strip()

    # Match patterns like "2h", "3d", "1w", "2mo"
    match = re.match(r'(\d+)\s*(s|m|h|d|w|mo|y)', time_str)
    if not match:
        return now

    value = int(match.group(1))
    unit = match.group(2)

    from datetime import timedelta
    if unit == 's':
        return now - timedelta(seconds=value)
    elif unit == 'm':
        return now - timedelta(minutes=value)
    elif unit == 'h':
        return now - timedelta(hours=value)
    elif unit == 'd':
        return now - timedelta(days=value)
    elif unit == 'w':
        return now - timedelta(weeks=value)
    elif unit == 'mo':
        return now - timedelta(days=value * 30)
    elif unit == 'y':
        return now - timedelta(days=value * 365)

    return now


def scrape_community_posts(
    context: BrowserContext,
    community_url: str,
    max_posts: int = 50,
    include_comments: bool = False,
    max_comments_per_post: int = 5
) -> list[dict]:
    """
    Scrape posts from a Skool community by visiting each post page.

    Args:
        context: Authenticated browser context
        community_url: URL of the Skool community (e.g., https://www.skool.com/community-name)
        max_posts: Maximum number of posts to scrape
        include_comments: Whether to scrape comments on each post
        max_comments_per_post: Max comments to scrape per post

    Returns:
        List of post dictionaries
    """
    page = context.new_page()
    posts = []

    try:
        # Normalize URL
        community_url = community_url.rstrip('/')
        if community_url.endswith('/community'):
            community_url = community_url[:-10]

        print(f"Navigating to {community_url}")
        page.goto(community_url)
        page.wait_for_load_state("domcontentloaded")
        page.wait_for_timeout(3000)

        # Collect unique post URLs
        post_urls = set()
        scroll_attempts = 0
        max_scroll_attempts = 15

        while len(post_urls) < max_posts and scroll_attempts < max_scroll_attempts:
            links = page.locator('a[href*="?p="]').all()
            for link in links:
                href = link.get_attribute('href')
                if href and '?p=' in href:
                    full_url = f"https://www.skool.com{href}" if not href.startswith('http') else href
                    post_urls.add(full_url)

            if len(post_urls) >= max_posts:
                break

            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            page.wait_for_timeout(2000)
            scroll_attempts += 1

        print(f"Found {len(post_urls)} unique post URLs")

        # Visit each post page
        post_urls_list = list(post_urls)[:max_posts]

        for i, post_url in enumerate(post_urls_list):
            try:
                post_data = scrape_single_post(page, post_url, i)
                if post_data:
                    posts.append(post_data)
                    print(f"Scraped post {i+1}/{len(post_urls_list)}: {post_data.get('title', 'Untitled')[:50]}")
            except Exception as e:
                print(f"Error scraping post {post_url}: {e}")
                continue

    finally:
        page.close()

    return posts


def scrape_single_post(page, post_url: str, index: int) -> Optional[dict]:
    """Visit a single post page and extract all data"""
    try:
        page.goto(post_url)
        page.wait_for_load_state("domcontentloaded")
        page.wait_for_timeout(1500)

        title = ""
        content = ""
        author = ""
        author_url = ""
        timestamp = ""
        likes = 0
        comments_count = 0

        body_text = page.locator('body').inner_text()

        # Title from h1
        try:
            h1 = page.locator('h1').first
            if h1.count() > 0:
                title = h1.inner_text().strip()
        except:
            pass

        # Fallback: title from URL slug
        if not title:
            import urllib.parse
            parsed = urllib.parse.urlparse(post_url)
            path_parts = parsed.path.split('/')
            if len(path_parts) >= 3:
                slug = path_parts[-1].split('?')[0]
                title = slug.replace('-', ' ').title()

        # Author
        try:
            author_links = page.locator('a[href*="/@"]').all()
            if author_links:
                author = author_links[0].inner_text().strip()
                href = author_links[0].get_attribute('href')
                if href:
                    author_url = f"https://www.skool.com{href}" if not href.startswith('http') else href
        except:
            pass

        # Content
        try:
            paragraphs = page.locator('p').all()
            content_parts = []
            for p in paragraphs[:3]:
                text = p.inner_text().strip()
                if text and len(text) > 20:
                    content_parts.append(text)
            content = ' '.join(content_parts)[:500]
        except:
            pass

        # Engagement from page text
        like_match = re.search(r'(\d+)\s*(?:like)', body_text, re.I)
        if like_match:
            likes = int(like_match.group(1))

        comment_match = re.search(r'(\d+)\s*(?:comment|repl)', body_text, re.I)
        if comment_match:
            comments_count = int(comment_match.group(1))

        # Timestamp
        time_patterns = [
            r'(\d+[smhdw])\s*ago',
            r'(\d+)\s*(second|minute|hour|day|week|month)s?\s*ago',
        ]
        for pattern in time_patterns:
            match = re.search(pattern, body_text, re.I)
            if match:
                timestamp = match.group(0)
                break

        posted_at = None
        if timestamp:
            try:
                posted_at = parse_relative_time(timestamp)
            except:
                pass

        return {
            'id': f"post_{index}",
            'title': title or f"Post {index}",
            'content': content,
            'author': author,
            'author_url': author_url,
            'url': post_url,
            'timestamp': timestamp,
            'posted_at': posted_at.isoformat() if posted_at else None,
            'likes': likes,
            'comments_count': comments_count,
            'category': "",
            'scraped_at': datetime.now().isoformat()
        }

    except Exception as e:
        print(f"Error in scrape_single_post: {e}")
        return None


def scrape_post_comments(
    context: BrowserContext,
    post_url: str,
    max_comments: int = 5
) -> list[dict]:
    """Scrape comments from a specific post"""
    page = context.new_page()
    comments = []

    try:
        page.goto(post_url)
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(2000)

        # Find comment elements
        comment_selectors = ['.comment', '[data-testid="comment"]', '.reply']
        comment_elements = []

        for sel in comment_selectors:
            els = page.locator(sel).all()
            if els:
                comment_elements = els[:max_comments]
                break

        for i, comment_el in enumerate(comment_elements):
            try:
                author = ""
                content = ""
                timestamp = ""

                # Author
                author_el = comment_el.locator('.author-name, [data-testid="comment-author"], a[href*="/@"]').first
                if author_el.count() > 0:
                    author = author_el.inner_text().strip()

                # Content
                content_el = comment_el.locator('.comment-content, .comment-body, p').first
                if content_el.count() > 0:
                    content = content_el.inner_text().strip()

                # Timestamp
                time_el = comment_el.locator('time, .timestamp').first
                if time_el.count() > 0:
                    timestamp = time_el.inner_text().strip()

                comments.append({
                    'author': author,
                    'content': content,
                    'timestamp': timestamp
                })

            except Exception as e:
                print(f"Error extracting comment {i}: {e}")
                continue

    finally:
        page.close()

    return comments


def save_posts_to_csv(posts: list[dict], filename: str = "scraped_posts.csv"):
    """Save posts to CSV file"""
    filepath = OUTPUT_DIR / filename

    if not posts:
        print("No posts to save")
        return filepath

    # Flatten comments for CSV
    fieldnames = [
        'id', 'title', 'content', 'author', 'author_url', 'url',
        'timestamp', 'posted_at', 'likes', 'comments_count', 'category', 'scraped_at'
    ]

    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(posts)

    print(f"Saved {len(posts)} posts to {filepath}")
    return filepath


def save_posts_to_json(posts: list[dict], filename: str = "scraped_posts.json"):
    """Save posts to JSON file"""
    filepath = OUTPUT_DIR / filename

    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(posts, f, indent=2, ensure_ascii=False)

    print(f"Saved {len(posts)} posts to {filepath}")
    return filepath


def scrape_community(
    community_url: str,
    max_posts: int = 50,
    include_comments: bool = False,
    headless: bool = True
) -> list[dict]:
    """
    Main entry point - scrape a community and save results.

    Args:
        community_url: Skool community URL
        max_posts: Maximum posts to scrape
        include_comments: Whether to also scrape comments
        headless: Run browser in headless mode

    Returns:
        List of scraped posts
    """
    from skool_auth import get_authenticated_context

    playwright, browser, context = get_authenticated_context(headless=headless)

    try:
        posts = scrape_community_posts(
            context,
            community_url,
            max_posts=max_posts,
            include_comments=include_comments
        )

        # Save to both formats
        if posts:
            save_posts_to_csv(posts)
            save_posts_to_json(posts)

        return posts

    finally:
        browser.close()
        playwright.stop()


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python skool_scraper.py <community_url> [max_posts]")
        print("Example: python skool_scraper.py https://www.skool.com/ai-automation 30")
        sys.exit(1)

    url = sys.argv[1]
    max_posts = int(sys.argv[2]) if len(sys.argv) > 2 else 50

    print(f"Scraping {url} (max {max_posts} posts)...")
    posts = scrape_community(url, max_posts=max_posts, headless=False)
    print(f"\nScraped {len(posts)} posts successfully!")
