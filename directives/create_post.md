# Create Post

## Goal
Generate a high-quality Skool post based on content patterns and ideas from scraped data.

## Inputs
- **topic** (required): What the post should be about
- **style** (optional): question, story, tip, announcement, discussion
- **community** (optional): Target community for tone matching
- **reference_posts** (optional): Top posts to use as inspiration

## Workflow

### Step 1: Gather Context
If not already done:
1. Run `scrape_skool_posts.md` on target community
2. Run `find_comment_opportunities.md` to identify top performers
3. Review `.tmp/analysis_results.json` for patterns

### Step 2: Generate Post
The orchestrator (Claude) will generate the post directly based on:
- Topic provided by user
- Engagement patterns from scraped data
- Community tone and style

### Step 3: Output Format
```
TITLE: [Catchy, pattern-matched title]

BODY:
[Post content - hook, value, CTA]

---
NOTES:
- Why this format works
- Suggested posting time
- Expected engagement
```

## Post Frameworks That Work

### 1. Question Post
```
[Provocative question related to pain point]

I've been thinking about [topic] and wondering...

[2-3 bullet points expanding the question]

What's your take?
```

### 2. Quick Win / Tip
```
[Number] [benefit] in [timeframe]

Here's what I learned:

1. [Tip 1]
2. [Tip 2]
3. [Tip 3]

Which one are you trying first?
```

### 3. Story Post
```
[Attention-grabbing opener about transformation]

[Brief backstory - the struggle]

[The turning point]

[The result + lesson]

Anyone else experienced this?
```

### 4. Resource Share
```
Just found [resource/tool/method] that [benefit]

Here's how it works:
[Brief explanation]

[Link or details]

Has anyone else tried this?
```

## Best Practices
- Keep titles under 60 characters
- First line should hook attention
- End with a question or CTA to drive comments
- Use line breaks for readability
- Match community tone (casual vs professional)
