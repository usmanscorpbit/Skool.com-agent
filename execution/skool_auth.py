"""
Skool Authentication Handler
Manages login and session persistence for Skool.com
"""

import os
import json
from pathlib import Path
from playwright.sync_api import sync_playwright, Browser, BrowserContext
from dotenv import load_dotenv

load_dotenv()

# Paths
BASE_DIR = Path(__file__).parent.parent
SESSION_FILE = BASE_DIR / ".tmp" / "skool_session.json"
SESSION_FILE.parent.mkdir(parents=True, exist_ok=True)


def login_to_skool(headless: bool = True) -> BrowserContext:
    """
    Login to Skool and return an authenticated browser context.
    Saves session state for reuse.
    """
    email = os.getenv("SKOOL_EMAIL")
    password = os.getenv("SKOOL_PASSWORD")

    if not email or not password:
        raise ValueError("SKOOL_EMAIL and SKOOL_PASSWORD must be set in .env")

    playwright = sync_playwright().start()
    browser = playwright.chromium.launch(headless=headless)

    # Try to load existing session
    if SESSION_FILE.exists():
        try:
            context = browser.new_context(storage_state=str(SESSION_FILE))
            # Verify session is still valid
            page = context.new_page()
            page.goto("https://www.skool.com/")
            page.wait_for_timeout(2000)

            # Check if we're logged in by looking for user menu
            if page.locator('[data-testid="user-menu"]').count() > 0 or \
               page.locator('.user-avatar').count() > 0 or \
               "skool.com/community" in page.url or \
               page.locator('a[href*="/settings"]').count() > 0:
                print("Reusing existing session")
                page.close()
                return context
            page.close()
            context.close()
        except Exception as e:
            print(f"Session expired or invalid: {e}")

    # Fresh login required
    context = browser.new_context()
    page = context.new_page()

    print("Logging in to Skool...")
    page.goto("https://www.skool.com/login")
    page.wait_for_load_state("domcontentloaded")
    page.wait_for_timeout(2000)

    # Wait for email input to be visible
    page.wait_for_selector('input[type="email"], input[name="email"]', timeout=10000)

    # Fill login form
    page.fill('input[name="email"], input[type="email"]', email)
    page.fill('input[name="password"], input[type="password"]', password)

    # Click login button
    page.click('button[type="submit"]')

    # Wait for navigation after login
    page.wait_for_timeout(5000)

    # Check if login succeeded
    max_attempts = 10
    for _ in range(max_attempts):
        if "login" not in page.url.lower():
            break
        page.wait_for_timeout(1000)

    # Verify login succeeded
    if "login" in page.url.lower():
        raise Exception("Login failed - check your credentials")

    # Save session state
    context.storage_state(path=str(SESSION_FILE))
    print(f"Session saved to {SESSION_FILE}")

    page.close()
    return context


def get_authenticated_context(headless: bool = True) -> tuple:
    """
    Get an authenticated browser context.
    Returns (playwright, browser, context) tuple.
    Caller is responsible for cleanup.
    """
    playwright = sync_playwright().start()
    browser = playwright.chromium.launch(headless=headless)

    email = os.getenv("SKOOL_EMAIL")
    password = os.getenv("SKOOL_PASSWORD")

    if not email or not password:
        raise ValueError("SKOOL_EMAIL and SKOOL_PASSWORD must be set in .env")

    # Try existing session first
    if SESSION_FILE.exists():
        try:
            context = browser.new_context(storage_state=str(SESSION_FILE))
            page = context.new_page()
            page.goto("https://www.skool.com/")
            page.wait_for_timeout(2000)

            # Simple check - if we're not redirected to login, we're good
            if "login" not in page.url.lower():
                print("Using existing session")
                page.close()
                return playwright, browser, context
            page.close()
            context.close()
        except Exception:
            pass

    # Fresh login
    context = browser.new_context()
    page = context.new_page()

    print("Performing fresh login...")
    page.goto("https://www.skool.com/login")
    page.wait_for_load_state("domcontentloaded")
    page.wait_for_timeout(2000)

    # Wait for email input to be visible
    page.wait_for_selector('input[type="email"], input[name="email"]', timeout=10000)

    page.fill('input[name="email"], input[type="email"]', email)
    page.fill('input[name="password"], input[type="password"]', password)
    page.click('button[type="submit"]')

    # Wait for navigation after login
    page.wait_for_timeout(5000)

    # Check if login succeeded by looking for redirect away from login page
    max_attempts = 10
    for _ in range(max_attempts):
        if "login" not in page.url.lower():
            break
        page.wait_for_timeout(1000)

    if "login" in page.url.lower():
        playwright.stop()
        raise Exception("Login failed - check credentials")

    context.storage_state(path=str(SESSION_FILE))
    print("Login successful, session saved")

    page.close()
    return playwright, browser, context


def clear_session():
    """Clear saved session (force fresh login next time)"""
    if SESSION_FILE.exists():
        SESSION_FILE.unlink()
        print("Session cleared")


if __name__ == "__main__":
    # Test authentication
    try:
        playwright, browser, context = get_authenticated_context(headless=False)
        page = context.new_page()
        page.goto("https://www.skool.com/")
        print(f"Current URL: {page.url}")
        print("Authentication test successful!")
        input("Press Enter to close browser...")
        browser.close()
        playwright.stop()
    except Exception as e:
        print(f"Authentication failed: {e}")
