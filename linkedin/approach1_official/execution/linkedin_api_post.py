"""
LinkedIn API Posting
Create posts via official LinkedIn API
"""

import os
import json
from pathlib import Path
from typing import Optional, List, Dict
from datetime import datetime
import httpx
from dotenv import load_dotenv

from .linkedin_api_auth import get_authenticated_client, LinkedInOAuth

# Load approach-specific env
APPROACH_DIR = Path(__file__).parent.parent
BASE_DIR = APPROACH_DIR.parent.parent
ENV_FILE = APPROACH_DIR / ".env.approach1"

if ENV_FILE.exists():
    load_dotenv(ENV_FILE)
else:
    load_dotenv(BASE_DIR / ".env")

OUTPUT_DIR = BASE_DIR / ".tmp" / "approach1"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


class LinkedInPoster:
    """
    Posts content via LinkedIn API.

    Uses the UGC (User Generated Content) API for creating posts.
    """

    API_BASE = "https://api.linkedin.com/v2"

    def __init__(self, auth_client: Optional[LinkedInOAuth] = None):
        """
        Initialize poster with auth client.

        Args:
            auth_client: Authenticated LinkedInOAuth client
        """
        self.auth = auth_client or get_authenticated_client()
        self._member_urn = None

    @property
    def member_urn(self) -> str:
        """Get member URN (cached)"""
        if not self._member_urn:
            self._member_urn = self.auth.get_member_urn()
        return self._member_urn

    def create_text_post(
        self,
        text: str,
        visibility: str = "PUBLIC"
    ) -> Dict:
        """
        Create a text-only post.

        Args:
            text: Post content
            visibility: "PUBLIC", "CONNECTIONS", or "LOGGED_IN"

        Returns:
            API response with post ID
        """
        # Build UGC post payload
        payload = {
            "author": self.member_urn,
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {
                        "text": text
                    },
                    "shareMediaCategory": "NONE"
                }
            },
            "visibility": {
                "com.linkedin.ugc.MemberNetworkVisibility": visibility
            }
        }

        with httpx.Client() as client:
            response = client.post(
                f"{self.API_BASE}/ugcPosts",
                headers=self.auth.get_headers(),
                json=payload
            )

            if response.status_code == 201:
                result = {
                    "success": True,
                    "post_id": response.headers.get("x-restli-id"),
                    "posted_at": datetime.now().isoformat()
                }
            else:
                result = {
                    "success": False,
                    "error": response.text,
                    "status_code": response.status_code
                }

        # Log the result
        self._log_post(text, result)

        return result

    def create_article_post(
        self,
        text: str,
        article_url: str,
        title: Optional[str] = None,
        description: Optional[str] = None,
        visibility: str = "PUBLIC"
    ) -> Dict:
        """
        Create a post with an article/link.

        Args:
            text: Post commentary
            article_url: URL to share
            title: Article title (optional, LinkedIn will scrape)
            description: Article description (optional)
            visibility: Visibility setting

        Returns:
            API response
        """
        media = {
            "status": "READY",
            "originalUrl": article_url
        }

        if title:
            media["title"] = {"text": title}
        if description:
            media["description"] = {"text": description}

        payload = {
            "author": self.member_urn,
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {
                        "text": text
                    },
                    "shareMediaCategory": "ARTICLE",
                    "media": [media]
                }
            },
            "visibility": {
                "com.linkedin.ugc.MemberNetworkVisibility": visibility
            }
        }

        with httpx.Client() as client:
            response = client.post(
                f"{self.API_BASE}/ugcPosts",
                headers=self.auth.get_headers(),
                json=payload
            )

            if response.status_code == 201:
                result = {
                    "success": True,
                    "post_id": response.headers.get("x-restli-id"),
                    "posted_at": datetime.now().isoformat()
                }
            else:
                result = {
                    "success": False,
                    "error": response.text,
                    "status_code": response.status_code
                }

        self._log_post(text, result)
        return result

    def create_image_post(
        self,
        text: str,
        image_path: str,
        visibility: str = "PUBLIC"
    ) -> Dict:
        """
        Create a post with an image.

        Args:
            text: Post commentary
            image_path: Path to local image file
            visibility: Visibility setting

        Returns:
            API response
        """
        # Step 1: Register upload
        register_payload = {
            "registerUploadRequest": {
                "recipes": ["urn:li:digitalmediaRecipe:feedshare-image"],
                "owner": self.member_urn,
                "serviceRelationships": [{
                    "relationshipType": "OWNER",
                    "identifier": "urn:li:userGeneratedContent"
                }]
            }
        }

        with httpx.Client() as client:
            # Register the upload
            response = client.post(
                f"{self.API_BASE}/assets?action=registerUpload",
                headers=self.auth.get_headers(),
                json=register_payload
            )

            if response.status_code != 200:
                return {
                    "success": False,
                    "error": f"Failed to register upload: {response.text}",
                    "status_code": response.status_code
                }

            register_data = response.json()
            upload_url = register_data["value"]["uploadMechanism"][
                "com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest"
            ]["uploadUrl"]
            asset = register_data["value"]["asset"]

            # Step 2: Upload the image
            with open(image_path, "rb") as f:
                image_data = f.read()

            upload_response = client.put(
                upload_url,
                content=image_data,
                headers={
                    "Authorization": f"Bearer {self.auth.access_token}",
                    "Content-Type": "application/octet-stream"
                }
            )

            if upload_response.status_code not in [200, 201]:
                return {
                    "success": False,
                    "error": f"Failed to upload image: {upload_response.text}",
                    "status_code": upload_response.status_code
                }

            # Step 3: Create the post with uploaded image
            payload = {
                "author": self.member_urn,
                "lifecycleState": "PUBLISHED",
                "specificContent": {
                    "com.linkedin.ugc.ShareContent": {
                        "shareCommentary": {
                            "text": text
                        },
                        "shareMediaCategory": "IMAGE",
                        "media": [{
                            "status": "READY",
                            "media": asset
                        }]
                    }
                },
                "visibility": {
                    "com.linkedin.ugc.MemberNetworkVisibility": visibility
                }
            }

            post_response = client.post(
                f"{self.API_BASE}/ugcPosts",
                headers=self.auth.get_headers(),
                json=payload
            )

            if post_response.status_code == 201:
                result = {
                    "success": True,
                    "post_id": post_response.headers.get("x-restli-id"),
                    "asset": asset,
                    "posted_at": datetime.now().isoformat()
                }
            else:
                result = {
                    "success": False,
                    "error": post_response.text,
                    "status_code": post_response.status_code
                }

        self._log_post(text, result)
        return result

    def delete_post(self, post_urn: str) -> Dict:
        """
        Delete a post.

        Args:
            post_urn: Post URN (from create response)

        Returns:
            Result dict
        """
        with httpx.Client() as client:
            response = client.delete(
                f"{self.API_BASE}/ugcPosts/{post_urn}",
                headers=self.auth.get_headers()
            )

            return {
                "success": response.status_code == 204,
                "status_code": response.status_code
            }

    def _log_post(self, text: str, result: Dict):
        """Log post to file"""
        log_file = OUTPUT_DIR / "api_post_log.json"
        log_entries = []
        if log_file.exists():
            with open(log_file) as f:
                log_entries = json.load(f)

        log_entries.append({
            "text": text[:200],
            "result": result,
            "timestamp": datetime.now().isoformat()
        })

        with open(log_file, "w") as f:
            json.dump(log_entries, f, indent=2)


def create_post(
    text: str,
    article_url: Optional[str] = None,
    image_path: Optional[str] = None,
    visibility: str = "PUBLIC"
) -> Dict:
    """
    Main entry point for creating a post.

    Args:
        text: Post content
        article_url: Optional URL to share
        image_path: Optional image to attach
        visibility: "PUBLIC", "CONNECTIONS", or "LOGGED_IN"

    Returns:
        Result dict
    """
    poster = LinkedInPoster()

    if image_path:
        return poster.create_image_post(text, image_path, visibility)
    elif article_url:
        return poster.create_article_post(text, article_url, visibility=visibility)
    else:
        return poster.create_text_post(text, visibility)


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python linkedin_api_post.py <text> [--url URL] [--image PATH]")
        sys.exit(1)

    text = sys.argv[1]
    url = None
    image = None

    # Parse optional args
    for i, arg in enumerate(sys.argv):
        if arg == "--url" and i + 1 < len(sys.argv):
            url = sys.argv[i + 1]
        if arg == "--image" and i + 1 < len(sys.argv):
            image = sys.argv[i + 1]

    print(f"Creating post: {text[:50]}...")
    print("WARNING: This will create a real post on LinkedIn!")

    confirm = input("Continue? (yes/no): ")
    if confirm.lower() != "yes":
        print("Cancelled")
    else:
        result = create_post(text, article_url=url, image_path=image)
        print(f"Result: {result}")
