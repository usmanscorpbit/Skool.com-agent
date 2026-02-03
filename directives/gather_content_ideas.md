# Gather Content Ideas

## Goal
Analyze top-performing Skool posts to identify content patterns, engagement benchmarks, and ideas for your own posts.

## Inputs
- **communities** (required): List of Skool community URLs to analyze
- **posts_per_community** (optional): Posts to scrape from each (default: 50)

## Prerequisites
1. Run `scrape_skool_posts.md` for each target community
2. Have scraped data in `.tmp/scraped_posts.json`

## Execution Steps

1. **Scrape multiple communities** (if needed)
   ```bash
   cd execution
   python skool_scraper.py "https://www.skool.com/community-1" 100
   # Rename output
   mv ../.tmp/scraped_posts.json ../.tmp/community1_posts.json

   python skool_scraper.py "https://www.skool.com/community-2" 100
   mv ../.tmp/scraped_posts.json ../.tmp/community2_posts.json
   ```

2. **Run content analysis**
   ```bash
   python analyze_posts.py balanced 50
   ```

3. **Export to Google Sheets for review**
   ```bash
   python export_to_sheet.py
   ```

## Outputs

### Engagement Benchmarks
- Average likes per post
- Average comments per post
- Maximum engagement seen
- Engagement by category/channel

### Top Performing Posts
- Posts with highest combined engagement
- Common patterns in titles
- Content themes that resonate

### Content Ideas
- Suggested topics based on what's working
- Posting time insights (when are popular posts made)
- Category recommendations

## Analysis Questions to Answer

1. **What topics get the most engagement?**
   - Look at top 10 posts by likes
   - Identify common themes/keywords

2. **What's the engagement threshold?**
   - Use benchmarks to set realistic goals
   - Posts with 2x avg engagement = worth studying

3. **What format works?**
   - Questions vs statements
   - Short vs long posts
   - Posts with images/videos

4. **When to post?**
   - Check timestamps of top performers
   - Identify peak activity windows

## Using the Data

### For Post Creation
1. Review top-performing post titles
2. Identify patterns (questions, hooks, topics)
3. Create similar content with your unique angle

### For Engagement Strategy
1. Note which categories are most active
2. Identify prolific authors to learn from
3. Track what types of comments get replies

## Google Sheet Structure

**Tab 1: Comment Opportunities**
- Ranked posts to engage with now

**Tab 2: Content Patterns**
- Engagement benchmarks
- Top posts to study
- Content idea prompts

## Example Workflow

```
Morning routine:
1. Scrape community (30 posts)
2. Analyze for comment opportunities
3. Comment on top 5
4. Note any content ideas

Weekly content planning:
1. Review Content Patterns tab
2. Pick 3-5 content ideas
3. Draft posts inspired by top performers
4. Schedule throughout the week
```
