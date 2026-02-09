"""
Bulk LinkedIn Profile Scraper with Google Sheets Export
Scrapes multiple profiles and exports to Google Sheets
"""

import json
import time
import sys
from pathlib import Path
from datetime import datetime

# Setup paths
BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(BASE_DIR / "approach2_playwright" / "execution"))
sys.path.insert(0, str(BASE_DIR.parent / "execution"))  # For export_to_sheet

from shared.types import LinkedInProfile, ApproachType, ConnectionDegree
from approach2_playwright.execution.anti_detection import AntiDetection, RateLimiter
from dotenv import load_dotenv
import os
import gspread
from google.oauth2.service_account import Credentials

# Load env
load_dotenv(BASE_DIR / "approach2_playwright" / ".env.approach2")

OUTPUT_DIR = BASE_DIR / ".tmp" / "bulk_scrape"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


class BulkProfileScraper:
    """Scrapes multiple LinkedIn profiles with rate limiting"""

    def __init__(self, headless: bool = False):
        self.headless = headless
        self.anti_detection = AntiDetection()
        self.rate_limiter = RateLimiter(
            actions_per_hour=int(os.getenv("ACTIONS_PER_HOUR", "20")),
            profiles_per_session=int(os.getenv("PROFILES_PER_SESSION", "50")),
        )
        self.playwright = None
        self.browser = None
        self.context = None
        self.profiles_scraped = []

    def start_browser(self):
        """Start browser and login"""
        from playwright.sync_api import sync_playwright

        email = os.getenv("LINKEDIN_EMAIL")
        password = os.getenv("LINKEDIN_PASSWORD")

        if not email or not password:
            raise ValueError("LINKEDIN_EMAIL and LINKEDIN_PASSWORD required in .env.approach2")

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
                page.goto("https://www.linkedin.com/feed/")
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
        page.goto("https://www.linkedin.com/login")
        time.sleep(2)

        page.fill('#username', email)
        page.fill('#password', password)
        page.click('button[type="submit"]')
        time.sleep(5)

        if "/feed" not in page.url and "/login" not in page.url:
            print("Waiting for login to complete...")
            time.sleep(10)

        self.context.storage_state(path=str(session_file))
        print("Login successful!")
        page.close()

    def scrape_profile(self, profile_url: str) -> dict:
        """Scrape a single profile"""
        page = self.context.new_page()
        profile_data = {}

        try:
            page.goto(profile_url, wait_until="networkidle", timeout=30000)
            time.sleep(5)

            # Check if we hit authwall
            if "authwall" in page.url or "login" in page.url:
                page.close()
                return {
                    "name": "AUTH_REQUIRED",
                    "headline": "Profile requires login",
                    "profile_url": profile_url,
                    "scraped_at": datetime.now().isoformat()
                }

            # Get page content for debugging
            page_title = page.title()

            # Name - the main h1 on profile pages
            name = ""
            try:
                # Most reliable: the h1 tag
                h1_el = page.locator('h1').first
                if h1_el.count() > 0:
                    name = h1_el.inner_text().strip()
            except:
                pass

            # Headline - usually in a div after the name
            headline = ""
            try:
                # Try getting text from the profile header area
                headline_el = page.locator('.text-body-medium').first
                if headline_el.count() > 0:
                    headline = headline_el.inner_text().strip()
            except:
                pass

            # Location
            location = ""
            try:
                loc_el = page.locator('.text-body-small.inline.t-black--light').first
                if loc_el.count() > 0:
                    location = loc_el.inner_text().strip()
            except:
                pass

            # Try alternative approach - get all text from main profile section
            if not name:
                try:
                    main_section = page.locator('main section').first
                    if main_section.count() > 0:
                        all_text = main_section.inner_text()
                        lines = [l.strip() for l in all_text.split('\n') if l.strip()]
                        if lines:
                            name = lines[0] if len(lines) > 0 else ""
                            headline = lines[1] if len(lines) > 1 else ""
                            location = lines[2] if len(lines) > 2 else ""
                except:
                    pass

            # About section
            about = ""
            try:
                about_section = page.locator('#about')
                if about_section.count() > 0:
                    about_section.scroll_into_view_if_needed()
                    time.sleep(1)
                    # Get the next sibling container
                    about_container = page.locator('#about').locator('..').locator('..').locator('div.display-flex')
                    if about_container.count() > 0:
                        about = about_container.first.inner_text().strip()[:500]
            except:
                pass

            # Connections
            connections = ""
            try:
                page_text = page.inner_text('body')
                import re
                conn_match = re.search(r'(\d+[\d,]*)\s*(?:connections?|followers?)', page_text, re.IGNORECASE)
                if conn_match:
                    connections = conn_match.group(0)
            except:
                pass

            profile_data = {
                "name": name,
                "headline": headline,
                "location": location,
                "about": about,
                "connections": connections,
                "profile_url": profile_url,
                "page_title": page_title,
                "scraped_at": datetime.now().isoformat()
            }

            self.rate_limiter.record_profile_scrape()

        except Exception as e:
            profile_data = {
                "name": "ERROR",
                "headline": str(e)[:200],
                "profile_url": profile_url,
                "scraped_at": datetime.now().isoformat()
            }
        finally:
            page.close()

        return profile_data

    def scrape_multiple(self, profile_urls: list, max_profiles: int = 100) -> list:
        """Scrape multiple profiles with rate limiting"""
        self.start_browser()
        results = []

        # Warm up session
        print("Warming up session...")
        page = self.context.new_page()
        try:
            page.goto("https://www.linkedin.com/feed/", timeout=60000)
            time.sleep(3)
            for _ in range(2):
                page.mouse.wheel(0, 300)
                time.sleep(2)
        except Exception as e:
            print(f"Warm up warning: {e}")
        finally:
            page.close()

        total = min(len(profile_urls), max_profiles)
        print(f"\nScraping {total} profiles...")

        for i, url in enumerate(profile_urls[:max_profiles]):
            if not self.rate_limiter.can_scrape_profile():
                print(f"\nRate limit reached after {i} profiles. Stopping.")
                break

            print(f"[{i+1}/{total}] Scraping: {url[:60]}...")

            profile = self.scrape_profile(url)
            results.append(profile)

            if profile.get("name") and profile["name"] != "ERROR":
                print(f"  [OK] {profile['name']} - {profile['headline'][:50] if profile.get('headline') else 'N/A'}")
            else:
                print(f"  [FAIL] {profile.get('headline', 'Unknown error')[:50]}")

            # Rate limiting delay
            delay = self.anti_detection.human_delay(3.0)
            time.sleep(delay)

            # Take breaks
            if i > 0 and i % 10 == 0:
                print(f"\n  Taking a short break...")
                time.sleep(self.anti_detection.human_delay(15.0))

        self.profiles_scraped = results

        # Save to JSON
        output_file = OUTPUT_DIR / "scraped_profiles.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"\nSaved {len(results)} profiles to {output_file}")

        return results

    def close(self):
        """Clean up browser"""
        if self.context:
            self.context.close()
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()


def export_to_csv(profiles: list):
    """Export profiles to CSV file"""
    import csv

    csv_file = OUTPUT_DIR / "scraped_profiles.csv"

    headers = ["Name", "Headline", "Location", "About", "Connections", "Profile URL", "Scraped At"]

    with open(csv_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(headers)

        for p in profiles:
            writer.writerow([
                p.get("name", ""),
                p.get("headline", ""),
                p.get("location", ""),
                (p.get("about", "") or "")[:500],
                p.get("connections", ""),
                p.get("profile_url", ""),
                p.get("scraped_at", "")
            ])

    print(f"\nExported {len(profiles)} profiles to CSV:")
    print(f"  {csv_file}")

    return csv_file


def export_to_google_sheet(profiles: list, sheet_name: str = "LinkedIn Profiles"):
    """Export profiles to Google Sheet"""
    creds_file = BASE_DIR.parent / "credentials.json"

    if not creds_file.exists():
        print(f"\nGoogle credentials not found at {creds_file}")
        print("To enable Google Sheets export, add your credentials.json file")
        return None

    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]

    creds = Credentials.from_service_account_file(str(creds_file), scopes=scopes)
    client = gspread.authorize(creds)

    # Create or open spreadsheet
    try:
        spreadsheet = client.open(sheet_name)
        print(f"Opened existing spreadsheet: {sheet_name}")
    except gspread.SpreadsheetNotFound:
        spreadsheet = client.create(sheet_name)
        spreadsheet.share(None, perm_type='anyone', role='writer')
        print(f"Created new spreadsheet: {sheet_name}")

    # Get or create worksheet
    try:
        worksheet = spreadsheet.worksheet("Profiles")
        worksheet.clear()
    except gspread.WorksheetNotFound:
        worksheet = spreadsheet.add_worksheet("Profiles", rows=1000, cols=10)

    # Headers
    headers = ["Name", "Headline", "Location", "About", "Connections", "Profile URL", "Scraped At"]

    # Prepare data
    rows = [headers]
    for p in profiles:
        rows.append([
            p.get("name", ""),
            p.get("headline", ""),
            p.get("location", ""),
            p.get("about", "")[:500] if p.get("about") else "",
            p.get("connections", ""),
            p.get("profile_url", ""),
            p.get("scraped_at", "")
        ])

    # Write to sheet
    worksheet.update(rows, value_input_option="RAW")

    sheet_url = f"https://docs.google.com/spreadsheets/d/{spreadsheet.id}"
    print(f"\nExported {len(profiles)} profiles to Google Sheets:")
    print(f"  {sheet_url}")

    return sheet_url


def main():
    """Main function"""
    print("=" * 60)
    print("LinkedIn Bulk Profile Scraper")
    print("=" * 60)

    # Get profile URLs from user or file
    urls_file = OUTPUT_DIR / "profile_urls.txt"

    if urls_file.exists():
        with open(urls_file) as f:
            profile_urls = [line.strip() for line in f if line.strip() and "linkedin.com/in/" in line]
        print(f"Loaded {len(profile_urls)} URLs from {urls_file}")
    else:
        print(f"\nNo URLs file found. Creating sample at: {urls_file}")
        print("Add LinkedIn profile URLs (one per line) to this file and run again.")

        sample_urls = [
            "https://www.linkedin.com/in/williamhgates",
            "https://www.linkedin.com/in/satlovelace",
            "# Add more profile URLs here, one per line",
        ]
        with open(urls_file, "w") as f:
            f.write("\n".join(sample_urls))

        print(f"\nSample file created with {len(sample_urls)} URLs.")
        print("Edit the file and run this script again.")
        return

    if not profile_urls:
        print("No valid LinkedIn profile URLs found in file.")
        return

    # Scrape profiles
    scraper = BulkProfileScraper(headless=False)

    try:
        profiles = scraper.scrape_multiple(profile_urls, max_profiles=100)

        # Export to CSV (always works)
        if profiles:
            print("\n" + "=" * 60)
            export_to_csv(profiles)

            # Try Google Sheets (may fail if quota exceeded)
            try:
                export_to_google_sheet(profiles, "LinkedIn Scraped Profiles")
            except Exception as e:
                print(f"\nGoogle Sheets export failed: {e}")
                print("Data has been saved to CSV file instead.")

    finally:
        scraper.close()

    print("\n" + "=" * 60)
    print("Done!")


if __name__ == "__main__":
    main()