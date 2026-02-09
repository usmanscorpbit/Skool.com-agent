"""
LinkedIn Profile Scraper
Scrapes profile data using Playwright browser automation
"""

import json
import re
from pathlib import Path
from typing import List, Optional
from datetime import datetime
from playwright.sync_api import Page, BrowserContext

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from shared.types import LinkedInProfile, ApproachType, ConnectionDegree, ScrapingResult
from .linkedin_browser_auth import get_authenticated_context
from .anti_detection import AntiDetection, RateLimiter

BASE_DIR = Path(__file__).parent.parent.parent
OUTPUT_DIR = BASE_DIR / ".tmp" / "approach2"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


class LinkedInProfileScraper:
    """
    Scrapes LinkedIn profiles via browser automation.
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

    def scrape_profile(self, profile_url: str) -> Optional[LinkedInProfile]:
        """
        Scrape a single LinkedIn profile.

        Args:
            profile_url: URL of the profile to scrape

        Returns:
            LinkedInProfile or None if failed
        """
        if not self.rate_limiter.can_scrape_profile():
            print("Rate limit reached for profile scraping")
            return None

        page = self.context.new_page()
        try:
            # Navigate to profile
            page.goto(profile_url, wait_until="domcontentloaded")
            self.anti_detection.medium_wait()

            # Check for auth wall or errors
            if "/authwall" in page.url or "page not found" in page.title().lower():
                print(f"Cannot access profile: {profile_url}")
                return None

            profile = self._extract_profile_data(page, profile_url)
            self.rate_limiter.record_profile_scrape()

            return profile

        except Exception as e:
            print(f"Error scraping profile {profile_url}: {e}")
            return None
        finally:
            page.close()

    def _extract_profile_data(self, page: Page, profile_url: str) -> LinkedInProfile:
        """Extract profile data from loaded page"""

        # Extract profile ID from URL
        profile_id = self._extract_profile_id(profile_url)

        # Name
        name = ""
        name_selectors = [
            'h1.text-heading-xlarge',
            '.pv-text-details__left-panel h1',
            'h1[data-anonymize="person-name"]'
        ]
        for selector in name_selectors:
            el = page.locator(selector).first
            if el.count() > 0:
                name = el.inner_text().strip()
                break

        # Headline
        headline = ""
        headline_selectors = [
            '.text-body-medium.break-words',
            '.pv-text-details__left-panel .text-body-medium',
            'div[data-anonymize="headline"]'
        ]
        for selector in headline_selectors:
            el = page.locator(selector).first
            if el.count() > 0:
                headline = el.inner_text().strip()
                break

        # Location
        location = ""
        location_selectors = [
            '.pv-text-details__left-panel .text-body-small:not(.inline)',
            'span.text-body-small[data-anonymize="location"]'
        ]
        for selector in location_selectors:
            el = page.locator(selector).first
            if el.count() > 0:
                location = el.inner_text().strip()
                break

        # Connection degree
        connection_degree = self._extract_connection_degree(page)

        # Connections/followers count
        connections, followers = self._extract_network_info(page)

        # About section (may need to scroll)
        about = self._extract_about_section(page)

        # Extract company and title from headline or experience
        company, title = self._extract_current_position(page, headline)

        # Experience
        experience = self._extract_experience(page)

        # Skills
        skills = self._extract_skills(page)

        return LinkedInProfile(
            id=profile_id,
            name=name,
            headline=headline,
            profile_url=profile_url,
            location=location,
            about=about,
            company=company,
            title=title,
            connections=connections,
            followers=followers,
            connection_degree=connection_degree,
            experience=experience,
            skills=skills,
            source_approach=ApproachType.PLAYWRIGHT,
            scraped_at=datetime.now()
        )

    def _extract_profile_id(self, url: str) -> str:
        """Extract profile ID from URL"""
        # Handle various URL formats
        patterns = [
            r'/in/([^/?\s]+)',
            r'/pub/([^/?\s]+)'
        ]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return url.split('/')[-1].split('?')[0]

    def _extract_connection_degree(self, page: Page) -> ConnectionDegree:
        """Extract connection degree"""
        degree_selectors = [
            '.dist-value',
            '.pv-text-details__right-panel .text-body-small'
        ]

        for selector in degree_selectors:
            el = page.locator(selector)
            if el.count() > 0:
                text = el.first.inner_text().lower()
                if "1st" in text:
                    return ConnectionDegree.FIRST
                elif "2nd" in text:
                    return ConnectionDegree.SECOND
                elif "3rd" in text:
                    return ConnectionDegree.THIRD

        return ConnectionDegree.OUT_OF_NETWORK

    def _extract_network_info(self, page: Page) -> tuple:
        """Extract connections and followers count"""
        connections = None
        followers = None

        # Look for connections link
        conn_el = page.locator('a[href*="/connections"] span, li.text-body-small')
        if conn_el.count() > 0:
            for i in range(conn_el.count()):
                text = conn_el.nth(i).inner_text().lower()
                if "connection" in text:
                    numbers = re.findall(r'[\d,]+', text)
                    if numbers:
                        connections = int(numbers[0].replace(',', ''))
                elif "follower" in text:
                    numbers = re.findall(r'[\d,]+', text)
                    if numbers:
                        followers = int(numbers[0].replace(',', ''))

        return connections, followers

    def _extract_about_section(self, page: Page) -> Optional[str]:
        """Extract the About section"""
        about_selectors = [
            '#about ~ .display-flex .full-width',
            'section.pv-about-section div.inline-show-more-text',
            'div[data-generated-suggestion-target*="about"]'
        ]

        for selector in about_selectors:
            el = page.locator(selector)
            if el.count() > 0:
                return el.first.inner_text().strip()

        return None

    def _extract_current_position(self, page: Page, headline: str) -> tuple:
        """Extract current company and title"""
        company = None
        title = None

        # Try to parse from headline (common format: "Title at Company")
        if " at " in headline:
            parts = headline.split(" at ", 1)
            title = parts[0].strip()
            company = parts[1].strip()
        elif " @ " in headline:
            parts = headline.split(" @ ", 1)
            title = parts[0].strip()
            company = parts[1].strip()

        # Try experience section if not found
        if not company:
            exp_company = page.locator(
                '.pv-entity__secondary-title, '
                '.experience-item__subtitle, '
                'span[aria-hidden="true"]:has-text("·")'
            )
            if exp_company.count() > 0:
                company = exp_company.first.inner_text().split('·')[0].strip()

        return company, title

    def _extract_experience(self, page: Page) -> List[dict]:
        """Extract work experience"""
        experience = []

        # Scroll to experience section
        exp_section = page.locator('#experience')
        if exp_section.count() > 0:
            exp_section.scroll_into_view_if_needed()
            self.anti_detection.short_wait()

        exp_items = page.locator(
            '.pvs-entity--padded, '
            '.pv-entity__position-group-pager, '
            'li.pvs-list__pager-item'
        )

        for i in range(min(exp_items.count(), 5)):  # Limit to 5 positions
            try:
                item = exp_items.nth(i)
                exp_data = {
                    "title": "",
                    "company": "",
                    "duration": ""
                }

                # Title
                title_el = item.locator('.t-bold span[aria-hidden="true"]').first
                if title_el.count() > 0:
                    exp_data["title"] = title_el.inner_text().strip()

                # Company
                company_el = item.locator('.t-normal span[aria-hidden="true"]').first
                if company_el.count() > 0:
                    exp_data["company"] = company_el.inner_text().strip()

                # Duration
                duration_el = item.locator('.t-black--light span[aria-hidden="true"]').first
                if duration_el.count() > 0:
                    exp_data["duration"] = duration_el.inner_text().strip()

                if exp_data["title"] or exp_data["company"]:
                    experience.append(exp_data)

            except Exception:
                continue

        return experience

    def _extract_skills(self, page: Page) -> List[str]:
        """Extract skills"""
        skills = []

        # Scroll to skills section
        skills_section = page.locator('#skills')
        if skills_section.count() > 0:
            skills_section.scroll_into_view_if_needed()
            self.anti_detection.short_wait()

        skill_els = page.locator(
            '.pv-skill-category-entity__name-text, '
            '.pvs-entity--padded .t-bold span[aria-hidden="true"]'
        )

        for i in range(min(skill_els.count(), 10)):  # Limit to 10 skills
            try:
                skill = skill_els.nth(i).inner_text().strip()
                if skill and skill not in skills:
                    skills.append(skill)
            except Exception:
                continue

        return skills

    def scrape_multiple_profiles(
        self,
        profile_urls: List[str],
        max_profiles: int = 50
    ) -> ScrapingResult:
        """
        Scrape multiple profiles with rate limiting.

        Args:
            profile_urls: List of profile URLs
            max_profiles: Maximum profiles to scrape

        Returns:
            ScrapingResult with scraped profiles
        """
        profiles = []
        errors = []

        for i, url in enumerate(profile_urls[:max_profiles]):
            if not self.rate_limiter.can_scrape_profile():
                errors.append(f"Rate limit reached after {i} profiles")
                break

            if self.anti_detection.should_take_break():
                print("Taking a break...")
                self.anti_detection.long_wait()
                self.anti_detection.long_wait()

            print(f"Scraping profile {i + 1}/{len(profile_urls)}: {url}")
            profile = self.scrape_profile(url)

            if profile:
                profiles.append(profile)
            else:
                errors.append(f"Failed to scrape: {url}")

            # Delay between profiles
            self.anti_detection.medium_wait()

        return ScrapingResult(
            success=len(profiles) > 0,
            approach=ApproachType.PLAYWRIGHT,
            profiles=profiles,
            errors=errors,
            metadata={
                "attempted": min(len(profile_urls), max_profiles),
                "scraped": len(profiles),
                "rate_limit_status": self.rate_limiter.get_status()
            }
        )


def scrape_profiles(profile_urls: List[str], headless: bool = False) -> ScrapingResult:
    """
    Main entry point for profile scraping.

    Args:
        profile_urls: List of profile URLs to scrape
        headless: Run browser in headless mode

    Returns:
        ScrapingResult with profiles
    """
    playwright, browser, context, auth = get_authenticated_context(headless)

    try:
        scraper = LinkedInProfileScraper(
            context=context,
            anti_detection=auth.anti_detection,
            rate_limiter=auth.rate_limiter
        )

        result = scraper.scrape_multiple_profiles(profile_urls)

        # Save results
        output_file = OUTPUT_DIR / "scraped_profiles.json"
        with open(output_file, "w") as f:
            json.dump([p.to_dict() for p in result.profiles], f, indent=2)
        print(f"Saved {len(result.profiles)} profiles to {output_file}")

        return result

    finally:
        auth.close()


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python linkedin_profile_scraper.py <profile_url> [profile_url2] ...")
        print("Example: python linkedin_profile_scraper.py https://www.linkedin.com/in/someone")
        sys.exit(1)

    urls = sys.argv[1:]
    result = scrape_profiles(urls, headless=False)

    print(f"\nResults: {result.to_dict()}")
    for profile in result.profiles:
        print(f"\n{profile.name} - {profile.headline}")
        print(f"  Company: {profile.company}")
        print(f"  Location: {profile.location}")
        print(f"  Connections: {profile.connections}")
