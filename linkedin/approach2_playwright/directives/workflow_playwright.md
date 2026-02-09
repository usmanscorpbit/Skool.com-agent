# LinkedIn Automation - Approach 2: Playwright Browser Automation

## Overview
Full-featured LinkedIn automation using browser control with Playwright. This approach provides the most complete feature set but carries higher risk of account restrictions.

## Risk Level: HIGH
- LinkedIn actively detects and blocks automation
- Use a dedicated test account, not your primary account
- Follow all rate limits strictly
- Use warm-up sessions before actions

## Features Supported
| Feature | Script | Status |
|---------|--------|--------|
| Profile Scraping | `linkedin_profile_scraper.py` | ✅ Full |
| Post Discovery | `linkedin_post_finder.py` | ✅ Full |
| Content Posting | `linkedin_content_poster.py` | ✅ Full |
| Send Messages | `linkedin_messenger.py` | ✅ Full |
| Post Comments | `linkedin_commenter.py` | ✅ Full |
| Trending Topics | Via post analysis | ✅ Partial |

## Prerequisites
1. Python environment with dependencies installed
2. `.env.approach2` configured with LinkedIn credentials
3. Test LinkedIn account (DO NOT use primary account)
4. Playwright browsers installed: `playwright install chromium`

## Configuration
Create `linkedin/approach2_playwright/.env.approach2`:
```
LINKEDIN_EMAIL=your_test_account@email.com
LINKEDIN_PASSWORD=your_password

# Anti-detection settings
PLAYWRIGHT_HEADLESS=false

# Rate limits (conservative defaults)
ACTIONS_PER_HOUR=20
PROFILES_PER_SESSION=50
MESSAGES_PER_DAY=25
COMMENTS_PER_DAY=30
```

## Workflow

### Phase 1: Session Setup
1. Run authentication to establish session:
   ```bash
   python linkedin/approach2_playwright/execution/linkedin_browser_auth.py
   ```
2. Complete any security challenges manually
3. Session is saved to `linkedin/.tmp/approach2/linkedin_session.json`

### Phase 2: Profile Prospecting
1. Prepare list of target profile URLs
2. Run profile scraper:
   ```bash
   python linkedin/approach2_playwright/execution/linkedin_profile_scraper.py <url1> <url2> ...
   ```
3. Results saved to `linkedin/.tmp/approach2/scraped_profiles.json`
4. Use `ProfileAnalyzer` to score and rank profiles

### Phase 3: Find Posts for Engagement
1. Search by hashtags or keywords:
   ```bash
   python linkedin/approach2_playwright/execution/linkedin_post_finder.py #entrepreneur #startup
   ```
2. Results saved to `linkedin/.tmp/approach2/found_posts.json`
3. Use `ProfileAnalyzer.find_comment_opportunities()` to score posts

### Phase 4: Generate Content
1. Use `ContentGenerator` to create:
   - Posts (thought leadership, tips, stories)
   - Comments for target posts
   - Personalized connection messages

### Phase 5: Execute Actions
**Post Content:**
```bash
python linkedin/approach2_playwright/execution/linkedin_content_poster.py
```

**Send Connection Requests:**
```bash
python linkedin/approach2_playwright/execution/linkedin_messenger.py connect <profile_url> "personalized note"
```

**Post Comments:**
```bash
python linkedin/approach2_playwright/execution/linkedin_commenter.py <post_url> "your comment"
```

## Rate Limits
| Action | Limit | Period |
|--------|-------|--------|
| Any action | 20 | Per hour |
| Profile scrapes | 50 | Per session |
| Messages | 25 | Per day |
| Comments | 30 | Per day |

## Anti-Detection Measures
The `anti_detection.py` module implements:
- Human-like delays (gaussian distribution)
- Natural typing speed with variations
- Random mouse movements
- Scroll behavior patterns
- Session warm-up routines
- Break scheduling

## Error Handling
- **Login failed**: Check credentials, handle 2FA manually
- **Rate limit hit**: Stop immediately, wait until next period
- **Element not found**: LinkedIn may have changed UI, update selectors
- **Account restricted**: Stop all automation, wait 24-48 hours

## Output Files
All outputs in `linkedin/.tmp/approach2/`:
- `linkedin_session.json` - Browser session state
- `scraped_profiles.json` - Scraped profile data
- `found_posts.json` - Discovered posts
- `post_log.json` - Posted content log
- `message_log.json` - Sent messages log
- `comment_log.json` - Posted comments log

## Troubleshooting

### Session Keeps Expiring
- LinkedIn sessions expire after ~24 hours of inactivity
- Run `clear_session()` and re-authenticate
- Check for security emails from LinkedIn

### Actions Failing Silently
- Run with `headless=False` to see browser
- Check for UI changes on LinkedIn
- Verify selectors still match elements

### Account Warnings
1. STOP all automation immediately
2. Log in manually and verify identity
3. Wait 48-72 hours before resuming
4. Reduce rate limits by 50%

## Best Practices
1. Always warm up session before actions
2. Space actions throughout the day
3. Mix automated and manual activity
4. Monitor for warning signs (CAPTCHAs, verification emails)
5. Keep rate limits conservative
6. Use headless=False for debugging
