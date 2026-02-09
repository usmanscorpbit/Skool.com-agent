"""
LinkedIn Official API Authentication
OAuth 2.0 authentication for LinkedIn Marketing API
"""

import os
import json
import webbrowser
from pathlib import Path
from typing import Optional, Dict
from datetime import datetime, timedelta
from urllib.parse import urlencode, parse_qs, urlparse
import httpx
from dotenv import load_dotenv

# Load approach-specific env
APPROACH_DIR = Path(__file__).parent.parent
BASE_DIR = APPROACH_DIR.parent.parent
ENV_FILE = APPROACH_DIR / ".env.approach1"

if ENV_FILE.exists():
    load_dotenv(ENV_FILE)
else:
    load_dotenv(BASE_DIR / ".env")

TOKEN_FILE = BASE_DIR / ".tmp" / "approach1" / "linkedin_token.json"
TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)


class LinkedInOAuth:
    """
    Handles LinkedIn OAuth 2.0 authentication.

    Required scopes for different features:
    - r_liteprofile: Basic profile info
    - r_emailaddress: Email address
    - w_member_social: Post content
    - r_organization_social: Read org posts
    - w_organization_social: Post as organization
    """

    AUTH_URL = "https://www.linkedin.com/oauth/v2/authorization"
    TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"
    API_BASE = "https://api.linkedin.com/v2"

    # Default scopes for personal posting
    DEFAULT_SCOPES = ["openid", "profile", "w_member_social"]

    def __init__(
        self,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        redirect_uri: str = "http://localhost:8080/callback"
    ):
        """
        Initialize LinkedIn OAuth client.

        Args:
            client_id: LinkedIn app client ID
            client_secret: LinkedIn app client secret
            redirect_uri: OAuth redirect URI
        """
        self.client_id = client_id or os.getenv("LINKEDIN_CLIENT_ID")
        self.client_secret = client_secret or os.getenv("LINKEDIN_CLIENT_SECRET")
        self.redirect_uri = redirect_uri

        if not self.client_id or not self.client_secret:
            raise ValueError(
                "LINKEDIN_CLIENT_ID and LINKEDIN_CLIENT_SECRET are required. "
                "Create a LinkedIn app at https://www.linkedin.com/developers/"
            )

        self._access_token = None
        self._token_expiry = None
        self._load_token()

    def _load_token(self):
        """Load saved token if exists and valid"""
        if TOKEN_FILE.exists():
            try:
                with open(TOKEN_FILE) as f:
                    data = json.load(f)
                    expiry = datetime.fromisoformat(data["expiry"])
                    if expiry > datetime.now():
                        self._access_token = data["access_token"]
                        self._token_expiry = expiry
                        print("Loaded existing access token")
            except Exception as e:
                print(f"Could not load token: {e}")

    def _save_token(self, access_token: str, expires_in: int):
        """Save token to file"""
        expiry = datetime.now() + timedelta(seconds=expires_in - 300)  # 5 min buffer
        data = {
            "access_token": access_token,
            "expiry": expiry.isoformat(),
            "saved_at": datetime.now().isoformat()
        }
        with open(TOKEN_FILE, "w") as f:
            json.dump(data, f, indent=2)
        self._access_token = access_token
        self._token_expiry = expiry

    def get_authorization_url(self, scopes: list = None, state: str = "random_state") -> str:
        """
        Get the authorization URL for user to grant access.

        Args:
            scopes: OAuth scopes to request
            state: State parameter for CSRF protection

        Returns:
            Authorization URL
        """
        scopes = scopes or self.DEFAULT_SCOPES

        params = {
            "response_type": "code",
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "state": state,
            "scope": " ".join(scopes)
        }

        return f"{self.AUTH_URL}?{urlencode(params)}"

    def exchange_code_for_token(self, authorization_code: str) -> Dict:
        """
        Exchange authorization code for access token.

        Args:
            authorization_code: Code from OAuth callback

        Returns:
            Token response
        """
        data = {
            "grant_type": "authorization_code",
            "code": authorization_code,
            "redirect_uri": self.redirect_uri,
            "client_id": self.client_id,
            "client_secret": self.client_secret
        }

        with httpx.Client() as client:
            response = client.post(
                self.TOKEN_URL,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            response.raise_for_status()
            token_data = response.json()

        self._save_token(
            token_data["access_token"],
            token_data.get("expires_in", 5184000)  # Default 60 days
        )

        return token_data

    def start_auth_flow(self, scopes: list = None):
        """
        Start interactive OAuth flow.

        Opens browser for user authorization.
        """
        auth_url = self.get_authorization_url(scopes)

        print("\n=== LinkedIn OAuth Flow ===")
        print("Opening browser for authorization...")
        print(f"\nIf browser doesn't open, visit:\n{auth_url}\n")

        webbrowser.open(auth_url)

        print("After authorizing, you'll be redirected to a URL like:")
        print("http://localhost:8080/callback?code=XXXXX&state=random_state")
        print("\nPaste the FULL redirect URL here:")

        redirect_url = input("> ").strip()

        # Parse the authorization code from URL
        parsed = urlparse(redirect_url)
        params = parse_qs(parsed.query)

        if "code" not in params:
            raise ValueError("No authorization code found in URL")

        code = params["code"][0]
        token_data = self.exchange_code_for_token(code)

        print(f"\nSuccess! Token saved to {TOKEN_FILE}")
        print(f"Token expires in {token_data.get('expires_in', 'unknown')} seconds")

        return token_data

    @property
    def access_token(self) -> Optional[str]:
        """Get current access token, or None if expired"""
        if self._access_token and self._token_expiry:
            if self._token_expiry > datetime.now():
                return self._access_token
        return None

    @property
    def is_authenticated(self) -> bool:
        """Check if we have a valid access token"""
        return self.access_token is not None

    def get_headers(self) -> Dict:
        """Get headers for API requests"""
        if not self.access_token:
            raise ValueError("No valid access token. Run start_auth_flow() first.")

        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "X-Restli-Protocol-Version": "2.0.0"
        }

    def get_user_info(self) -> Dict:
        """
        Get current user's basic info.

        Returns:
            User profile data
        """
        with httpx.Client() as client:
            response = client.get(
                f"{self.API_BASE}/userinfo",
                headers=self.get_headers()
            )
            response.raise_for_status()
            return response.json()

    def get_member_urn(self) -> str:
        """
        Get current user's member URN for posting.

        Returns:
            URN like "urn:li:person:ABC123"
        """
        user_info = self.get_user_info()
        return f"urn:li:person:{user_info['sub']}"


def get_authenticated_client() -> LinkedInOAuth:
    """
    Get authenticated LinkedIn OAuth client.

    Returns:
        Authenticated LinkedInOAuth instance
    """
    client = LinkedInOAuth()

    if not client.is_authenticated:
        print("No valid token found. Starting authentication flow...")
        client.start_auth_flow()

    return client


def clear_token():
    """Clear saved token (force re-authentication)"""
    if TOKEN_FILE.exists():
        TOKEN_FILE.unlink()
        print("Token cleared")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "clear":
        clear_token()
    else:
        try:
            client = get_authenticated_client()
            user = client.get_user_info()
            print(f"\nAuthenticated as: {user.get('name', 'Unknown')}")
            print(f"Email: {user.get('email', 'Not available')}")
            print(f"Member URN: {client.get_member_urn()}")
        except Exception as e:
            print(f"Error: {e}")
            print("\nMake sure you have:")
            print("1. Created a LinkedIn app at https://www.linkedin.com/developers/")
            print("2. Set LINKEDIN_CLIENT_ID and LINKEDIN_CLIENT_SECRET in .env.approach1")
            print("3. Added http://localhost:8080/callback as a redirect URI in your app")
