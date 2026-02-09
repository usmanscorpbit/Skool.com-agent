# LinkedIn Automation - Approach 3: Third-Party Services

## Overview
LinkedIn automation via Phantombuster and Apify APIs. These services handle the browser automation and proxy management, reducing technical complexity and detection risk.

## Risk Level: MEDIUM
- Risk is offloaded to third-party services
- Still requires LinkedIn session cookie for full functionality
- Services may be affected by LinkedIn changes

## Features Supported
| Feature | Service | Status |
|---------|---------|--------|
| Profile Scraping | Apify/Phantombuster | ✅ Full |
| Post Discovery | Apify/Phantombuster | ✅ Full |
| Search Profiles | Apify | ✅ Full |
| Connection Requests | Phantombuster | ✅ Full |
| Send Messages | Phantombuster | ✅ Full |
| Post Comments | Phantombuster | ✅ Partial |
| Content Posting | Not available | ❌ Manual |

## Prerequisites
1. Phantombuster account with API key
2. Apify account with API token
3. LinkedIn session cookie (li_at) for full functionality
4. `.env.approach3` configured

## Configuration
Create `linkedin/approach3_thirdparty/.env.approach3`:
```
# Phantombuster
PHANTOMBUSTER_API_KEY=your_api_key

# Phantombuster Phantom IDs (set up in your Phantombuster dashboard)
PHANTOMBUSTER_PROFILE_SCRAPER_ID=
PHANTOMBUSTER_POST_FINDER_ID=
PHANTOMBUSTER_NETWORK_BOOSTER_ID=
PHANTOMBUSTER_MESSAGE_SENDER_ID=
PHANTOMBUSTER_COMMENTER_ID=

# Apify
APIFY_API_TOKEN=your_token

# Optional: Override default Apify actor IDs
APIFY_PROFILE_SCRAPER_ID=curious_coder/linkedin-profile-scraper
APIFY_POST_SCRAPER_ID=curious_coder/linkedin-post-scraper
APIFY_SEARCH_SCRAPER_ID=bebity/linkedin-search-scraper

# LinkedIn Session Cookie (for authenticated actions)
LINKEDIN_SESSION_COOKIE=your_li_at_cookie_value
```

## Getting Your LinkedIn Session Cookie
1. Log in to LinkedIn in your browser
2. Open Developer Tools (F12)
3. Go to Application > Cookies > linkedin.com
4. Copy the value of `li_at` cookie
5. Add to `.env.approach3` as `LINKEDIN_SESSION_COOKIE`

**Note:** Cookie expires periodically (~1-2 weeks). Update when needed.

## Service Comparison

### Phantombuster
**Pros:**
- Purpose-built LinkedIn automations
- Pre-configured "Phantoms" for common tasks
- Good for actions (messages, comments, connections)

**Cons:**
- Monthly subscription required (~$50-150/month)
- Limited customization
- Credits consumed per action

**Best for:** Messaging, connection requests, commenting

### Apify
**Pros:**
- Pay-per-use pricing (cheaper for scraping)
- More flexible actors
- Better for bulk data extraction

**Cons:**
- Fewer action-oriented actors
- Requires more setup
- Variable actor quality

**Best for:** Profile scraping, search, data extraction

## Workflow

### Phase 1: Setup Services
1. Create Phantombuster account, get API key
2. Set up required Phantoms (profile scraper, network booster, etc.)
3. Create Apify account, get API token
4. Configure `.env.approach3`

### Phase 2: Scrape Profiles
**Using Apify (recommended for bulk scraping):**
```python
from linkedin.approach3_thirdparty.execution.apify_linkedin_client import get_client

client = get_client()
results = client.scrape_profiles([
    "https://linkedin.com/in/person1",
    "https://linkedin.com/in/person2"
])
```

**Using Phantombuster:**
```python
from linkedin.approach3_thirdparty.execution.phantombuster_client import get_client

client = get_client()
results = client.scrape_profiles([
    "https://linkedin.com/in/person1"
], session_cookie="your_li_at")
```

### Phase 3: Find Posts
**Using Apify:**
```python
client = get_client()
posts = client.scrape_posts(
    hashtags=["entrepreneur", "startup"],
    max_posts=50
)
```

### Phase 4: Normalize Data
```python
from linkedin.approach3_thirdparty.execution.data_normalizer import DataNormalizer

# Normalize Apify results to shared types
result = DataNormalizer.normalize_profiles(raw_data, source="apify")
profiles = result.profiles  # List[LinkedInProfile]
```

### Phase 5: Execute Actions (Phantombuster)
**Send Connection Requests:**
```python
client = get_client()
results = client.send_connection_requests(
    profile_urls=["https://linkedin.com/in/target"],
    message_template="Hi {firstName}, I'd love to connect!",
    session_cookie="your_li_at"
)
```

**Send Messages:**
```python
results = client.send_messages(
    profile_urls=["https://linkedin.com/in/target"],
    message_template="Hi {firstName}, following up on...",
    session_cookie="your_li_at"
)
```

## Rate Limits
Services enforce their own limits plus LinkedIn's:

| Service | Limit Type | Typical Limit |
|---------|------------|---------------|
| Phantombuster | Actions per phantom per day | 10-50 |
| Apify | Compute units | Pay per use |
| LinkedIn (via any service) | Connection requests | ~100/week |
| LinkedIn (via any service) | Messages | ~50/day |

## Cost Estimation
| Service | Pricing | Typical Monthly |
|---------|---------|-----------------|
| Phantombuster | Subscription | $56-128/month |
| Apify | Pay per use | $10-50/month |

## Output Files
All outputs in `linkedin/.tmp/approach3/`:
- `apify_profiles.json` - Profiles from Apify
- `apify_posts.json` - Posts from Apify
- `phantombuster_profiles.json` - Profiles from Phantombuster
- `phantombuster_connections.json` - Connection request results

## Error Handling
- **API key invalid**: Check credentials in `.env.approach3`
- **Cookie expired**: Get fresh `li_at` cookie from browser
- **Rate limit**: Wait and retry, reduce batch sizes
- **Actor failed**: Check Apify/Phantombuster dashboard for logs

## Best Practices
1. Start with Apify for scraping (cheaper, pay-per-use)
2. Use Phantombuster for actions (better action support)
3. Keep session cookie updated
4. Monitor usage to control costs
5. Use DataNormalizer to standardize outputs
6. Check service dashboards for run logs and errors
