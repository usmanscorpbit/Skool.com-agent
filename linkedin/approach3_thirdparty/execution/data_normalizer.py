"""
Data Normalizer
Converts data from different third-party services to shared types
"""

import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from shared.types import (
    LinkedInProfile,
    LinkedInPost,
    ApproachType,
    ConnectionDegree,
    ScrapingResult
)

BASE_DIR = Path(__file__).parent.parent.parent
OUTPUT_DIR = BASE_DIR / ".tmp" / "approach3"


class DataNormalizer:
    """
    Normalizes data from Phantombuster and Apify to shared types.
    """

    @staticmethod
    def normalize_phantombuster_profile(data: Dict) -> LinkedInProfile:
        """
        Convert Phantombuster profile data to LinkedInProfile.

        Args:
            data: Raw Phantombuster profile data

        Returns:
            LinkedInProfile object
        """
        # Phantombuster profile fields (may vary by phantom)
        return LinkedInProfile(
            id=data.get("profileId", data.get("vmid", str(hash(data.get("profileUrl", ""))))),
            name=data.get("name", data.get("fullName", "")),
            headline=data.get("headline", data.get("title", "")),
            profile_url=data.get("profileUrl", data.get("linkedinProfile", "")),
            location=data.get("location", data.get("city", "")),
            about=data.get("summary", data.get("about", "")),
            company=data.get("company", data.get("companyName", "")),
            title=data.get("jobTitle", data.get("currentJob", "")),
            industry=data.get("industry", ""),
            connections=DataNormalizer._parse_int(data.get("connectionCount", data.get("connections"))),
            followers=DataNormalizer._parse_int(data.get("followerCount", data.get("followers"))),
            connection_degree=DataNormalizer._parse_connection_degree(data.get("degree")),
            experience=data.get("jobs", data.get("experience", [])),
            skills=data.get("skills", []),
            source_approach=ApproachType.THIRDPARTY,
            scraped_at=datetime.now()
        )

    @staticmethod
    def normalize_apify_profile(data: Dict) -> LinkedInProfile:
        """
        Convert Apify profile data to LinkedInProfile.

        Args:
            data: Raw Apify profile data

        Returns:
            LinkedInProfile object
        """
        # Apify profile fields (varies by actor)
        return LinkedInProfile(
            id=data.get("id", data.get("publicIdentifier", str(hash(data.get("url", ""))))),
            name=data.get("fullName", data.get("name", "")),
            headline=data.get("headline", ""),
            profile_url=data.get("url", data.get("profileUrl", data.get("linkedinUrl", ""))),
            location=data.get("location", data.get("locationName", "")),
            about=data.get("summary", data.get("about", "")),
            company=data.get("companyName", data.get("currentCompany", "")),
            title=data.get("title", data.get("currentTitle", "")),
            industry=data.get("industryName", data.get("industry", "")),
            connections=DataNormalizer._parse_int(data.get("connectionsCount", data.get("connections"))),
            followers=DataNormalizer._parse_int(data.get("followersCount", data.get("followers"))),
            connection_degree=ConnectionDegree.OUT_OF_NETWORK,  # Usually not provided
            experience=data.get("experience", data.get("positions", [])),
            skills=DataNormalizer._extract_skills(data.get("skills", [])),
            source_approach=ApproachType.THIRDPARTY,
            scraped_at=datetime.now()
        )

    @staticmethod
    def normalize_phantombuster_post(data: Dict) -> LinkedInPost:
        """
        Convert Phantombuster post data to LinkedInPost.

        Args:
            data: Raw Phantombuster post data

        Returns:
            LinkedInPost object
        """
        return LinkedInPost(
            id=data.get("postId", data.get("activityId", str(hash(data.get("postUrl", ""))))),
            author_name=data.get("authorName", data.get("name", "")),
            author_profile_url=data.get("authorProfile", data.get("profileUrl", "")),
            author_headline=data.get("authorHeadline", ""),
            content=data.get("postContent", data.get("text", data.get("content", ""))),
            post_url=data.get("postUrl", data.get("url", "")),
            likes=DataNormalizer._parse_int(data.get("likeCount", data.get("likes", 0))),
            comments=DataNormalizer._parse_int(data.get("commentCount", data.get("comments", 0))),
            shares=DataNormalizer._parse_int(data.get("shareCount", data.get("reposts", 0))),
            posted_relative=data.get("postedAgo", data.get("timestamp", "")),
            hashtags=DataNormalizer._extract_hashtags(data.get("postContent", "")),
            source_approach=ApproachType.THIRDPARTY,
            scraped_at=datetime.now()
        )

    @staticmethod
    def normalize_apify_post(data: Dict) -> LinkedInPost:
        """
        Convert Apify post data to LinkedInPost.

        Args:
            data: Raw Apify post data

        Returns:
            LinkedInPost object
        """
        return LinkedInPost(
            id=data.get("urn", data.get("id", str(hash(data.get("url", ""))))),
            author_name=data.get("author", {}).get("name", data.get("authorName", "")),
            author_profile_url=data.get("author", {}).get("url", data.get("authorUrl", "")),
            author_headline=data.get("author", {}).get("headline", ""),
            content=data.get("text", data.get("content", "")),
            post_url=data.get("url", data.get("postUrl", "")),
            likes=DataNormalizer._parse_int(data.get("numLikes", data.get("likes", 0))),
            comments=DataNormalizer._parse_int(data.get("numComments", data.get("comments", 0))),
            shares=DataNormalizer._parse_int(data.get("numShares", data.get("reposts", 0))),
            posted_at=DataNormalizer._parse_datetime(data.get("postedAt", data.get("timestamp"))),
            hashtags=data.get("hashtags", DataNormalizer._extract_hashtags(data.get("text", ""))),
            source_approach=ApproachType.THIRDPARTY,
            scraped_at=datetime.now()
        )

    @staticmethod
    def normalize_profiles(
        data: List[Dict],
        source: str  # "phantombuster" or "apify"
    ) -> ScrapingResult:
        """
        Normalize a list of profiles from any source.

        Args:
            data: List of raw profile data
            source: Source service name

        Returns:
            ScrapingResult with normalized profiles
        """
        profiles = []
        errors = []

        for item in data:
            try:
                if source == "phantombuster":
                    profile = DataNormalizer.normalize_phantombuster_profile(item)
                elif source == "apify":
                    profile = DataNormalizer.normalize_apify_profile(item)
                else:
                    raise ValueError(f"Unknown source: {source}")

                if profile.name:  # Only include if we got a name
                    profiles.append(profile)
            except Exception as e:
                errors.append(f"Failed to normalize profile: {e}")

        return ScrapingResult(
            success=len(profiles) > 0,
            approach=ApproachType.THIRDPARTY,
            profiles=profiles,
            errors=errors,
            metadata={
                "source": source,
                "raw_count": len(data),
                "normalized_count": len(profiles)
            }
        )

    @staticmethod
    def normalize_posts(
        data: List[Dict],
        source: str  # "phantombuster" or "apify"
    ) -> ScrapingResult:
        """
        Normalize a list of posts from any source.

        Args:
            data: List of raw post data
            source: Source service name

        Returns:
            ScrapingResult with normalized posts
        """
        posts = []
        errors = []

        for item in data:
            try:
                if source == "phantombuster":
                    post = DataNormalizer.normalize_phantombuster_post(item)
                elif source == "apify":
                    post = DataNormalizer.normalize_apify_post(item)
                else:
                    raise ValueError(f"Unknown source: {source}")

                if post.content:  # Only include if we got content
                    posts.append(post)
            except Exception as e:
                errors.append(f"Failed to normalize post: {e}")

        return ScrapingResult(
            success=len(posts) > 0,
            approach=ApproachType.THIRDPARTY,
            posts=posts,
            errors=errors,
            metadata={
                "source": source,
                "raw_count": len(data),
                "normalized_count": len(posts)
            }
        )

    # Helper methods

    @staticmethod
    def _parse_int(value: Any) -> Optional[int]:
        """Safely parse integer from various formats"""
        if value is None:
            return None
        if isinstance(value, int):
            return value
        if isinstance(value, str):
            # Handle "500+", "1.2K", etc.
            value = value.replace(",", "").replace("+", "").strip().lower()
            if "k" in value:
                return int(float(value.replace("k", "")) * 1000)
            if "m" in value:
                return int(float(value.replace("m", "")) * 1000000)
            try:
                return int(value)
            except ValueError:
                return None
        return None

    @staticmethod
    def _parse_connection_degree(value: Any) -> ConnectionDegree:
        """Parse connection degree from various formats"""
        if value is None:
            return ConnectionDegree.OUT_OF_NETWORK
        if isinstance(value, int):
            try:
                return ConnectionDegree(value)
            except ValueError:
                return ConnectionDegree.OUT_OF_NETWORK

        value = str(value).lower()
        if "1" in value or "first" in value:
            return ConnectionDegree.FIRST
        if "2" in value or "second" in value:
            return ConnectionDegree.SECOND
        if "3" in value or "third" in value:
            return ConnectionDegree.THIRD

        return ConnectionDegree.OUT_OF_NETWORK

    @staticmethod
    def _parse_datetime(value: Any) -> Optional[datetime]:
        """Parse datetime from various formats"""
        if value is None:
            return None
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            # Try common formats
            formats = [
                "%Y-%m-%dT%H:%M:%S.%fZ",
                "%Y-%m-%dT%H:%M:%SZ",
                "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%d"
            ]
            for fmt in formats:
                try:
                    return datetime.strptime(value, fmt)
                except ValueError:
                    continue
        return None

    @staticmethod
    def _extract_hashtags(text: str) -> List[str]:
        """Extract hashtags from text"""
        import re
        if not text:
            return []
        return re.findall(r'#(\w+)', text)

    @staticmethod
    def _extract_skills(skills_data: Any) -> List[str]:
        """Extract skills from various formats"""
        if not skills_data:
            return []
        if isinstance(skills_data, list):
            result = []
            for item in skills_data:
                if isinstance(item, str):
                    result.append(item)
                elif isinstance(item, dict):
                    result.append(item.get("name", item.get("skill", "")))
            return [s for s in result if s]
        return []


def load_and_normalize_file(filepath: Path, source: str, data_type: str) -> ScrapingResult:
    """
    Load a JSON file and normalize its contents.

    Args:
        filepath: Path to JSON file
        source: "phantombuster" or "apify"
        data_type: "profiles" or "posts"

    Returns:
        ScrapingResult with normalized data
    """
    with open(filepath) as f:
        data = json.load(f)

    if not isinstance(data, list):
        data = [data]

    if data_type == "profiles":
        return DataNormalizer.normalize_profiles(data, source)
    elif data_type == "posts":
        return DataNormalizer.normalize_posts(data, source)
    else:
        raise ValueError(f"Unknown data type: {data_type}")


if __name__ == "__main__":
    # Test normalization with sample data
    sample_phantombuster_profile = {
        "name": "John Doe",
        "headline": "Software Engineer at TechCorp",
        "profileUrl": "https://www.linkedin.com/in/johndoe",
        "location": "San Francisco, CA",
        "connectionCount": "500+",
        "company": "TechCorp",
        "jobTitle": "Software Engineer"
    }

    sample_apify_profile = {
        "fullName": "Jane Smith",
        "headline": "Product Manager | Building Products",
        "url": "https://www.linkedin.com/in/janesmith",
        "locationName": "New York, NY",
        "connectionsCount": 1200,
        "currentCompany": "StartupXYZ"
    }

    # Normalize
    pb_profile = DataNormalizer.normalize_phantombuster_profile(sample_phantombuster_profile)
    ap_profile = DataNormalizer.normalize_apify_profile(sample_apify_profile)

    print("Phantombuster profile:")
    print(f"  {pb_profile.name} - {pb_profile.headline}")
    print(f"  Company: {pb_profile.company}")

    print("\nApify profile:")
    print(f"  {ap_profile.name} - {ap_profile.headline}")
    print(f"  Company: {ap_profile.company}")
