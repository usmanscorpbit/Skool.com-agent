# Auto Engage Workflow

## Goal
Fully automated Skool community engagement. User provides community URL → Agent does everything automatically → User just picks which content to post.

## Trigger
User pastes a Skool community URL (e.g., `https://www.skool.com/muggles`)

## Automated Workflow

### Phase 1: Scrape & Analyze (Automatic)
1. Authenticate with Skool using saved session
2. Scrape community posts (max 20)
3. Analyze for engagement opportunities
4. Identify top 3 posts for commenting
5. Scrape comments from those posts for reply opportunities
6. Export data to Google Sheets

### Phase 2: Generate Options (Automatic)
Based on scraped data, generate:

**Comments (3-5 options per top post)**
- Analyze post content, title, author
- Generate thoughtful, engaging comments
- Vary styles: question, agreement, insight, personal experience

**Replies (3-5 options per existing comment)**
- Read existing comments on top posts
- Generate replies that add value
- Options: agree & expand, ask follow-up, share related experience

**New Posts (3-5 options)**
- Analyze top engagement patterns
- Use frameworks from `create_post.md`
- Match community tone and topics

### Phase 3: User Selection
Present options to user:
```
📝 COMMENT OPTIONS for "Post Title"
[1] Comment text option 1...
[2] Comment text option 2...
[3] Comment text option 3...

💬 REPLY OPTIONS to @username's comment
[1] Reply text option 1...
[2] Reply text option 2...
[3] Reply text option 3...

📄 NEW POST OPTIONS
[1] Title: "..." - Body preview...
[2] Title: "..." - Body preview...
[3] Title: "..." - Body preview...
```

User responds with their choices (e.g., "Comment 2, Reply 1, Post 3")

### Phase 4: Auto-Post (After Approval)
Execute selected actions:
1. Post approved comment → `post_comment()`
2. Post approved reply → `post_reply()`
3. Create approved post → `create_post()`

Report success/failure for each action.

## Execution Scripts Used
- `execution/skool_auth.py` - Authentication
- `execution/skool_scraper.py` - Scraping posts
- `execution/analyze_posts.py` - Finding opportunities
- `execution/auto_engage.py` - Posting actions
- `execution/export_to_sheet.py` - Google Sheets export

## Comment Generation Guidelines

### Style Variations
1. **Insightful Agreement**: "This resonates because [reason]. I've found that [related insight]..."
2. **Curious Question**: "Interesting take! Have you considered [angle]? I'm curious about..."
3. **Personal Experience**: "This hits home. When I [similar situation], I learned..."
4. **Value Add**: "Great point. Adding to this - [complementary tip or resource]..."
5. **Engagement Prompt**: "Love this! What's been the biggest challenge with [topic] for you?"

### Reply Guidelines
- Reference the original comment specifically
- Add new value, don't just agree
- Keep it conversational
- Ask follow-up questions when appropriate

### Post Generation Frameworks
See `directives/create_post.md` for:
- Question posts
- Quick win/tip posts
- Story posts
- Resource share posts

## Error Handling
- If login fails → Prompt user to check credentials
- If scraping returns no posts → Report and suggest different community
- If posting fails → Report error, don't retry without user consent
- Always clean up browser resources

## Output
- Google Sheets updated with scraped data
- Confirmation of each posted item
- Links to posted content when available
