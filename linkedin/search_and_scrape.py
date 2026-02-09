"""
LinkedIn Search and Bulk Scrape
Searches for profiles by keyword and scrapes them
"""

import json
import time
import csv
import sys
import re
from pathlib import Path
from datetime import datetime

# Setup paths
BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(BASE_DIR / "approach2_playwright" / "execution"))

from approach2_playwright.execution.anti_detection import AntiDetection, RateLimiter
from dotenv import load_dotenv
import os

# Load env
load_dotenv(BASE_DIR / "approach2_playwright" / ".env.approach2")

OUTPUT_DIR = BASE_DIR / ".tmp" / "ai_automation_scrape"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


class LinkedInSearchScraper:
    """Search LinkedIn and scrape profiles"""

    def __init__(self, headless: bool = False):
        self.headless = headless
        self.anti_detection = AntiDetection()
        self.rate_limiter = RateLimiter(
            actions_per_hour=30,
            profiles_per_session=100,
        )
        self.playwright = None
        self.browser = None
        self.context = None

    def start_browser(self):
        """Start browser and login"""
        from playwright.sync_api import sync_playwright

        email = os.getenv("LINKEDIN_EMAIL")
        password = os.getenv("LINKEDIN_PASSWORD")

        if not email or not password:
            raise ValueError("LINKEDIN_EMAIL and LINKEDIN_PASSWORD required")

        self.playwright = sync_playwright().start()

        viewport = self.anti_detection.get_viewport_size()
        self.browser = self.playwright.chromium.launch(
            headless=self.headless,
            args=self.anti_detection.get_browser_args()
        )

        session_file = OUTPUT_DIR / "linkedin_session.json"

        # Try existing session
        if session_file.exists():
            try:
                self.context = self.browser.new_context(
                    storage_state=str(session_file),
                    viewport={"width": viewport[0], "height": viewport[1]},
                    user_agent=self.anti_detection.user_agent
                )
                page = self.context.new_page()
                page.goto("https://www.linkedin.com/feed/", timeout=60000)
                time.sleep(3)
                if "/feed" in page.url:
                    print("Reusing existing session")
                    page.close()
                    return
                page.close()
                self.context.close()
            except:
                pass

        # Fresh login
        self.context = self.browser.new_context(
            viewport={"width": viewport[0], "height": viewport[1]},
            user_agent=self.anti_detection.user_agent
        )

        page = self.context.new_page()
        print("Logging in to LinkedIn...")
        page.goto("https://www.linkedin.com/login", timeout=60000)
        time.sleep(2)

        page.fill('#username', email)
        page.fill('#password', password)
        page.click('button[type="submit"]')
        time.sleep(5)

        for _ in range(10):
            if "/feed" in page.url:
                break
            time.sleep(1)

        self.context.storage_state(path=str(session_file))
        print("Login successful!")
        page.close()

    def search_profiles(self, keyword: str, max_results: int = 100) -> list:
        """Search for profiles by keyword"""
        print(f"\nSearching for: {keyword}")

        from urllib.parse import quote
        search_url = f"https://www.linkedin.com/search/results/people/?keywords={quote(keyword)}&origin=SWITCH_SEARCH_VERTICAL"

        page = self.context.new_page()
        profile_urls = []

        try:
            page.goto(search_url, timeout=60000)
            time.sleep(5)

            pages_scraped = 0
            max_pages = (max_results // 10) + 1

            while len(profile_urls) < max_results and pages_scraped < max_pages:
                print(f"  Page {pages_scraped + 1}: Found {len(profile_urls)} profiles so far...")

                # Scroll to load all results on page
                for _ in range(3):
                    page.mouse.wheel(0, 500)
                    time.sleep(1)

                # Find profile links
                links = page.locator('a[href*="/in/"]')

                for i in range(links.count()):
                    try:
                        href = links.nth(i).get_attribute('href')
                        if href and '/in/' in href and href not in profile_urls:
                            # Clean up URL
                            clean_url = href.split('?')[0]
                            if clean_url.startswith('https://www.linkedin.com/in/'):
                                profile_urls.append(clean_url)
                    except:
                        pass

                # Try to go to next page
                pages_scraped += 1

                if len(profile_urls) >= max_results:
                    break

                # Click next button
                try:
                    next_btn = page.locator('button[aria-label="Next"]')
                    if next_btn.count() > 0 and next_btn.first.is_enabled():
                        next_btn.first.click()
                        time.sleep(4)
                    else:
                        break
                except:
                    break

        except Exception as e:
            print(f"Search error: {e}")
        finally:
            page.close()

        # Remove duplicates
        profile_urls = list(dict.fromkeys(profile_urls))[:max_results]
        print(f"  Found {len(profile_urls)} unique profiles")

        return profile_urls

    def scrape_profile(self, profile_url: str) -> dict:
        """Scrape a single profile"""
        page = self.context.new_page()
        profile_data = {}

        try:
            page.goto(profile_url, timeout=30000)
            time.sleep(4)

            # Check for blocks
            if "authwall" in page.url or "login" in page.url:
                return {"name": "AUTH_REQUIRED", "profile_url": profile_url, "scraped_at": datetime.now().isoformat()}

            page_title = page.title()
            if "Content Unavailable" in page_title:
                return {"name": "CONTENT_UNAVAILABLE", "profile_url": profile_url, "scraped_at": datetime.now().isoformat()}

            # Name
            name = ""
            try:
                h1 = page.locator('h1').first
                if h1.count() > 0:
                    name = h1.inner_text().strip()
            except:
                pass

            # Headline
            headline = ""
            try:
                hl = page.locator('.text-body-medium').first
                if hl.count() > 0:
                    headline = hl.inner_text().strip()
            except:
                pass

            # Location
            location = ""
            try:
                loc = page.locator('.text-body-small.inline.t-black--light').first
                if loc.count() > 0:
                    location = loc.inner_text().strip()
            except:
                pass

            # Connections/Followers
            connections = ""
            try:
                page_text = page.inner_text('body')
                conn_match = re.search(r'(\d+[\d,]*)\s*(?:connections?|followers?)', page_text, re.IGNORECASE)
                if conn_match:
                    connections = conn_match.group(0)
            except:
                pass

            # About
            about = ""
            try:
                about_section = page.locator('#about')
                if about_section.count() > 0:
                    about_section.scroll_into_view_if_needed()
                    time.sleep(1)
                    # Try to get about text
                    about_text = page.locator('#about').locator('..').locator('..').locator('span[aria-hidden="true"]')
                    if about_text.count() > 0:
                        about = about_text.first.inner_text().strip()[:500]
            except:
                pass

            # Company
            company = ""
            try:
                exp_section = page.locator('#experience')
                if exp_section.count() > 0:
                    company_el = page.locator('#experience').locator('..').locator('..').locator('span.t-14.t-normal')
                    if company_el.count() > 0:
                        company = company_el.first.inner_text().strip()
            except:
                pass

            profile_data = {
                "name": name,
                "headline": headline,
                "location": location,
                "company": company,
                "connections": connections,
                "about": about,
                "profile_url": profile_url,
                "scraped_at": datetime.now().isoformat()
            }

            self.rate_limiter.record_profile_scrape()

        except Exception as e:
            profile_data = {
                "name": "ERROR",
                "headline": str(e)[:100],
                "profile_url": profile_url,
                "scraped_at": datetime.now().isoformat()
            }
        finally:
            page.close()

        return profile_data

    def scrape_profiles(self, profile_urls: list) -> list:
        """Scrape multiple profiles"""
        results = []
        total = len(profile_urls)

        print(f"\nScraping {total} profiles...")

        for i, url in enumerate(profile_urls):
            if not self.rate_limiter.can_scrape_profile():
                print(f"\nRate limit reached after {i} profiles.")
                break

            print(f"[{i+1}/{total}] {url.split('/in/')[-1][:30]}...", end=" ")

            profile = self.scrape_profile(url)
            results.append(profile)

            name = profile.get("name", "")
            if name and name not in ["ERROR", "AUTH_REQUIRED", "CONTENT_UNAVAILABLE"]:
                print(f"OK - {name[:30]}")
            else:
                print(f"SKIP - {name}")

            # Delay
            time.sleep(self.anti_detection.human_delay(2.5))

            # Break every 15 profiles
            if i > 0 and i % 15 == 0:
                print("  Taking a short break...")
                time.sleep(10)

        return results

    def close(self):
        if self.context:
            self.context.close()
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()


def export_to_csv(profiles: list, filename: str = "ai_automation_profiles.csv"):
    """Export profiles to CSV"""
    csv_file = OUTPUT_DIR / filename

    headers = ["Name", "Headline", "Company", "Location", "Connections", "About", "Profile URL", "Scraped At"]

    # Filter out errors
    valid_profiles = [p for p in profiles if p.get("name") not in ["ERROR", "AUTH_REQUIRED", "CONTENT_UNAVAILABLE", ""]]

    with open(csv_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(headers)

        for p in valid_profiles:
            writer.writerow([
                p.get("name", ""),
                p.get("headline", ""),
                p.get("company", ""),
                p.get("location", ""),
                p.get("connections", ""),
                (p.get("about", "") or "")[:300],
                p.get("profile_url", ""),
                p.get("scraped_at", "")
            ])

    print(f"\n{'='*60}")
    print(f"EXPORTED {len(valid_profiles)} profiles to:")
    print(f"  {csv_file}")
    print(f"{'='*60}")

    return csv_file


def main():
    print("=" * 60)
    print("LinkedIn AI AUTOMATION Profile Scraper")
    print("=" * 60)

    # Search terms for AI Automation niche
    search_terms = [
        "AI automation specialist",
        "AI automation consultant",
        "automation AI engineer",
        "AI workflow automation",
        "business automation AI"
    ]

    scraper = LinkedInSearchScraper(headless=False)

    try:
        scraper.start_browser()

        all_profile_urls = []

        # Search for each term
        for term in search_terms:
            urls = scraper.search_profiles(term, max_results=25)
            all_profile_urls.extend(urls)
            time.sleep(5)  # Pause between searches

        # Remove duplicates
        all_profile_urls = list(dict.fromkeys(all_profile_urls))
        print(f"\nTotal unique profiles found: {len(all_profile_urls)}")

        # Save URLs to file
        urls_file = OUTPUT_DIR / "found_profile_urls.txt"
        with open(urls_file, "w") as f:
            f.write("\n".join(all_profile_urls))
        print(f"Saved URLs to: {urls_file}")

        # Scrape all profiles
        if all_profile_urls:
            profiles = scraper.scrape_profiles(all_profile_urls[:100])  # Max 100

            # Save JSON
            json_file = OUTPUT_DIR / "ai_automation_profiles.json"
            with open(json_file, "w", encoding="utf-8") as f:
                json.dump(profiles, f, indent=2, ensure_ascii=False)

            # Export to CSV
            export_to_csv(profiles)

    finally:
        scraper.close()

    print("\nDone!")


if __name__ == "__main__":
    main()