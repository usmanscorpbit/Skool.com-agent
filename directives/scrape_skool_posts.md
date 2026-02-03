# Scrape Skool Posts

## Goal
Scrape posts from a Skool community to gather engagement data, post content, and author information.

## Inputs
- **community_url** (required): The Skool community URL (e.g., `https://www.skool.com/ai-automation`)
- **max_posts** (optional): Maximum number of posts to scrape (default: 50)
- **include_comments** (optional): Whether to scrape comments on each post (default: false)

## Prerequisites
1. Skool credentials configured in `.env`:
   - `SKOOL_EMAIL`
   - `SKOOL_PASSWORD`
2. Playwright installed: `playwright install chromium`
3. You must be a member of the community you're scraping

## Execution Steps

1. **Validate inputs**
   - Confirm community_url is provided
   - Verify it's a valid Skool URL format

2. **Run the scraper**
   ```bash
   cd execution
   python skool_scraper.py "https://www.skool.com/community-name" 50
   ```

3. **Verify output**
   - Check `.tmp/scraped_posts.json` was created
   - Check `.tmp/scraped_posts.csv` was created
   - Confirm posts have expected fields (title, author, likes, etc.)

## Outputs
- `.tmp/scraped_posts.json` - Full post data in JSON format
- `.tmp/scraped_posts.csv` - Simplified CSV for quick review

## Data Fields Collected
| Field | Description |
|-------|-------------|
| id | Unique post identifier |
| title | Post title/headline |
| content | Post body (truncated to 500 chars) |
| author | Author name |
| author_url | Link to author profile |
| url | Direct link to post |
| timestamp | Relative time (e.g., "2h", "3d") |
| posted_at | ISO timestamp |
| likes | Number of likes |
| comments_count | Number of comments |
| category | Post category/channel |

## Edge Cases
- **Private communities**: You must be a member to scrape
- **Rate limiting**: If scraping fails, wait 5 minutes and retry with smaller batch
- **Deleted posts**: Some URLs may be invalid; scraper skips these gracefully
- **Session expiry**: If auth fails, delete `.tmp/skool_session.json` and retry

## Troubleshooting
- **"Login failed"**: Check SKOOL_EMAIL and SKOOL_PASSWORD in `.env`
- **Empty results**: Verify community URL is correct and you're a member
- **Timeout**: Run with `headless=False` to debug: modify script or run interactively
