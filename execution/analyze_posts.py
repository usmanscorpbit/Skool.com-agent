"""
Post Analyzer
Identifies comment opportunities and content patterns from scraped Skool posts
"""

import os
import json
import csv
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).parent.parent
INPUT_DIR = BASE_DIR / ".tmp"
OUTPUT_DIR = BASE_DIR / ".tmp"


def load_posts(filename: str = "scraped_posts.json") -> list[dict]:
    """Load posts from JSON file"""
    filepath = INPUT_DIR / filename
    if not filepath.exists():
        raise FileNotFoundError(f"No posts file found at {filepath}")

    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def get_topic_keywords() -> list[str]:
    """Get topic keywords from environment or return defaults"""
    keywords_str = os.getenv("TOPIC_KEYWORDS", "")
    if keywords_str:
        return [k.strip().lower() for k in keywords_str.split(",") if k.strip()]
    return []


def calculate_recency_score(post: dict) -> float:
    """
    Score based on how recent the post is.
    Higher score = more recent = better opportunity to be early.
    """
    posted_at = post.get('posted_at')
    if not posted_at:
        return 0.5  # Default middle score if no timestamp

    try:
        post_time = datetime.fromisoformat(posted_at)
        hours_ago = (datetime.now() - post_time).total_seconds() / 3600

        # Score formula: newer posts get higher scores
        if hours_ago < 2:
            return 1.0
        elif hours_ago < 6:
            return 0.9
        elif hours_ago < 12:
            return 0.8
        elif hours_ago < 24:
            return 0.7
        elif hours_ago < 48:
            return 0.5
        elif hours_ago < 72:
            return 0.3
        else:
            return 0.1
    except:
        return 0.5


def calculate_engagement_opportunity_score(post: dict) -> float:
    """
    Score based on engagement metrics.
    Sweet spot: some likes but few comments = opportunity to add value.
    """
    likes = post.get('likes', 0)
    comments = post.get('comments_count', 0)

    # High likes + low comments = great opportunity
    if likes >= 5 and comments <= 3:
        return 1.0
    elif likes >= 3 and comments <= 5:
        return 0.8
    elif likes >= 1 and comments <= 3:
        return 0.7
    elif comments == 0:
        return 0.6  # No engagement yet
    elif comments > 20:
        return 0.2  # Too crowded
    else:
        return 0.5


def calculate_high_engagement_score(post: dict) -> float:
    """
    Score for high engagement posts (maximum exposure strategy).
    More engagement = more visibility for your comment.
    """
    likes = post.get('likes', 0)
    comments = post.get('comments_count', 0)
    total_engagement = likes + comments

    if total_engagement >= 50:
        return 1.0
    elif total_engagement >= 30:
        return 0.9
    elif total_engagement >= 20:
        return 0.8
    elif total_engagement >= 10:
        return 0.7
    elif total_engagement >= 5:
        return 0.5
    else:
        return 0.3


def calculate_topic_score(post: dict, keywords: list[str]) -> float:
    """
    Score based on topic relevance to your expertise keywords.
    """
    if not keywords:
        return 0.5  # No keywords configured, neutral score

    title = post.get('title', '').lower()
    content = post.get('content', '').lower()
    text = f"{title} {content}"

    matches = sum(1 for kw in keywords if kw in text)

    if matches >= 3:
        return 1.0
    elif matches >= 2:
        return 0.8
    elif matches >= 1:
        return 0.6
    else:
        return 0.2


def analyze_for_comment_opportunities(
    posts: list[dict],
    mode: str = "balanced",
    keywords: Optional[list[str]] = None
) -> list[dict]:
    """
    Analyze posts and rank them for comment opportunities.

    Modes:
    - "recent": Prioritize recent posts with few comments (early visibility)
    - "engagement": Prioritize high engagement posts (maximum exposure)
    - "topic": Prioritize posts matching your topic keywords
    - "balanced": Weighted combination of all factors

    Returns posts sorted by opportunity score with analysis.
    """
    if keywords is None:
        keywords = get_topic_keywords()

    analyzed = []

    for post in posts:
        recency = calculate_recency_score(post)
        opportunity = calculate_engagement_opportunity_score(post)
        engagement = calculate_high_engagement_score(post)
        topic = calculate_topic_score(post, keywords)

        # Calculate final score based on mode
        if mode == "recent":
            final_score = recency * 0.5 + opportunity * 0.4 + topic * 0.1
        elif mode == "engagement":
            final_score = engagement * 0.5 + recency * 0.2 + topic * 0.3
        elif mode == "topic":
            final_score = topic * 0.5 + recency * 0.3 + opportunity * 0.2
        else:  # balanced
            final_score = (recency * 0.25 + opportunity * 0.25 +
                          engagement * 0.25 + topic * 0.25)

        analyzed.append({
            **post,
            'scores': {
                'recency': round(recency, 2),
                'opportunity': round(opportunity, 2),
                'engagement': round(engagement, 2),
                'topic': round(topic, 2),
                'final': round(final_score, 2)
            },
            'recommendation': get_recommendation(recency, opportunity, engagement, topic)
        })

    # Sort by final score descending
    analyzed.sort(key=lambda x: x['scores']['final'], reverse=True)

    return analyzed


def get_recommendation(recency: float, opportunity: float,
                       engagement: float, topic: float) -> str:
    """Generate a human-readable recommendation"""
    reasons = []

    if recency >= 0.8:
        reasons.append("fresh post")
    if opportunity >= 0.7:
        reasons.append("low competition")
    if engagement >= 0.7:
        reasons.append("high visibility")
    if topic >= 0.6:
        reasons.append("matches your expertise")

    if not reasons:
        return "Average opportunity"

    return "Good: " + ", ".join(reasons)


def analyze_content_patterns(posts: list[dict]) -> dict:
    """
    Analyze posts to identify content patterns and ideas.
    Useful for creating your own posts.
    """
    if not posts:
        return {}

    # Engagement stats
    likes = [p.get('likes', 0) for p in posts]
    comments = [p.get('comments_count', 0) for p in posts]

    avg_likes = sum(likes) / len(likes) if likes else 0
    avg_comments = sum(comments) / len(comments) if comments else 0

    # Top performing posts
    sorted_by_engagement = sorted(
        posts,
        key=lambda x: x.get('likes', 0) + x.get('comments_count', 0),
        reverse=True
    )
    top_posts = sorted_by_engagement[:5]

    # Extract common words from top posts (simple analysis)
    top_titles = [p.get('title', '') for p in top_posts]

    # Category distribution
    categories = {}
    for p in posts:
        cat = p.get('category', 'Uncategorized')
        categories[cat] = categories.get(cat, 0) + 1

    return {
        'total_posts_analyzed': len(posts),
        'engagement_benchmarks': {
            'avg_likes': round(avg_likes, 1),
            'avg_comments': round(avg_comments, 1),
            'max_likes': max(likes) if likes else 0,
            'max_comments': max(comments) if comments else 0
        },
        'top_performing_posts': [
            {
                'title': p.get('title', ''),
                'url': p.get('url', ''),
                'likes': p.get('likes', 0),
                'comments': p.get('comments_count', 0)
            }
            for p in top_posts
        ],
        'category_distribution': categories,
        'content_ideas': [
            f"Post similar to: {t[:100]}" for t in top_titles if t
        ]
    }


def save_analysis_to_csv(
    analyzed_posts: list[dict],
    filename: str = "comment_opportunities.csv"
):
    """Save analyzed posts to CSV"""
    filepath = OUTPUT_DIR / filename

    fieldnames = [
        'rank', 'title', 'author', 'url', 'likes', 'comments_count',
        'timestamp', 'final_score', 'recency_score', 'opportunity_score',
        'engagement_score', 'topic_score', 'recommendation'
    ]

    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for i, post in enumerate(analyzed_posts, 1):
            writer.writerow({
                'rank': i,
                'title': post.get('title', ''),
                'author': post.get('author', ''),
                'url': post.get('url', ''),
                'likes': post.get('likes', 0),
                'comments_count': post.get('comments_count', 0),
                'timestamp': post.get('timestamp', ''),
                'final_score': post['scores']['final'],
                'recency_score': post['scores']['recency'],
                'opportunity_score': post['scores']['opportunity'],
                'engagement_score': post['scores']['engagement'],
                'topic_score': post['scores']['topic'],
                'recommendation': post.get('recommendation', '')
            })

    print(f"Saved analysis to {filepath}")
    return filepath


def save_analysis_to_json(
    analyzed_posts: list[dict],
    patterns: dict,
    filename: str = "analysis_results.json"
):
    """Save full analysis to JSON"""
    filepath = OUTPUT_DIR / filename

    results = {
        'generated_at': datetime.now().isoformat(),
        'comment_opportunities': analyzed_posts,
        'content_patterns': patterns
    }

    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"Saved full analysis to {filepath}")
    return filepath


def run_analysis(
    input_file: str = "scraped_posts.json",
    mode: str = "balanced",
    top_n: int = 20
) -> tuple[list[dict], dict]:
    """
    Main entry point - analyze posts and return results.

    Args:
        input_file: Path to scraped posts JSON
        mode: Scoring mode (recent/engagement/topic/balanced)
        top_n: Number of top opportunities to return

    Returns:
        (top_opportunities, content_patterns)
    """
    posts = load_posts(input_file)
    print(f"Loaded {len(posts)} posts for analysis")

    # Analyze for comment opportunities
    analyzed = analyze_for_comment_opportunities(posts, mode=mode)
    top_opportunities = analyzed[:top_n]

    # Analyze content patterns
    patterns = analyze_content_patterns(posts)

    # Save results
    save_analysis_to_csv(top_opportunities)
    save_analysis_to_json(analyzed, patterns)

    return top_opportunities, patterns


if __name__ == "__main__":
    import sys

    mode = sys.argv[1] if len(sys.argv) > 1 else "balanced"
    top_n = int(sys.argv[2]) if len(sys.argv) > 2 else 20

    print(f"Running analysis (mode={mode}, top={top_n})...")

    try:
        opportunities, patterns = run_analysis(mode=mode, top_n=top_n)

        print(f"\n=== TOP {len(opportunities)} COMMENT OPPORTUNITIES ===\n")
        for i, post in enumerate(opportunities[:10], 1):
            print(f"{i}. [{post['scores']['final']:.2f}] {post.get('title', 'Untitled')[:60]}")
            print(f"   {post.get('recommendation', '')}")
            print(f"   Likes: {post.get('likes', 0)} | Comments: {post.get('comments_count', 0)}")
            print(f"   URL: {post.get('url', 'N/A')}")
            print()

        print("\n=== CONTENT PATTERNS ===\n")
        print(f"Avg Likes: {patterns['engagement_benchmarks']['avg_likes']}")
        print(f"Avg Comments: {patterns['engagement_benchmarks']['avg_comments']}")
        print(f"\nTop performing topics:")
        for idea in patterns.get('content_ideas', [])[:5]:
            print(f"  - {idea}")

    except FileNotFoundError as e:
        print(f"Error: {e}")
        print("Run skool_scraper.py first to generate post data.")
