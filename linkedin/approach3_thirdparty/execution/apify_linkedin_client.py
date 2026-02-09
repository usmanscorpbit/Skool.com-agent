"""
Apify LinkedIn Client
Interfaces with Apify actors for LinkedIn data extraction
https://apify.com/
"""

import os
import json
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime
from apify_client import ApifyClient
from dotenv import load_dotenv

# Load approach-specific env
APPROACH_DIR = Path(__file__).parent.parent
BASE_DIR = APPROACH_DIR.parent.parent
ENV_FILE = APPROACH_DIR / ".env.approach3"

if ENV_FILE.exists():
    load_dotenv(ENV_FILE)
else:
    load_dotenv(BASE_DIR / ".env")

OUTPUT_DIR = BASE_DIR / ".tmp" / "approach3"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


class ApifyLinkedInClient:
    """
    Client for Apify LinkedIn actors.

    Popular Apify LinkedIn actors:
    - LinkedIn Profile Scraper
    - LinkedIn Company Scraper
    - LinkedIn Jobs Scraper
    - LinkedIn Post Scraper
    """

    # Popular LinkedIn actor IDs on Apify
    DEFAULT_ACTORS = {
        "profile_scraper": "curious_coder/linkedin-profile-scraper",
        "company_scraper": "anchor/linkedin-company-scraper",
        "post_scraper": "curious_coder/linkedin-post-scraper",
        "search_scraper": "bebity/linkedin-search-scraper",
    }

    def __init__(self, api_token: Optional[str] = None):
        """
        Initialize Apify client.

        Args:
            api_token: Apify API token (or from env APIFY_API_TOKEN)
        """
        self.api_token = api_token or os.getenv("APIFY_API_TOKEN")
        if not self.api_token:
            raise ValueError("APIFY_API_TOKEN is required")

        self.client = ApifyClient(self.api_token)

        # Custom actor IDs (override defaults via env)
        self.actor_ids = {
            "profile_scraper": os.getenv(
                "APIFY_PROFILE_SCRAPER_ID",
                self.DEFAULT_ACTORS["profile_scraper"]
            ),
            "company_scraper": os.getenv(
                "APIFY_COMPANY_SCRAPER_ID",
                self.DEFAULT_ACTORS["company_scraper"]
            ),
            "post_scraper": os.getenv(
                "APIFY_POST_SCRAPER_ID",
                self.DEFAULT_ACTORS["post_scraper"]
            ),
            "search_scraper": os.getenv(
                "APIFY_SEARCH_SCRAPER_ID",
                self.DEFAULT_ACTORS["search_scraper"]
            ),
        }

    def run_actor(
        self,
        actor_id: str,
        run_input: Dict[str, Any],
        timeout_secs: int = 300
    ) -> List[Dict]:
        """
        Run an Apify actor and get results.

        Args:
            actor_id: Actor ID (e.g., "curious_coder/linkedin-profile-scraper")
            run_input: Input configuration for the actor
            timeout_secs: Maximum wait time

        Returns:
            List of result items
        """
        print(f"Running actor: {actor_id}")

        # Start the actor
        run = self.client.actor(actor_id).call(
            run_input=run_input,
            timeout_secs=timeout_secs
        )

        # Get results from the default dataset
        dataset_items = self.client.dataset(run["defaultDatasetId"]).list_items().items

        return dataset_items

    def scrape_profiles(
        self,
        profile_urls: List[str],
        cookie: Optional[str] = None
    ) -> List[Dict]:
        """
        Scrape LinkedIn profiles.

        Args:
            profile_urls: List of profile URLs
            cookie: LinkedIn session cookie (li_at)

        Returns:
            List of profile data
        """
        actor_id = self.actor_ids["profile_scraper"]

        run_input = {
            "profileUrls": profile_urls,
            "proxy": {
                "useApifyProxy": True,
                "apifyProxyGroups": ["RESIDENTIAL"]
            }
        }

        if cookie:
            run_input["cookie"] = cookie

        results = self.run_actor(actor_id, run_input)

        # Save results
        output_file = OUTPUT_DIR / "apify_profiles.json"
        with open(output_file, "w") as f:
            json.dump(results, f, indent=2)
        print(f"Saved {len(results)} profiles to {output_file}")

        return results

    def scrape_companies(
        self,
        company_urls: List[str],
        cookie: Optional[str] = None
    ) -> List[Dict]:
        """
        Scrape LinkedIn company pages.

        Args:
            company_urls: List of company page URLs
            cookie: LinkedIn session cookie

        Returns:
            List of company data
        """
        actor_id = self.actor_ids["company_scraper"]

        run_input = {
            "urls": company_urls,
            "proxy": {
                "useApifyProxy": True
            }
        }

        if cookie:
            run_input["cookie"] = cookie

        results = self.run_actor(actor_id, run_input)

        # Save results
        output_file = OUTPUT_DIR / "apify_companies.json"
        with open(output_file, "w") as f:
            json.dump(results, f, indent=2)

        return results

    def scrape_posts(
        self,
        profile_urls: List[str] = None,
        hashtags: List[str] = None,
        max_posts: int = 50,
        cookie: Optional[str] = None
    ) -> List[Dict]:
        """
        Scrape LinkedIn posts.

        Args:
            profile_urls: Scrape posts from these profiles
            hashtags: Scrape posts with these hashtags
            max_posts: Maximum posts to return
            cookie: LinkedIn session cookie

        Returns:
            List of post data
        """
        actor_id = self.actor_ids["post_scraper"]

        run_input = {
            "maxPosts": max_posts,
            "proxy": {
                "useApifyProxy": True
            }
        }

        if profile_urls:
            run_input["profileUrls"] = profile_urls
        if hashtags:
            run_input["hashtags"] = hashtags
        if cookie:
            run_input["cookie"] = cookie

        results = self.run_actor(actor_id, run_input)

        # Save results
        output_file = OUTPUT_DIR / "apify_posts.json"
        with open(output_file, "w") as f:
            json.dump(results, f, indent=2)
        print(f"Saved {len(results)} posts to {output_file}")

        return results

    def search_profiles(
        self,
        keywords: str,
        location: Optional[str] = None,
        industry: Optional[str] = None,
        max_results: int = 100,
        cookie: Optional[str] = None
    ) -> List[Dict]:
        """
        Search for LinkedIn profiles.

        Args:
            keywords: Search keywords
            location: Filter by location
            industry: Filter by industry
            max_results: Maximum profiles to return
            cookie: LinkedIn session cookie

        Returns:
            List of profile search results
        """
        actor_id = self.actor_ids["search_scraper"]

        run_input = {
            "searchType": "people",
            "keywords": keywords,
            "maxResults": max_results,
            "proxy": {
                "useApifyProxy": True,
                "apifyProxyGroups": ["RESIDENTIAL"]
            }
        }

        if location:
            run_input["location"] = location
        if industry:
            run_input["industry"] = industry
        if cookie:
            run_input["cookie"] = cookie

        results = self.run_actor(actor_id, run_input)

        # Save results
        output_file = OUTPUT_DIR / "apify_search_results.json"
        with open(output_file, "w") as f:
            json.dump(results, f, indent=2)
        print(f"Saved {len(results)} search results to {output_file}")

        return results

    def get_actor_info(self, actor_id: str) -> Dict:
        """Get information about an actor"""
        return self.client.actor(actor_id).get()

    def list_runs(self, actor_id: str, limit: int = 10) -> List[Dict]:
        """List recent runs of an actor"""
        runs = self.client.actor(actor_id).runs().list(limit=limit)
        return runs.items


def get_client() -> ApifyLinkedInClient:
    """Get configured Apify client"""
    return ApifyLinkedInClient()


if __name__ == "__main__":
    # Test connection
    try:
        client = get_client()

        # Test with a sample profile (public figure)
        print("Testing Apify LinkedIn client...")
        print("Actor IDs configured:")
        for name, actor_id in client.actor_ids.items():
            print(f"  {name}: {actor_id}")

        # Uncomment to test actual scraping (uses Apify credits):
        # results = client.scrape_profiles([
        #     "https://www.linkedin.com/in/satlovelace"
        # ])
        # print(f"Scraped {len(results)} profiles")

    except Exception as e:
        print(f"Error: {e}")
        print("\nMake sure APIFY_API_TOKEN is set in .env.approach3")
