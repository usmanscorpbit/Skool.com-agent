"""
Auto Engage - Automated Skool Community Engagement
Scrapes, analyzes, and posts comments/replies/posts automatically
"""

import os
import json
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


def scrape_post_with_comments(context: BrowserContext, post_url: str) -> dict:
    """Scrape a single post with all its comments for reply suggestions"""
    page = context.new_page()

    try:
        page.goto(post_url)
        page.wait_for_load_state("domcontentloaded")
        page.wait_for_timeout(2000)

        body_text = page.locator('body').inner_text()

        # Get post title
        title = ""
        try:
            h1 = page.locator('h1').first
            if h1.count() > 0:
                title = h1.inner_text().strip()
        except:
            pass

        # Get post content
        content = ""
        try:
            # Look for main post content area
            paragraphs = page.locator('p').all()
            content_parts = []
            for p in paragraphs[:5]:
                text = p.inner_text().strip()
                if text and len(text) > 10:
                    content_parts.append(text)
            content = '\n'.join(content_parts)[:1000]
        except:
            pass

        # Get author
        author = ""
        try:
            author_links = page.locator('a[href*="/@"]').all()
            if author_links:
                author = author_links[0].inner_text().strip()
        except:
            pass

        # Get existing comments
        comments = []
        try:
            # Scroll to load comments
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            page.wait_for_timeout(1500)

            # Find comment containers - look for user links followed by text
            comment_sections = page.locator('div:has(> a[href*="/@"])').all()

            seen_authors = set()
            for section in comment_sections[:10]:
                try:
                    section_text = section.inner_text().strip()
                    author_link = section.locator('a[href*="/@"]').first

                    if author_link.count() > 0:
                        comment_author = author_link.inner_text().strip()

                        # Skip if we've seen this author (likely the post author)
                        if comment_author == author or comment_author in seen_authors:
                            continue
                        seen_authors.add(comment_author)

                        # Extract comment text (text after author name)
                        comment_text = section_text.replace(comment_author, '').strip()

                        # Clean up the text
                        lines = [l.strip() for l in comment_text.split('\n') if l.strip()]
                        if lines:
                            comment_text = ' '.join(lines[:3])[:300]

                            if len(comment_text) > 20:
                                comments.append({
                                    'author': comment_author,
                                    'content': comment_text
                                })
                except:
                    continue

        except Exception as e:
            print(f"Error getting comments: {e}")

        return {
            'url': post_url,
            'title': title,
            'content': content,
            'author': author,
            'comments': comments[:5]  # Top 5 comments
        }

    finally:
        page.close()


def post_comment(context: BrowserContext, post_url: str, comment_text: str) -> bool:
    """Post a comment on a Skool post"""
    page = context.new_page()

    try:
        page.goto(post_url)
        page.wait_for_load_state("domcontentloaded")
        page.wait_for_timeout(2000)

        # Find comment input - try multiple selectors
        comment_selectors = [
            'textarea[placeholder*="comment"]',
            'textarea[placeholder*="Comment"]',
            'textarea[placeholder*="Write"]',
            'div[contenteditable="true"]',
            '[data-testid="comment-input"]',
            'textarea'
        ]

        comment_input = None
        for selector in comment_selectors:
            el = page.locator(selector).first
            if el.count() > 0:
                comment_input = el
                break

        if not comment_input:
            print("Could not find comment input")
            return False

        # Click to focus and type comment
        comment_input.click()
        page.wait_for_timeout(500)
        comment_input.fill(comment_text)
        page.wait_for_timeout(500)

        # Find and click submit button
        submit_selectors = [
            'button:has-text("Post")',
            'button:has-text("Comment")',
            'button:has-text("Submit")',
            'button:has-text("Send")',
            'button[type="submit"]'
        ]

        for selector in submit_selectors:
            btn = page.locator(selector).first
            if btn.count() > 0 and btn.is_visible():
                btn.click()
                page.wait_for_timeout(2000)
                print(f"Comment posted successfully!")
                return True

        # Try pressing Enter as fallback
        comment_input.press("Enter")
        page.wait_for_timeout(2000)
        print("Comment submitted via Enter key")
        return True

    except Exception as e:
        print(f"Error posting comment: {e}")
        return False
    finally:
        page.close()


def post_reply(context: BrowserContext, post_url: str, comment_author: str, reply_text: str) -> bool:
    """Post a reply to a specific comment"""
    page = context.new_page()

    try:
        page.goto(post_url)
        page.wait_for_load_state("domcontentloaded")
        page.wait_for_timeout(2000)

        # Scroll to load comments
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        page.wait_for_timeout(1500)

        # Find the comment by author and click reply
        comment_sections = page.locator(f'div:has(a[href*="/@"]:has-text("{comment_author}"))').all()

        for section in comment_sections:
            try:
                # Look for reply button
                reply_btn = section.locator('button:has-text("Reply"), a:has-text("Reply")').first
                if reply_btn.count() > 0:
                    reply_btn.click()
                    page.wait_for_timeout(1000)

                    # Find reply input
                    reply_input = page.locator('textarea:visible, div[contenteditable="true"]:visible').first
                    if reply_input.count() > 0:
                        reply_input.fill(reply_text)
                        page.wait_for_timeout(500)

                        # Submit reply
                        submit_btn = page.locator('button:has-text("Post"):visible, button:has-text("Reply"):visible, button[type="submit"]:visible').first
                        if submit_btn.count() > 0:
                            submit_btn.click()
                            page.wait_for_timeout(2000)
                            print(f"Reply posted to {comment_author}!")
                            return True
                    break
            except:
                continue

        print(f"Could not find comment by {comment_author} to reply to")
        return False

    except Exception as e:
        print(f"Error posting reply: {e}")
        return False
    finally:
        page.close()


def create_post(context: BrowserContext, community_url: str, title: str, content: str) -> bool:
    """Create a new post in the community"""
    page = context.new_page()

    try:
        # Navigate to community
        community_url = community_url.rstrip('/')
        page.goto(community_url)
        page.wait_for_load_state("domcontentloaded")
        page.wait_for_timeout(3000)

        # Step 1: Click "Write something" to open post form
        write_area = page.locator('text=Write something').first
        if write_area.count() == 0:
            print("Could not find Write something area")
            return False

        write_area.click()
        page.wait_for_timeout(2500)

        # Step 2: Fill in title
        title_input = page.locator('input[placeholder*="Title"]').first
        if title_input.count() > 0:
            title_input.fill(title)
            page.wait_for_timeout(500)

        # Step 3: Fill in content
        content_input = page.locator('div[contenteditable="true"]').first
        if content_input.count() > 0:
            content_input.click()
            page.keyboard.type(content, delay=5)
            page.wait_for_timeout(1000)

        # Step 4: Handle category selection
        cat_selector = page.locator('text=Select a category').first
        if cat_selector.count() > 0:
            cat_selector.click(force=True)
            page.wait_for_timeout(1500)

            # Click category using JavaScript with event dispatch
            page.evaluate('''() => {
                const items = document.querySelectorAll('[class*="DropdownItem"]');
                for (let item of items) {
                    if (item.innerText.trim().startsWith('All') || item.innerText.trim().startsWith('General')) {
                        item.click();
                        item.dispatchEvent(new MouseEvent('mousedown', {bubbles: true}));
                        item.dispatchEvent(new MouseEvent('mouseup', {bubbles: true}));
                        return true;
                    }
                }
                return false;
            }''')
            page.wait_for_timeout(1500)

            # Click outside to close dropdown if still open
            page.mouse.click(100, 100)
            page.wait_for_timeout(500)

        # Step 5: Submit post
        post_btn = page.locator('button:has-text("Post")').first
        if post_btn.count() > 0:
            post_btn.click(force=True)
            page.wait_for_timeout(3000)

            # Also try form submit via JS as backup
            page.evaluate('''() => {
                const forms = document.querySelectorAll('form');
                for (let form of forms) {
                    form.submit();
                }
            }''')
            page.wait_for_timeout(3000)

            print(f"Post '{title}' created successfully!")
            return True

        print("Could not find submit button")
        return False

    except Exception as e:
        print(f"Error creating post: {e}")
        return False
    finally:
        page.close()


def run_full_engagement(community_url: str, headless: bool = False) -> dict:
    """
    Run full engagement workflow:
    1. Scrape community
    2. Analyze posts
    3. Return engagement opportunities
    """
    from skool_auth import get_authenticated_context
    from skool_scraper import scrape_community_posts, save_posts_to_json
    from analyze_posts import analyze_for_comment_opportunities, analyze_content_patterns

    print(f"\n{'='*60}")
    print(f"AUTOMATED ENGAGEMENT FOR: {community_url}")
    print(f"{'='*60}\n")

    playwright, browser, context = get_authenticated_context(headless=headless)

    try:
        # Step 1: Scrape posts
        print("Step 1: Scraping community posts...")
        posts = scrape_community_posts(context, community_url, max_posts=20)
        save_posts_to_json(posts)
        print(f"Found {len(posts)} posts\n")

        # Step 2: Analyze for opportunities
        print("Step 2: Analyzing engagement opportunities...")
        analyzed = analyze_for_comment_opportunities(posts, mode="balanced")
        patterns = analyze_content_patterns(posts)

        # Step 3: Get top post for commenting
        top_posts = analyzed[:3]

        # Step 4: Scrape comments from top post
        print("\nStep 3: Getting comments from top posts...")
        posts_with_comments = []
        for post in top_posts:
            post_data = scrape_post_with_comments(context, post['url'])
            posts_with_comments.append(post_data)

        # Return context and browser for later use
        return {
            'playwright': playwright,
            'browser': browser,
            'context': context,
            'community_url': community_url,
            'posts': posts,
            'analyzed': analyzed,
            'patterns': patterns,
            'top_posts_with_comments': posts_with_comments
        }

    except Exception as e:
        browser.close()
        playwright.stop()
        raise e


def cleanup(engagement_data: dict):
    """Clean up browser resources"""
    try:
        engagement_data['browser'].close()
        engagement_data['playwright'].stop()
    except:
        pass


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python auto_engage.py <community_url>")
        sys.exit(1)

    url = sys.argv[1]
    data = run_full_engagement(url, headless=False)

    print("\n" + "="*60)
    print("ENGAGEMENT OPPORTUNITIES")
    print("="*60)

    for i, post in enumerate(data['top_posts_with_comments'], 1):
        print(f"\n{i}. {post['title']}")
        print(f"   URL: {post['url']}")
        print(f"   Comments: {len(post['comments'])}")
        for j, c in enumerate(post['comments'], 1):
            print(f"   [{j}] {c['author']}: {c['content'][:80]}...")

    cleanup(data)
