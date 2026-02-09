# LinkedIn Automation - Approach 1: Official API

## Overview
Safe LinkedIn automation using official LinkedIn APIs. This approach has limited features but zero risk of account suspension.

## Risk Level: LOW
- Uses official LinkedIn APIs
- No scraping or automation detection risk
- Account-safe but feature-limited

## Features Supported
| Feature | Method | Status |
|---------|--------|--------|
| Profile Scraping | Manual export only | ⚠️ Manual |
| Post Discovery | Not available | ❌ None |
| Content Posting | Marketing API | ✅ Full |
| Send Messages | Not available | ❌ None |
| Post Comments | Not available | ❌ None |
| Article Posts | Marketing API | ✅ Full |
| Image Posts | Marketing API | ✅ Full |

## Prerequisites
1. LinkedIn Developer Account: https://www.linkedin.com/developers/
2. LinkedIn App with OAuth 2.0 credentials
3. Verified app with appropriate products enabled
4. `.env.approach1` configured

## Setup LinkedIn App

### Step 1: Create LinkedIn App
1. Go to https://www.linkedin.com/developers/
2. Click "Create app"
3. Fill in app details
4. Under Products, request access to:
   - Share on LinkedIn
   - Sign In with LinkedIn using OpenID Connect

### Step 2: Configure OAuth
1. In app settings, go to Auth
2. Add redirect URL: `http://localhost:8080/callback`
3. Note your Client ID and Client Secret

### Step 3: Get Permissions Approved
- For posting as a user: "Share on LinkedIn" product
- For organization posting: "Marketing Developer Platform" (requires company page admin)

## Configuration
Create `linkedin/approach1_official/.env.approach1`:
```
# LinkedIn OAuth App Credentials
LINKEDIN_CLIENT_ID=your_client_id
LINKEDIN_CLIENT_SECRET=your_client_secret

# For organization posting (optional)
LINKEDIN_ORGANIZATION_ID=urn:li:organization:12345
```

## Workflow

### Phase 1: Authentication
Run the auth flow to get an access token:
```bash
python linkedin/approach1_official/execution/linkedin_api_auth.py
```

This will:
1. Open browser for OAuth authorization
2. Prompt you to paste the redirect URL
3. Exchange code for access token
4. Save token to `linkedin/.tmp/approach1/linkedin_token.json`

**Token expires after 60 days** - re-run auth when needed.

### Phase 2: Prospecting (Manual)
Since API doesn't support profile scraping:

**Option A: Export Connections**
1. Go to LinkedIn Settings > Data Privacy > Get a copy of your data
2. Select "Connections"
3. Download and process:
```bash
python linkedin/approach1_official/execution/manual_export_processor.py Connections.csv connections
```

**Option B: Sales Navigator Export**
1. Build a lead list in Sales Navigator
2. Export to CSV
3. Process:
```bash
python linkedin/approach1_official/execution/manual_export_processor.py leads.csv sales_navigator
```

### Phase 3: Generate Content
Use shared content generator:
```python
from linkedin.shared.content_generator import ContentGenerator

generator = ContentGenerator()
post = generator.generate_post(
    topic="AI in business",
    style="thought_leadership"
)
```

### Phase 4: Post Content

**Text Post:**
```bash
python linkedin/approach1_official/execution/linkedin_api_post.py "Your post content here"
```

**Article Post:**
```bash
python linkedin/approach1_official/execution/linkedin_api_post.py "Check out this article!" --url https://example.com/article
```

**Image Post:**
```bash
python linkedin/approach1_official/execution/linkedin_api_post.py "Great photo!" --image /path/to/image.jpg
```

**Programmatic:**
```python
from linkedin.approach1_official.execution.linkedin_api_post import create_post

result = create_post(
    text="My post content...",
    visibility="PUBLIC"  # or "CONNECTIONS"
)
```

## API Limits
| Resource | Limit | Period |
|----------|-------|--------|
| API calls | 100,000 | Per day |
| Posts | 150 | Per day per app |
| Image uploads | 50 | Per day |

## Output Files
All outputs in `linkedin/.tmp/approach1/`:
- `linkedin_token.json` - OAuth access token
- `processed_profiles.json` - Processed exports
- `api_post_log.json` - Posted content log

## Error Handling
- **401 Unauthorized**: Token expired, re-run auth flow
- **403 Forbidden**: Missing permissions, check app products
- **429 Too Many Requests**: Rate limited, wait and retry
- **Invalid grant**: OAuth code expired, restart auth flow

## Limitations
This approach CANNOT:
- Scrape profiles (use manual exports)
- Find posts to engage with
- Send messages or connection requests
- Post comments on others' posts
- Access trending topics

For these features, use Approach 2 (Playwright) or Approach 3 (Third-Party).

## Best Practices
1. Keep access token secure (don't commit to git)
2. Monitor API usage in LinkedIn Developer Portal
3. Use descriptive post content for better engagement
4. Include images when possible (higher engagement)
5. Post during business hours for visibility
6. Refresh token before it expires (60 days)

## Hybrid Strategy
Combine with other approaches:
- **Prospecting**: Use Approach 3 (Phantombuster/Apify) to find targets
- **Engagement**: Manual or Approach 2 (Playwright) for comments/messages
- **Posting**: Use this approach for safe, reliable content publishing
