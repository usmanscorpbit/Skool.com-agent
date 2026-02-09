"""
Profile Analyzer for LinkedIn Automation
Scores and categorizes profiles for targeting
"""

from typing import List, Optional, Dict
from dataclasses import dataclass
from .types import LinkedInProfile, LinkedInPost, CommentOpportunity


@dataclass
class TargetCriteria:
    """Criteria for identifying target profiles"""
    industries: List[str] = None
    titles: List[str] = None
    title_keywords: List[str] = None
    companies: List[str] = None
    company_sizes: List[str] = None  # "startup", "mid", "enterprise"
    locations: List[str] = None
    min_connections: int = 0
    min_followers: int = 0
    connection_degrees: List[int] = None  # [1, 2] for 1st and 2nd degree

    def __post_init__(self):
        self.industries = self.industries or []
        self.titles = self.titles or []
        self.title_keywords = self.title_keywords or []
        self.companies = self.companies or []
        self.company_sizes = self.company_sizes or []
        self.locations = self.locations or []
        self.connection_degrees = self.connection_degrees or [1, 2, 3]


class ProfileAnalyzer:
    """
    Analyzes LinkedIn profiles for relevance and targeting.
    """

    def __init__(self, criteria: Optional[TargetCriteria] = None):
        """
        Initialize with target criteria.

        Args:
            criteria: TargetCriteria for scoring profiles
        """
        self.criteria = criteria or TargetCriteria()

    def score_profile(self, profile: LinkedInProfile) -> float:
        """
        Score a profile's relevance (0.0 to 1.0).

        Args:
            profile: LinkedInProfile to score

        Returns:
            Relevance score between 0.0 and 1.0
        """
        scores = []
        weights = []

        # Industry match
        if self.criteria.industries and profile.industry:
            industry_match = any(
                ind.lower() in profile.industry.lower()
                for ind in self.criteria.industries
            )
            scores.append(1.0 if industry_match else 0.0)
            weights.append(0.25)

        # Title match
        if self.criteria.titles or self.criteria.title_keywords:
            title_score = self._score_title(profile)
            scores.append(title_score)
            weights.append(0.30)

        # Company match
        if self.criteria.companies and profile.company:
            company_match = any(
                comp.lower() in profile.company.lower()
                for comp in self.criteria.companies
            )
            scores.append(1.0 if company_match else 0.0)
            weights.append(0.15)

        # Location match
        if self.criteria.locations and profile.location:
            location_match = any(
                loc.lower() in profile.location.lower()
                for loc in self.criteria.locations
            )
            scores.append(1.0 if location_match else 0.0)
            weights.append(0.10)

        # Connection degree
        if profile.connection_degree:
            degree = profile.connection_degree.value
            if degree in self.criteria.connection_degrees:
                # Prefer closer connections
                degree_score = 1.0 if degree == 1 else (0.7 if degree == 2 else 0.4)
            else:
                degree_score = 0.0
            scores.append(degree_score)
            weights.append(0.10)

        # Follower/connection count bonus
        if profile.followers and profile.followers >= self.criteria.min_followers:
            follower_score = min(1.0, profile.followers / 10000)
            scores.append(follower_score)
            weights.append(0.10)

        if not scores:
            return 0.5  # Default middle score if no criteria

        # Weighted average
        total_weight = sum(weights)
        weighted_sum = sum(s * w for s, w in zip(scores, weights))
        return weighted_sum / total_weight if total_weight > 0 else 0.5

    def _score_title(self, profile: LinkedInProfile) -> float:
        """Score based on title matching"""
        if not profile.title and not profile.headline:
            return 0.0

        title_text = (profile.title or "") + " " + (profile.headline or "")
        title_text = title_text.lower()

        # Exact title match
        for title in self.criteria.titles:
            if title.lower() in title_text:
                return 1.0

        # Keyword match
        keyword_matches = sum(
            1 for kw in self.criteria.title_keywords
            if kw.lower() in title_text
        )
        if keyword_matches > 0:
            return min(1.0, keyword_matches * 0.3)

        return 0.0

    def categorize_profile(self, profile: LinkedInProfile) -> str:
        """
        Categorize a profile.

        Returns one of: "prospect", "influencer", "competitor", "partner", "other"
        """
        score = self.score_profile(profile)
        headline = (profile.headline or "").lower()
        title = (profile.title or "").lower()

        # Check for influencer indicators
        influencer_keywords = ["speaker", "author", "thought leader", "influencer", "creator"]
        if any(kw in headline or kw in title for kw in influencer_keywords):
            if profile.followers and profile.followers > 10000:
                return "influencer"

        # Check for competitor indicators
        competitor_keywords = ["founder", "ceo", "co-founder"]
        if any(kw in headline or kw in title for kw in competitor_keywords):
            if score < 0.5:  # Different industry/focus
                return "competitor"

        # Check for partner indicators
        partner_keywords = ["partner", "agency", "consultant", "advisor"]
        if any(kw in headline or kw in title for kw in partner_keywords):
            if score > 0.6:
                return "partner"

        # Default based on score
        if score > 0.7:
            return "prospect"

        return "other"

    def extract_personalization_points(self, profile: LinkedInProfile) -> List[str]:
        """
        Extract points for message personalization.

        Args:
            profile: Profile to analyze

        Returns:
            List of personalization points
        """
        points = []

        # Company mention
        if profile.company:
            points.append(f"You work at {profile.company}")

        # Title mention
        if profile.title:
            points.append(f"Your role as {profile.title}")

        # Industry mention
        if profile.industry:
            points.append(f"Your expertise in {profile.industry}")

        # Location mention
        if profile.location:
            points.append(f"Based in {profile.location}")

        # Recent experience
        if profile.experience and len(profile.experience) > 0:
            recent = profile.experience[0]
            if isinstance(recent, dict) and "company" in recent:
                points.append(f"Your experience at {recent['company']}")

        # Skills mention
        if profile.skills and len(profile.skills) > 0:
            top_skills = profile.skills[:3]
            points.append(f"Your skills in {', '.join(top_skills)}")

        # Follower mention (for influencers)
        if profile.followers and profile.followers > 5000:
            points.append(f"Your growing audience of {profile.followers:,} followers")

        return points

    def find_comment_opportunities(
        self,
        posts: List[LinkedInPost],
        max_results: int = 10
    ) -> List[CommentOpportunity]:
        """
        Find best posts to comment on.

        Scoring factors:
        - Recency (newer is better)
        - Engagement sweet spot (some likes, few comments)
        - Author relevance
        - Content relevance

        Args:
            posts: List of posts to analyze
            max_results: Maximum opportunities to return

        Returns:
            List of CommentOpportunity sorted by score
        """
        opportunities = []

        for post in posts:
            score = 0.0
            reasons = []

            # Recency score (based on relative time)
            recency_score = self._score_recency(post.posted_relative)
            score += recency_score * 0.3
            if recency_score > 0.7:
                reasons.append("Recent post")

            # Engagement opportunity score
            # Sweet spot: has some visibility but room for comments
            engagement_score = self._score_engagement_opportunity(post)
            score += engagement_score * 0.35
            if engagement_score > 0.6:
                reasons.append("Good engagement opportunity")

            # Total visibility score
            if post.total_engagement > 50:
                visibility_score = min(1.0, post.total_engagement / 500)
                score += visibility_score * 0.2
                reasons.append("High visibility post")

            # Comment-to-like ratio (fewer comments relative to likes = opportunity)
            if post.likes > 10:
                ratio = post.comments / post.likes
                if ratio < 0.1:  # Less than 10% comments to likes
                    score += 0.15
                    reasons.append("Low comment ratio")

            opportunities.append(CommentOpportunity(
                post=post,
                score=min(1.0, score),
                reasons=reasons
            ))

        # Sort by score and return top results
        opportunities.sort(key=lambda x: x.score, reverse=True)
        return opportunities[:max_results]

    def _score_recency(self, relative_time: Optional[str]) -> float:
        """Score based on relative time string (2h, 3d, etc.)"""
        if not relative_time:
            return 0.5

        relative_time = relative_time.lower().strip()

        # Parse time units
        if "m" in relative_time and "mo" not in relative_time:  # minutes
            return 1.0
        elif "h" in relative_time:  # hours
            try:
                hours = int(''.join(filter(str.isdigit, relative_time)))
                if hours <= 6:
                    return 0.95
                elif hours <= 12:
                    return 0.85
                elif hours <= 24:
                    return 0.7
                else:
                    return 0.5
            except ValueError:
                return 0.7
        elif "d" in relative_time:  # days
            try:
                days = int(''.join(filter(str.isdigit, relative_time)))
                if days == 1:
                    return 0.6
                elif days <= 3:
                    return 0.4
                elif days <= 7:
                    return 0.2
                else:
                    return 0.1
            except ValueError:
                return 0.3
        elif "w" in relative_time:  # weeks
            return 0.1
        elif "mo" in relative_time:  # months
            return 0.05

        return 0.5

    def _score_engagement_opportunity(self, post: LinkedInPost) -> float:
        """Score based on engagement opportunity (sweet spot analysis)"""
        likes = post.likes
        comments = post.comments

        # Sweet spot: 10-100 likes, < 10 comments
        if 10 <= likes <= 100 and comments < 10:
            return 1.0

        # Good: 5-200 likes, < 20 comments
        if 5 <= likes <= 200 and comments < 20:
            return 0.8

        # Decent: has likes but not too many comments
        if likes > 0 and comments < likes * 0.2:
            return 0.6

        # Too early (no engagement yet)
        if likes == 0 and comments == 0:
            return 0.3

        # Too crowded (many comments)
        if comments > 50:
            return 0.2

        return 0.4

    def rank_profiles(
        self,
        profiles: List[LinkedInProfile],
        top_n: int = 20
    ) -> List[Dict]:
        """
        Rank profiles by relevance.

        Args:
            profiles: Profiles to rank
            top_n: Number of top profiles to return

        Returns:
            List of dicts with profile, score, and category
        """
        ranked = []
        for profile in profiles:
            score = self.score_profile(profile)
            category = self.categorize_profile(profile)
            personalization = self.extract_personalization_points(profile)

            ranked.append({
                "profile": profile,
                "score": score,
                "category": category,
                "personalization_points": personalization
            })

        ranked.sort(key=lambda x: x["score"], reverse=True)
        return ranked[:top_n]
