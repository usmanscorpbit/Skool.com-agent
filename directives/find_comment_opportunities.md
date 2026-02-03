# Find Comment Opportunities

## Goal
Analyze scraped Skool posts to identify the best opportunities to comment for visibility and engagement.

## Inputs
- **mode** (optional): Scoring strategy - one of:
  - `recent` - Prioritize new posts where you can be early
  - `engagement` - Prioritize high-engagement posts for max exposure
  - `topic` - Prioritize posts matching your expertise keywords
  - `balanced` - Weighted combination of all factors (default)
- **top_n** (optional): Number of top opportunities to return (default: 20)
- **keywords** (optional): Override topic keywords from `.env`

## Prerequisites
1. Run `scrape_skool_posts.md` first to generate `.tmp/scraped_posts.json`
2. (Optional) Configure `TOPIC_KEYWORDS` in `.env` for topic-based filtering

## Execution Steps

1. **Verify scraped data exists**
   ```bash
   ls .tmp/scraped_posts.json
   ```

2. **Run the analyzer**
   ```bash
   cd execution
   python analyze_posts.py balanced 20
   ```

   Or for specific modes:
   ```bash
   python analyze_posts.py recent 15    # Early bird strategy
   python analyze_posts.py engagement 10  # High visibility strategy
   python analyze_posts.py topic 20       # Expertise matching
   ```

3. **Review results**
   - Top opportunities printed to console
   - Full results in `.tmp/comment_opportunities.csv`
   - Detailed analysis in `.tmp/analysis_results.json`

4. **(Optional) Export to Google Sheets**
   ```bash
   python export_to_sheet.py
   ```

## Outputs
- `.tmp/comment_opportunities.csv` - Ranked list of posts to comment on
- `.tmp/analysis_results.json` - Full analysis with scores and patterns
- Google Sheet (if exported) - Cloud-accessible results

## Scoring Criteria

### Recency Score (0-1)
| Age | Score |
|-----|-------|
| < 2 hours | 1.0 |
| < 6 hours | 0.9 |
| < 12 hours | 0.8 |
| < 24 hours | 0.7 |
| < 48 hours | 0.5 |
| < 72 hours | 0.3 |
| Older | 0.1 |

### Opportunity Score (0-1)
Sweet spot: Some likes + few comments = room to add value
| Condition | Score |
|-----------|-------|
| 5+ likes, ≤3 comments | 1.0 |
| 3+ likes, ≤5 comments | 0.8 |
| 1+ likes, ≤3 comments | 0.7 |
| No engagement yet | 0.6 |
| 20+ comments | 0.2 |

### Engagement Score (0-1)
Total engagement (likes + comments) for visibility
| Engagement | Score |
|------------|-------|
| 50+ | 1.0 |
| 30-49 | 0.9 |
| 20-29 | 0.8 |
| 10-19 | 0.7 |
| 5-9 | 0.5 |
| <5 | 0.3 |

### Topic Score (0-1)
Matches against `TOPIC_KEYWORDS` in `.env`
| Matches | Score |
|---------|-------|
| 3+ keywords | 1.0 |
| 2 keywords | 0.8 |
| 1 keyword | 0.6 |
| 0 keywords | 0.2 |

## Workflow Recommendation

**Daily routine:**
1. Scrape your target community (50 posts)
2. Run analysis in `recent` mode for early engagement
3. Comment on top 5-10 posts
4. Track which comments get replies/engagement

**Weekly content research:**
1. Scrape multiple communities (100+ posts each)
2. Run in `balanced` mode
3. Export to Google Sheets for review
4. Use patterns to inform your own content
