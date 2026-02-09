"""
Shared data types for LinkedIn automation
Consistent data structures across all three approaches
"""

from dataclasses import dataclass, field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class ApproachType(Enum):
    OFFICIAL_API = "approach1"
    PLAYWRIGHT = "approach2"
    THIRDPARTY = "approach3"


class ConnectionDegree(Enum):
    FIRST = 1
    SECOND = 2
    THIRD = 3
    OUT_OF_NETWORK = 0


@dataclass
class LinkedInProfile:
    """Represents a LinkedIn user profile"""
    id: str
    name: str
    headline: str
    profile_url: str

    # Optional fields
    location: Optional[str] = None
    about: Optional[str] = None
    company: Optional[str] = None
    title: Optional[str] = None
    industry: Optional[str] = None
    followers: Optional[int] = None
    connections: Optional[int] = None
    connection_degree: ConnectionDegree = ConnectionDegree.OUT_OF_NETWORK

    # Experience and skills
    experience: List[dict] = field(default_factory=list)
    skills: List[str] = field(default_factory=list)

    # Metadata
    source_approach: ApproachType = ApproachType.PLAYWRIGHT
    scraped_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "headline": self.headline,
            "profile_url": self.profile_url,
            "location": self.location,
            "about": self.about,
            "company": self.company,
            "title": self.title,
            "industry": self.industry,
            "followers": self.followers,
            "connections": self.connections,
            "connection_degree": self.connection_degree.value,
            "experience": self.experience,
            "skills": self.skills,
            "source_approach": self.source_approach.value,
            "scraped_at": self.scraped_at.isoformat()
        }

    @classmethod
    def from_dict(cls, data: dict) -> "LinkedInProfile":
        data = data.copy()
        if "connection_degree" in data:
            data["connection_degree"] = ConnectionDegree(data["connection_degree"])
        if "source_approach" in data:
            data["source_approach"] = ApproachType(data["source_approach"])
        if "scraped_at" in data and isinstance(data["scraped_at"], str):
            data["scraped_at"] = datetime.fromisoformat(data["scraped_at"])
        return cls(**data)


@dataclass
class LinkedInPost:
    """Represents a LinkedIn post"""
    id: str
    author_name: str
    author_profile_url: str
    content: str
    post_url: str

    # Engagement metrics
    likes: int = 0
    comments: int = 0
    shares: int = 0

    # Post metadata
    posted_at: Optional[datetime] = None
    posted_relative: Optional[str] = None  # "2h", "3d", etc.
    hashtags: List[str] = field(default_factory=list)
    media_urls: List[str] = field(default_factory=list)

    # Author info (if available)
    author_headline: Optional[str] = None
    author_id: Optional[str] = None

    # Metadata
    source_approach: ApproachType = ApproachType.PLAYWRIGHT
    scraped_at: datetime = field(default_factory=datetime.now)

    @property
    def total_engagement(self) -> int:
        return self.likes + self.comments + self.shares

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "author_name": self.author_name,
            "author_profile_url": self.author_profile_url,
            "author_headline": self.author_headline,
            "author_id": self.author_id,
            "content": self.content,
            "post_url": self.post_url,
            "likes": self.likes,
            "comments": self.comments,
            "shares": self.shares,
            "total_engagement": self.total_engagement,
            "posted_at": self.posted_at.isoformat() if self.posted_at else None,
            "posted_relative": self.posted_relative,
            "hashtags": self.hashtags,
            "media_urls": self.media_urls,
            "source_approach": self.source_approach.value,
            "scraped_at": self.scraped_at.isoformat()
        }


@dataclass
class CommentOpportunity:
    """A post identified as a good opportunity for commenting"""
    post: LinkedInPost
    score: float  # 0.0 to 1.0
    reasons: List[str] = field(default_factory=list)
    suggested_angle: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "post": self.post.to_dict(),
            "score": self.score,
            "reasons": self.reasons,
            "suggested_angle": self.suggested_angle
        }


@dataclass
class ContentDraft:
    """Generated content ready to post"""
    body: str
    content_type: str  # "post", "comment", "message"

    # Optional fields
    title: Optional[str] = None
    hashtags: List[str] = field(default_factory=list)
    media_urls: List[str] = field(default_factory=list)
    call_to_action: Optional[str] = None

    # For messages
    recipient_profile: Optional[LinkedInProfile] = None
    personalization_points: List[str] = field(default_factory=list)

    # For comments
    target_post: Optional[LinkedInPost] = None

    # Metadata
    generated_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        return {
            "body": self.body,
            "content_type": self.content_type,
            "title": self.title,
            "hashtags": self.hashtags,
            "media_urls": self.media_urls,
            "call_to_action": self.call_to_action,
            "personalization_points": self.personalization_points,
            "generated_at": self.generated_at.isoformat()
        }


@dataclass
class MessageThread:
    """Represents a message conversation"""
    thread_id: str
    participant: LinkedInProfile
    messages: List[dict] = field(default_factory=list)
    last_message_at: Optional[datetime] = None
    is_connection: bool = False


@dataclass
class ScrapingResult:
    """Result from any scraping operation"""
    success: bool
    approach: ApproachType
    profiles: List[LinkedInProfile] = field(default_factory=list)
    posts: List[LinkedInPost] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "approach": self.approach.value,
            "profiles_count": len(self.profiles),
            "posts_count": len(self.posts),
            "errors": self.errors,
            "metadata": self.metadata
        }
