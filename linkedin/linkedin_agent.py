"""
LinkedIn Automation Agent
Unified interface for all LinkedIn automation tasks:
- Profile scraping
- Post creation
- Messaging
- Commenting
- Post discovery

Usage:
    python linkedin_agent.py scrape --search "AI automation" --count 50
    python linkedin_agent.py post --content "Your post here" --hashtags "ai,automation"
    python linkedin_agent.py message --csv profiles.csv --template "Hi {name}..."
    python linkedin_agent.py comment --hashtags "ai,automation" --count 10
    python linkedin_agent.py find-posts --hashtags "startup,entrepreneur"
"""

import argparse
import json
import csv
import time
from pathlib import Path
from datetime import datetime
from typing import List, Optional

# Setup path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent))

from approach2_playwright.execution.linkedin_browser_auth import LinkedInAuth, get_authenticated_context
from approach2_playwright.execution.anti_detection import AntiDetection, RateLimiter
from shared.types import LinkedInProfile

BASE_DIR = Path(__file__).parent
OUTPUT_DIR = BASE_DIR / ".tmp" / "agent_output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


class LinkedInAgent:
    """
    Unified LinkedIn automation agent.
    Provides simple interface for all automation tasks.
    """

    def __init__(self, headless: bool = False):
        self.headless = headless
        self.playwright = None
        self.browser = None
        self.context = None
        self.auth = None

    def _ensure_authenticated(self):
        """Ensure browser is authenticated"""
        if not self.context:
            self.playwright, self.browser, self.context, self.auth = get_authenticated_context(self.headless)

    def close(self):
        """Close browser and cleanup"""
        if self.auth:
            self.auth.close()
            self.auth = None
            self.context = None
            self.browser = None
            self.playwright = None

    # =========================================================================
    # SCRAPING
    # =========================================================================

    def scrape_profiles_from_search(
        self,
        search_terms: List[str],
        max_profiles: int = 50,
        output_csv: str = None
    ) -> List[dict]:
        """
        Search LinkedIn and scrape profiles.

        Args:
            search_terms: Keywords to search
            max_profiles: Maximum profiles to scrape
            output_csv: Output CSV filename (optional)

        Returns:
            List of scraped profile dicts
        """
        from search_and_scrape import LinkedInSearchScraper

        scraper = LinkedInSearchScraper(headless=self.headless)

        try:
            # Start browser and login
            scraper.start_browser()

            # Search for profiles using each search term
            print(f"Searching for profiles: {search_terms}")
            all_profile_urls = []

            for term in search_terms:
                urls = scraper.search_profiles(term, max_results=max_profiles)
                all_profile_urls.extend(urls)

            # Deduplicate
            profile_urls = list(dict.fromkeys(all_profile_urls))

            if not profile_urls:
                print("No profiles found")
                return []

            print(f"Found {len(profile_urls)} unique profile URLs")

            # Scrape profiles (limit to max_profiles)
            profiles = scraper.scrape_profiles(profile_urls[:max_profiles])

            # Export to CSV
            csv_file = output_csv or f"scraped_profiles_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            csv_path = OUTPUT_DIR / csv_file

            self._export_profiles_to_csv(profiles, csv_path)
            print(f"\nExported {len(profiles)} profiles to: {csv_path}")

            return profiles

        finally:
            scraper.close()

    def scrape_profiles_from_urls(
        self,
        profile_urls: List[str],
        output_csv: str = None
    ) -> List[dict]:
        """
        Scrape specific profile URLs.

        Args:
            profile_urls: List of LinkedIn profile URLs
            output_csv: Output CSV filename

        Returns:
            List of scraped profile dicts
        """
        from bulk_scrape_to_sheet import BulkProfileScraper

        scraper = BulkProfileScraper(headless=self.headless)

        try:
            profiles = scraper.scrape_multiple(profile_urls)

            # Export to CSV
            csv_file = output_csv or f"scraped_profiles_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            csv_path = OUTPUT_DIR / csv_file

            self._export_profiles_to_csv(profiles, csv_path)
            print(f"\nExported {len(profiles)} profiles to: {csv_path}")

            return profiles

        finally:
            scraper.close()

    def _export_profiles_to_csv(self, profiles: List[dict], csv_path: Path):
        """Export profiles to CSV"""
        headers = ["Name", "Headline", "Location", "Connections", "Profile URL", "Scraped At"]

        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(headers)

            for p in profiles:
                writer.writerow([
                    p.get("name", ""),
                    p.get("headline", ""),
                    p.get("location", ""),
                    p.get("connections", ""),
                    p.get("profile_url", ""),
                    p.get("scraped_at", "")
                ])

    # =========================================================================
    # POST CREATION
    # =========================================================================

    def create_post(
        self,
        content: str,
        hashtags: List[str] = None,
        media_paths: List[str] = None
    ) -> dict:
        """
        Create a LinkedIn post.

        Args:
            content: Post body text
            hashtags: List of hashtags (without #)
            media_paths: Paths to images/videos to attach

        Returns:
            Dict with success status
        """
        from approach2_playwright.execution.linkedin_content_poster import create_post

        result = create_post(
            content=content,
            hashtags=hashtags,
            media_paths=media_paths,
            headless=self.headless
        )

        self._log_action("post_created", {
            "content": content[:100],
            "hashtags": hashtags,
            "result": result
        })

        return result

    # =========================================================================
    # MESSAGING
    # =========================================================================

    def send_connection_request(
        self,
        profile_url: str,
        note: str = None
    ) -> dict:
        """
        Send a connection request.

        Args:
            profile_url: Profile URL
            note: Optional personalized note (max 300 chars)

        Returns:
            Dict with success status
        """
        from approach2_playwright.execution.linkedin_messenger import send_connection_request

        result = send_connection_request(
            profile_url=profile_url,
            note=note,
            headless=self.headless
        )

        self._log_action("connection_request", {
            "profile_url": profile_url,
            "note": note[:50] if note else None,
            "result": result
        })

        return result

    def send_message(
        self,
        profile_url: str,
        message: str
    ) -> dict:
        """
        Send a direct message to a connection.

        Args:
            profile_url: Profile URL
            message: Message text

        Returns:
            Dict with success status
        """
        from approach2_playwright.execution.linkedin_messenger import send_message

        result = send_message(
            profile_url=profile_url,
            message=message,
            headless=self.headless
        )

        self._log_action("message_sent", {
            "profile_url": profile_url,
            "message": message[:50],
            "result": result
        })

        return result

    def send_bulk_messages(
        self,
        profiles_csv: str,
        message_template: str,
        max_messages: int = 25,
        connection_request: bool = True
    ) -> List[dict]:
        """
        Send messages to multiple profiles from CSV.

        Args:
            profiles_csv: Path to CSV with profile URLs
            message_template: Message template with {name}, {company} placeholders
            max_messages: Maximum messages to send (default 25/day limit)
            connection_request: Send as connection request if not connected

        Returns:
            List of results
        """
        self._ensure_authenticated()

        from approach2_playwright.execution.linkedin_messenger import LinkedInMessenger

        messenger = LinkedInMessenger(
            context=self.context,
            anti_detection=self.auth.anti_detection,
            rate_limiter=self.auth.rate_limiter
        )

        # Load profiles from CSV
        profiles = self._load_profiles_from_csv(profiles_csv)

        if not profiles:
            return [{"error": "No profiles loaded from CSV"}]

        results = []

        for i, profile in enumerate(profiles[:max_messages]):
            if not self.auth.rate_limiter.can_send_message():
                print("Daily message limit reached")
                break

            # Personalize message
            first_name = profile.get("name", "").split()[0] if profile.get("name") else "there"
            message = message_template.replace("{name}", first_name)
            message = message.replace("{company}", profile.get("company", "your company"))
            message = message.replace("{headline}", profile.get("headline", ""))

            profile_url = profile.get("profile_url", "")

            print(f"[{i+1}/{min(len(profiles), max_messages)}] Messaging: {profile.get('name', profile_url)}")

            if connection_request:
                result = messenger.send_connection_request(profile_url, message[:300])
            else:
                result = messenger.send_message(profile_url, message)

            result["profile_name"] = profile.get("name", "")
            results.append(result)

            # Wait between messages
            self.auth.anti_detection.long_wait()

        # Log results
        self._log_action("bulk_messages", {
            "total_attempted": len(results),
            "successful": sum(1 for r in results if r.get("success")),
            "failed": sum(1 for r in results if not r.get("success"))
        })

        return results

    def _load_profiles_from_csv(self, csv_path: str) -> List[dict]:
        """Load profiles from CSV file"""
        profiles = []

        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Normalize column names
                profile = {
                    "name": row.get("Name") or row.get("name", ""),
                    "headline": row.get("Headline") or row.get("headline", ""),
                    "profile_url": row.get("Profile URL") or row.get("profile_url", ""),
                    "company": row.get("Company") or row.get("company", ""),
                    "location": row.get("Location") or row.get("location", "")
                }
                if profile["profile_url"]:
                    profiles.append(profile)

        return profiles

    # =========================================================================
    # COMMENTING
    # =========================================================================

    def find_posts(
        self,
        hashtags: List[str] = None,
        keywords: List[str] = None,
        include_feed: bool = True,
        max_posts: int = 20
    ) -> List[dict]:
        """
        Find posts to comment on.

        Args:
            hashtags: Hashtags to search
            keywords: Keywords to search
            include_feed: Include posts from main feed
            max_posts: Maximum posts per source

        Returns:
            List of found posts
        """
        from approach2_playwright.execution.linkedin_post_finder import find_posts

        result = find_posts(
            hashtags=hashtags,
            keywords=keywords,
            include_feed=include_feed,
            max_per_source=max_posts,
            headless=self.headless
        )

        # Convert posts to dicts
        posts = [p.to_dict() for p in result.posts]

        # Save to file
        output_file = OUTPUT_DIR / f"found_posts_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(output_file, "w") as f:
            json.dump(posts, f, indent=2, default=str)

        print(f"Found {len(posts)} posts, saved to: {output_file}")

        return posts

    def comment_on_post(
        self,
        post_url: str,
        comment: str
    ) -> dict:
        """
        Post a comment on a LinkedIn post.

        Args:
            post_url: URL of the post
            comment: Comment text

        Returns:
            Dict with success status
        """
        from approach2_playwright.execution.linkedin_commenter import post_comment

        result = post_comment(
            post_url=post_url,
            comment=comment,
            headless=self.headless
        )

        self._log_action("comment_posted", {
            "post_url": post_url,
            "comment": comment[:50],
            "result": result
        })

        return result

    def auto_comment(
        self,
        hashtags: List[str],
        comments: List[str],
        max_comments: int = 10
    ) -> List[dict]:
        """
        Automatically find posts and comment on them.

        Args:
            hashtags: Hashtags to search for posts
            comments: List of comments to use (cycled)
            max_comments: Maximum comments to post

        Returns:
            List of results
        """
        self._ensure_authenticated()

        from approach2_playwright.execution.linkedin_post_finder import LinkedInPostFinder
        from approach2_playwright.execution.linkedin_commenter import LinkedInCommenter

        finder = LinkedInPostFinder(
            context=self.context,
            anti_detection=self.auth.anti_detection,
            rate_limiter=self.auth.rate_limiter
        )

        commenter = LinkedInCommenter(
            context=self.context,
            anti_detection=self.auth.anti_detection,
            rate_limiter=self.auth.rate_limiter
        )

        # Find posts
        all_posts = []
        for tag in hashtags:
            print(f"Finding posts with #{tag}...")
            posts = finder.find_posts_by_hashtag(tag, max_posts=max_comments)
            all_posts.extend(posts)
            self.auth.anti_detection.medium_wait()

        if not all_posts:
            return [{"error": "No posts found"}]

        # Comment on posts
        results = []

        for i, post in enumerate(all_posts[:max_comments]):
            if not self.auth.rate_limiter.can_post_comment():
                print("Daily comment limit reached")
                break

            comment = comments[i % len(comments)]

            print(f"[{i+1}/{min(len(all_posts), max_comments)}] Commenting on {post.author_name}'s post")

            result = commenter.post_comment(post.post_url, comment)
            result["post_author"] = post.author_name
            result["post_content"] = post.content[:100]
            results.append(result)

            self.auth.anti_detection.long_wait()

        # Log results
        self._log_action("auto_comment", {
            "hashtags": hashtags,
            "total_attempted": len(results),
            "successful": sum(1 for r in results if r.get("success")),
            "failed": sum(1 for r in results if not r.get("success"))
        })

        return results

    # =========================================================================
    # UTILITIES
    # =========================================================================

    def _log_action(self, action_type: str, data: dict):
        """Log an action to the agent log"""
        log_file = OUTPUT_DIR / "agent_log.json"

        log_entries = []
        if log_file.exists():
            with open(log_file) as f:
                log_entries = json.load(f)

        log_entries.append({
            "action": action_type,
            "data": data,
            "timestamp": datetime.now().isoformat()
        })

        with open(log_file, "w") as f:
            json.dump(log_entries, f, indent=2, default=str)


def main():
    """CLI entry point"""
    parser = argparse.ArgumentParser(
        description="LinkedIn Automation Agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Scrape profiles:
    python linkedin_agent.py scrape --search "AI automation" --count 50

  Create a post:
    python linkedin_agent.py post --content "Excited about AI!" --hashtags ai,automation

  Send messages from CSV:
    python linkedin_agent.py message --csv profiles.csv --template "Hi {name}, I'd love to connect!"

  Find posts and comment:
    python linkedin_agent.py comment --hashtags startup,entrepreneur --comments "Great insight!,Love this!"

  Find posts to review:
    python linkedin_agent.py find-posts --hashtags ai,ml --keywords "machine learning"
        """
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Scrape command
    scrape_parser = subparsers.add_parser("scrape", help="Scrape LinkedIn profiles")
    scrape_parser.add_argument("--search", type=str, help="Search terms (comma-separated)")
    scrape_parser.add_argument("--urls", type=str, help="File with profile URLs (one per line)")
    scrape_parser.add_argument("--count", type=int, default=50, help="Max profiles to scrape")
    scrape_parser.add_argument("--output", type=str, help="Output CSV filename")

    # Post command
    post_parser = subparsers.add_parser("post", help="Create a LinkedIn post")
    post_parser.add_argument("--content", type=str, required=True, help="Post content")
    post_parser.add_argument("--hashtags", type=str, help="Hashtags (comma-separated)")
    post_parser.add_argument("--media", type=str, help="Media file paths (comma-separated)")

    # Message command
    msg_parser = subparsers.add_parser("message", help="Send messages/connection requests")
    msg_parser.add_argument("--csv", type=str, required=True, help="CSV file with profiles")
    msg_parser.add_argument("--template", type=str, required=True, help="Message template")
    msg_parser.add_argument("--max", type=int, default=25, help="Max messages to send")
    msg_parser.add_argument("--direct", action="store_true", help="Send as direct message (not connection request)")

    # Comment command
    comment_parser = subparsers.add_parser("comment", help="Auto-comment on posts")
    comment_parser.add_argument("--hashtags", type=str, required=True, help="Hashtags to search (comma-separated)")
    comment_parser.add_argument("--comments", type=str, required=True, help="Comments to use (comma-separated)")
    comment_parser.add_argument("--max", type=int, default=10, help="Max comments to post")

    # Find posts command
    find_parser = subparsers.add_parser("find-posts", help="Find posts to engage with")
    find_parser.add_argument("--hashtags", type=str, help="Hashtags to search (comma-separated)")
    find_parser.add_argument("--keywords", type=str, help="Keywords to search (comma-separated)")
    find_parser.add_argument("--max", type=int, default=20, help="Max posts per source")

    # Global args
    parser.add_argument("--headless", action="store_true", help="Run browser in headless mode")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    agent = LinkedInAgent(headless=args.headless)

    try:
        if args.command == "scrape":
            if args.search:
                search_terms = [t.strip() for t in args.search.split(",")]
                agent.scrape_profiles_from_search(search_terms, args.count, args.output)
            elif args.urls:
                with open(args.urls) as f:
                    urls = [line.strip() for line in f if line.strip()]
                agent.scrape_profiles_from_urls(urls, args.output)
            else:
                print("Error: Provide --search or --urls")

        elif args.command == "post":
            hashtags = [t.strip() for t in args.hashtags.split(",")] if args.hashtags else None
            media = [p.strip() for p in args.media.split(",")] if args.media else None
            result = agent.create_post(args.content, hashtags, media)
            print(f"Result: {result}")

        elif args.command == "message":
            results = agent.send_bulk_messages(
                profiles_csv=args.csv,
                message_template=args.template,
                max_messages=args.max,
                connection_request=not args.direct
            )
            successful = sum(1 for r in results if r.get("success"))
            print(f"\nSent {successful}/{len(results)} messages successfully")

        elif args.command == "comment":
            hashtags = [t.strip() for t in args.hashtags.split(",")]
            comments = [c.strip() for c in args.comments.split(",")]
            results = agent.auto_comment(hashtags, comments, args.max)
            successful = sum(1 for r in results if r.get("success"))
            print(f"\nPosted {successful}/{len(results)} comments successfully")

        elif args.command == "find-posts":
            hashtags = [t.strip() for t in args.hashtags.split(",")] if args.hashtags else None
            keywords = [k.strip() for k in args.keywords.split(",")] if args.keywords else None
            posts = agent.find_posts(hashtags, keywords, max_posts=args.max)
            print(f"\nFound {len(posts)} posts")
            for p in posts[:5]:
                print(f"  - {p.get('author_name', 'Unknown')}: {p.get('content', '')[:60]}...")

    finally:
        agent.close()


if __name__ == "__main__":
    main()