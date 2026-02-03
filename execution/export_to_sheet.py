"""
Google Sheets Exporter
Exports scraped posts and analysis to Google Sheets
"""

import os
import json
from datetime import datetime
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).parent.parent
INPUT_DIR = BASE_DIR / ".tmp"
CREDENTIALS_FILE = BASE_DIR / "credentials.json"
TOKEN_FILE = BASE_DIR / "token.json"


def get_google_sheets_client():
    """
    Get authenticated Google Sheets client.
    Requires credentials.json for first-time OAuth.
    """
    try:
        import gspread
        from google.oauth2.service_account import Credentials
        from google.oauth2.credentials import Credentials as UserCredentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from google.auth.transport.requests import Request
    except ImportError:
        raise ImportError(
            "Google Sheets dependencies not installed. Run: "
            "pip install gspread google-auth google-auth-oauthlib"
        )

    SCOPES = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive'
    ]

    creds = None

    # Try service account first (simpler for automation)
    if CREDENTIALS_FILE.exists():
        try:
            # Check if it's a service account file
            with open(CREDENTIALS_FILE) as f:
                cred_data = json.load(f)

            if cred_data.get('type') == 'service_account':
                creds = Credentials.from_service_account_file(
                    str(CREDENTIALS_FILE), scopes=SCOPES
                )
                return gspread.authorize(creds)
        except:
            pass

    # Try OAuth flow for user credentials
    if TOKEN_FILE.exists():
        creds = UserCredentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        elif CREDENTIALS_FILE.exists():
            flow = InstalledAppFlow.from_client_secrets_file(
                str(CREDENTIALS_FILE), SCOPES
            )
            creds = flow.run_local_server(port=0)

            # Save credentials for future runs
            with open(TOKEN_FILE, 'w') as token:
                token.write(creds.to_json())
        else:
            raise FileNotFoundError(
                f"No credentials found. Please add credentials.json to {BASE_DIR}"
            )

    return gspread.authorize(creds)


def export_opportunities_to_sheet(
    opportunities: list[dict],
    spreadsheet_id: Optional[str] = None,
    sheet_name: str = "Comment Opportunities"
) -> str:
    """
    Export comment opportunities to Google Sheet.

    Args:
        opportunities: List of analyzed posts
        spreadsheet_id: Google Sheet ID (or create new if None)
        sheet_name: Name of the worksheet

    Returns:
        URL of the Google Sheet
    """
    client = get_google_sheets_client()

    # Open or create spreadsheet
    if spreadsheet_id:
        spreadsheet = client.open_by_key(spreadsheet_id)
    else:
        spreadsheet_id = os.getenv("GOOGLE_SHEETS_ID")
        if spreadsheet_id:
            spreadsheet = client.open_by_key(spreadsheet_id)
        else:
            spreadsheet = client.create(f"Skool Analysis - {datetime.now().strftime('%Y-%m-%d')}")
            print(f"Created new spreadsheet: {spreadsheet.url}")

    # Get or create worksheet
    try:
        worksheet = spreadsheet.worksheet(sheet_name)
        worksheet.clear()
    except:
        worksheet = spreadsheet.add_worksheet(title=sheet_name, rows=100, cols=15)

    # Prepare headers and data
    headers = [
        "Rank", "Score", "Title", "Author", "URL", "Likes", "Comments",
        "Recency", "Opportunity", "Engagement", "Topic", "Recommendation", "Posted"
    ]

    rows = [headers]
    for i, post in enumerate(opportunities, 1):
        scores = post.get('scores', {})
        rows.append([
            i,
            scores.get('final', 0),
            post.get('title', '')[:100],
            post.get('author', ''),
            post.get('url', ''),
            post.get('likes', 0),
            post.get('comments_count', 0),
            scores.get('recency', 0),
            scores.get('opportunity', 0),
            scores.get('engagement', 0),
            scores.get('topic', 0),
            post.get('recommendation', ''),
            post.get('timestamp', '')
        ])

    # Write to sheet
    worksheet.update('A1', rows)

    # Format header row
    worksheet.format('A1:M1', {
        'textFormat': {'bold': True},
        'backgroundColor': {'red': 0.9, 'green': 0.9, 'blue': 0.9}
    })

    # Auto-resize columns
    try:
        worksheet.columns_auto_resize(0, 12)
    except:
        pass  # Some APIs don't support this

    print(f"Exported {len(opportunities)} opportunities to '{sheet_name}'")
    return spreadsheet.url


def export_content_patterns_to_sheet(
    patterns: dict,
    spreadsheet_id: Optional[str] = None,
    sheet_name: str = "Content Patterns"
) -> str:
    """
    Export content pattern analysis to Google Sheet.
    """
    client = get_google_sheets_client()

    # Open spreadsheet
    if spreadsheet_id:
        spreadsheet = client.open_by_key(spreadsheet_id)
    else:
        spreadsheet_id = os.getenv("GOOGLE_SHEETS_ID")
        if spreadsheet_id:
            spreadsheet = client.open_by_key(spreadsheet_id)
        else:
            raise ValueError("No spreadsheet ID provided. Set GOOGLE_SHEETS_ID in .env")

    # Get or create worksheet
    try:
        worksheet = spreadsheet.worksheet(sheet_name)
        worksheet.clear()
    except:
        worksheet = spreadsheet.add_worksheet(title=sheet_name, rows=50, cols=10)

    # Build content
    rows = []

    # Engagement benchmarks
    rows.append(["=== ENGAGEMENT BENCHMARKS ===", ""])
    benchmarks = patterns.get('engagement_benchmarks', {})
    rows.append(["Average Likes", benchmarks.get('avg_likes', 0)])
    rows.append(["Average Comments", benchmarks.get('avg_comments', 0)])
    rows.append(["Max Likes", benchmarks.get('max_likes', 0)])
    rows.append(["Max Comments", benchmarks.get('max_comments', 0)])
    rows.append(["", ""])

    # Top performing posts
    rows.append(["=== TOP PERFORMING POSTS ===", "", "", ""])
    rows.append(["Title", "Likes", "Comments", "URL"])
    for post in patterns.get('top_performing_posts', []):
        rows.append([
            post.get('title', '')[:80],
            post.get('likes', 0),
            post.get('comments', 0),
            post.get('url', '')
        ])
    rows.append(["", ""])

    # Content ideas
    rows.append(["=== CONTENT IDEAS ==="])
    for idea in patterns.get('content_ideas', []):
        rows.append([idea])

    # Write to sheet
    worksheet.update('A1', rows)

    print(f"Exported content patterns to '{sheet_name}'")
    return spreadsheet.url


def export_all(
    opportunities_file: str = "analysis_results.json",
    spreadsheet_id: Optional[str] = None
) -> str:
    """
    Export both opportunities and patterns from analysis file.

    Returns:
        URL of the Google Sheet
    """
    filepath = INPUT_DIR / opportunities_file

    if not filepath.exists():
        raise FileNotFoundError(
            f"Analysis file not found at {filepath}. Run analyze_posts.py first."
        )

    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)

    opportunities = data.get('comment_opportunities', [])
    patterns = data.get('content_patterns', {})

    # Export opportunities
    url = export_opportunities_to_sheet(opportunities, spreadsheet_id)

    # Export patterns to same spreadsheet
    sheet_id = spreadsheet_id or os.getenv("GOOGLE_SHEETS_ID")
    if sheet_id:
        export_content_patterns_to_sheet(patterns, sheet_id)

    return url


if __name__ == "__main__":
    import sys

    spreadsheet_id = sys.argv[1] if len(sys.argv) > 1 else None

    try:
        url = export_all(spreadsheet_id=spreadsheet_id)
        print(f"\nExport complete!")
        print(f"View your sheet: {url}")
    except FileNotFoundError as e:
        print(f"Error: {e}")
        print("\nMake sure to run the scraper and analyzer first:")
        print("  1. python skool_scraper.py <community_url>")
        print("  2. python analyze_posts.py")
        print("  3. python export_to_sheet.py")
    except Exception as e:
        print(f"Error exporting to Google Sheets: {e}")
        print("\nMake sure you have:")
        print("  1. credentials.json in the project root")
        print("  2. GOOGLE_SHEETS_ID set in .env (optional)")
