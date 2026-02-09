# LinkedIn Automation Workflow

## Overview
Automate LinkedIn engagement including profile scraping, posting, messaging, and commenting.

## Prerequisites
- LinkedIn account credentials in `linkedin/approach2_playwright/.env.approach2`
- Playwright installed: `pip install playwright && playwright install chromium`

## Available Actions

### 1. Scrape Profiles
Find and scrape LinkedIn profiles based on search terms.

**Script:** `linkedin/linkedin_agent.py`

**Usage:**
```bash
# Search and scrape profiles
python linkedin/linkedin_agent.py scrape --search "AI automation,workflow automation" --count 50

# Scrape specific URLs from a file
python linkedin/linkedin_agent.py scrape --urls profile_urls.txt --output my_profiles.csv
```

**Output:** CSV file in `linkedin/.tmp/agent_output/`

**Rate Limits:**
- 50 profiles per session
- 10-30 second delay between profiles
- Take breaks after every 12 profiles

---

### 2. Create Posts
Create and publish LinkedIn posts with hashtags and media.

**Script:** `linkedin/linkedin_agent.py`

**Usage:**
```bash
python linkedin/linkedin_agent.py post \
  --content "Excited to share our latest AI automation insights!" \
  --hashtags "ai,automation,productivity"
```

**With Media:**
```bash
python linkedin/linkedin_agent.py post \
  --content "Check out this infographic" \
  --hashtags "infographic,data" \
  --media "path/to/image.jpg"
```

**Rate Limits:**
- 20 posts per day maximum
- Wait 1+ hours between posts

---

### 3. Send Messages / Connection Requests
Send personalized messages or connection requests to scraped profiles.

**Script:** `linkedin/linkedin_agent.py`

**Usage:**
```bash
python linkedin/linkedin_agent.py message \
  --csv linkedin/.tmp/agent_output/scraped_profiles.csv \
  --template "Hi {name}, I noticed your work in {headline}. Would love to connect!" \
  --max 25
```

**Template Variables:**
- `{name}` - First name
- `{headline}` - Profile headline
- `{company}` - Company name

**Options:**
- `--direct` - Send as direct message (only for existing connections)
- Default sends as connection request with note

**Rate Limits:**
- 25 messages per day
- Connection notes limited to 300 characters

---

### 4. Find Posts to Comment On
Discover posts by hashtag or keyword for engagement opportunities.

**Script:** `linkedin/linkedin_agent.py`

**Usage:**
```bash
python linkedin/linkedin_agent.py find-posts \
  --hashtags "startup,entrepreneur" \
  --keywords "business automation" \
  --max 20
```

**Output:** JSON file with posts including:
- Author name and profile
- Post content
- Engagement metrics (likes, comments)
- Post URL

---

### 5. Auto-Comment on Posts
Find posts and automatically comment on them.

**Script:** `linkedin/linkedin_agent.py`

**Usage:**
```bash
python linkedin/linkedin_agent.py comment \
  --hashtags "ai,automation" \
  --comments "Great insight!,Love this perspective!,Thanks for sharing!" \
  --max 10
```

**Rate Limits:**
- 10-20 comments per day
- Vary comment content to avoid detection
- Wait 2-5 minutes between comments

---

## Direct Python Usage

For more control, use the modules directly:

```python
from linkedin.linkedin_agent import LinkedInAgent

agent = LinkedInAgent(headless=False)

try:
    # Scrape profiles
    profiles = agent.scrape_profiles_from_search(
        search_terms=["AI automation", "workflow expert"],
        max_profiles=50
    )

    # Create a post
    agent.create_post(
        content="Exciting news about automation!",
        hashtags=["ai", "automation"]
    )

    # Send messages
    results = agent.send_bulk_messages(
        profiles_csv="profiles.csv",
        message_template="Hi {name}, love your work!",
        max_messages=25
    )

    # Auto-comment
    agent.auto_comment(
        hashtags=["startup", "entrepreneur"],
        comments=["Great post!", "Interesting perspective!"],
        max_comments=10
    )

finally:
    agent.close()
```

---

## File Locations

| File | Description |
|------|-------------|
| `linkedin/linkedin_agent.py` | Main automation runner |
| `linkedin/.tmp/agent_output/` | Output files (CSV, JSON) |
| `linkedin/.tmp/approach2/linkedin_session.json` | Saved browser session |
| `linkedin/approach2_playwright/.env.approach2` | Credentials |

---

## Safety Guidelines

1. **Use a test account** - Never use your primary LinkedIn account
2. **Start slow** - Begin with low limits, increase gradually
3. **Monitor for warnings** - Check email for LinkedIn warnings
4. **Mix manual activity** - Use the account manually sometimes
5. **Take breaks** - Don't run automation every day
6. **Vary content** - Don't repeat the same messages/comments

---

## Rate Limit Summary

| Action | Recommended Limit | LinkedIn Limit |
|--------|-------------------|----------------|
| Profile scrapes | 50/session | ~100/day |
| Connection requests | 25/day | 100/week |
| Messages | 25/day | Varies |
| Posts | 2-3/day | 20/day |
| Comments | 10-20/day | Varies |

---

## Troubleshooting

### "Content Unavailable" during scraping
- Profile may be private or restricted
- LinkedIn may be rate-limiting
- Try reducing scraping speed

### Login issues
- Delete `linkedin/.tmp/approach2/linkedin_session.json`
- Run any command to trigger fresh login
- Complete any verification steps manually

### CAPTCHAs appearing
- Too many automated actions
- Take a 24-hour break
- Reduce rate limits in `.env.approach2`

### Message limit reached
- LinkedIn has daily limits
- Wait 24 hours before sending more
- Consider LinkedIn Premium for higher limits