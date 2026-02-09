"""
Phantombuster API Client
Interfaces with Phantombuster for LinkedIn automation
https://phantombuster.com/
"""

import os
import json
import time
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime
import httpx
from dotenv import load_dotenv

# Load approach-specific env
APPROACH_DIR = Path(__file__).parent.parent
BASE_DIR = APPROACH_DIR.parent.parent
ENV_FILE = APPROACH_DIR / ".env.approach3"

if ENV_FILE.exists():
    load_dotenv(ENV_FILE)
else:
    load_dotenv(BASE_DIR / ".env")

OUTPUT_DIR = BASE_DIR / ".tmp" / "approach3"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


class PhantombusterClient:
    """
    Client for Phantombuster API.

    Phantombuster provides pre-built "Phantoms" (automation scripts) for LinkedIn:
    - LinkedIn Profile Scraper
    - LinkedIn Network Booster (connection requests)
    - LinkedIn Message Sender
    - LinkedIn Post Commenter
    - LinkedIn Auto Liker
    """

    BASE_URL = "https://api.phantombuster.com/api/v2"

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Phantombuster client.

        Args:
            api_key: Phantombuster API key (or from env PHANTOMBUSTER_API_KEY)
        """
        self.api_key = api_key or os.getenv("PHANTOMBUSTER_API_KEY")
        if not self.api_key:
            raise ValueError("PHANTOMBUSTER_API_KEY is required")

        self.headers = {
            "X-Phantombuster-Key": self.api_key,
            "Content-Type": "application/json"
        }

        # Pre-configured phantom IDs (set in .env.approach3)
        self.phantom_ids = {
            "profile_scraper": os.getenv("PHANTOMBUSTER_PROFILE_SCRAPER_ID"),
            "post_finder": os.getenv("PHANTOMBUSTER_POST_FINDER_ID"),
            "network_booster": os.getenv("PHANTOMBUSTER_NETWORK_BOOSTER_ID"),
            "message_sender": os.getenv("PHANTOMBUSTER_MESSAGE_SENDER_ID"),
            "commenter": os.getenv("PHANTOMBUSTER_COMMENTER_ID"),
        }

    def _request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None,
        params: Optional[Dict] = None
    ) -> Dict:
        """Make API request"""
        url = f"{self.BASE_URL}/{endpoint}"

        with httpx.Client(timeout=60.0) as client:
            if method == "GET":
                response = client.get(url, headers=self.headers, params=params)
            elif method == "POST":
                response = client.post(url, headers=self.headers, json=data)
            else:
                raise ValueError(f"Unsupported method: {method}")

            response.raise_for_status()
            return response.json()

    def get_agents(self) -> List[Dict]:
        """
        List all available Phantoms (agents).

        Returns:
            List of agent configurations
        """
        result = self._request("GET", "agents/fetch-all")
        return result.get("data", [])

    def get_agent(self, agent_id: str) -> Dict:
        """
        Get details of a specific Phantom.

        Args:
            agent_id: Phantom/agent ID

        Returns:
            Agent configuration
        """
        result = self._request("GET", f"agents/fetch", params={"id": agent_id})
        return result

    def launch_agent(
        self,
        agent_id: str,
        arguments: Optional[Dict] = None
    ) -> Dict:
        """
        Launch a Phantom with given arguments.

        Args:
            agent_id: Phantom/agent ID
            arguments: Arguments to pass to the phantom

        Returns:
            Launch result with container ID
        """
        data = {"id": agent_id}
        if arguments:
            data["argument"] = arguments

        result = self._request("POST", "agents/launch", data=data)
        return result

    def get_agent_output(self, agent_id: str) -> Dict:
        """
        Get the output of a Phantom run.

        Args:
            agent_id: Phantom/agent ID

        Returns:
            Output data
        """
        result = self._request("GET", f"agents/fetch-output", params={"id": agent_id})
        return result

    def wait_for_completion(
        self,
        agent_id: str,
        timeout_seconds: int = 300,
        poll_interval: int = 10
    ) -> Dict:
        """
        Wait for a Phantom to complete.

        Args:
            agent_id: Phantom/agent ID
            timeout_seconds: Maximum wait time
            poll_interval: Seconds between status checks

        Returns:
            Final output
        """
        start_time = time.time()

        while time.time() - start_time < timeout_seconds:
            agent = self.get_agent(agent_id)
            status = agent.get("status", "")

            if status in ["finished", "error"]:
                return self.get_agent_output(agent_id)

            print(f"Agent status: {status}, waiting...")
            time.sleep(poll_interval)

        raise TimeoutError(f"Agent {agent_id} did not complete within {timeout_seconds}s")

    # High-level methods for specific Phantoms

    def scrape_profiles(
        self,
        profile_urls: List[str],
        session_cookie: Optional[str] = None
    ) -> Dict:
        """
        Scrape LinkedIn profiles using Profile Scraper phantom.

        Args:
            profile_urls: List of profile URLs to scrape
            session_cookie: LinkedIn session cookie (li_at)

        Returns:
            Scraping results
        """
        phantom_id = self.phantom_ids.get("profile_scraper")
        if not phantom_id:
            raise ValueError("PHANTOMBUSTER_PROFILE_SCRAPER_ID not configured")

        arguments = {
            "spreadsheetUrl": profile_urls,  # Can also be a Google Sheet URL
            "numberOfProfilesToProcess": len(profile_urls),
        }

        if session_cookie:
            arguments["sessionCookie"] = session_cookie

        self.launch_agent(phantom_id, arguments)
        result = self.wait_for_completion(phantom_id)

        # Save results
        output_file = OUTPUT_DIR / "phantombuster_profiles.json"
        with open(output_file, "w") as f:
            json.dump(result, f, indent=2)

        return result

    def send_connection_requests(
        self,
        profile_urls: List[str],
        message_template: Optional[str] = None,
        session_cookie: Optional[str] = None
    ) -> Dict:
        """
        Send connection requests using Network Booster phantom.

        Args:
            profile_urls: Profiles to connect with
            message_template: Connection request message
            session_cookie: LinkedIn session cookie

        Returns:
            Results
        """
        phantom_id = self.phantom_ids.get("network_booster")
        if not phantom_id:
            raise ValueError("PHANTOMBUSTER_NETWORK_BOOSTER_ID not configured")

        arguments = {
            "spreadsheetUrl": profile_urls,
            "numberOfAddsPerLaunch": min(len(profile_urls), 10),
        }

        if message_template:
            arguments["message"] = message_template
        if session_cookie:
            arguments["sessionCookie"] = session_cookie

        self.launch_agent(phantom_id, arguments)
        result = self.wait_for_completion(phantom_id)

        # Save results
        output_file = OUTPUT_DIR / "phantombuster_connections.json"
        with open(output_file, "w") as f:
            json.dump(result, f, indent=2)

        return result

    def send_messages(
        self,
        profile_urls: List[str],
        message_template: str,
        session_cookie: Optional[str] = None
    ) -> Dict:
        """
        Send messages using Message Sender phantom.

        Args:
            profile_urls: Profiles to message
            message_template: Message content
            session_cookie: LinkedIn session cookie

        Returns:
            Results
        """
        phantom_id = self.phantom_ids.get("message_sender")
        if not phantom_id:
            raise ValueError("PHANTOMBUSTER_MESSAGE_SENDER_ID not configured")

        arguments = {
            "spreadsheetUrl": profile_urls,
            "message": message_template,
            "numberOfMessagesPerLaunch": min(len(profile_urls), 10),
        }

        if session_cookie:
            arguments["sessionCookie"] = session_cookie

        self.launch_agent(phantom_id, arguments)
        result = self.wait_for_completion(phantom_id)

        return result

    def post_comments(
        self,
        post_urls: List[str],
        comments: List[str],
        session_cookie: Optional[str] = None
    ) -> Dict:
        """
        Post comments using Commenter phantom.

        Args:
            post_urls: Posts to comment on
            comments: Comments to post (matched by index or cycled)
            session_cookie: LinkedIn session cookie

        Returns:
            Results
        """
        phantom_id = self.phantom_ids.get("commenter")
        if not phantom_id:
            raise ValueError("PHANTOMBUSTER_COMMENTER_ID not configured")

        # Prepare input (post URL + comment pairs)
        input_data = []
        for i, url in enumerate(post_urls):
            comment = comments[i % len(comments)]
            input_data.append({"postUrl": url, "comment": comment})

        arguments = {
            "spreadsheetUrl": input_data,
            "numberOfCommentsPerLaunch": min(len(post_urls), 10),
        }

        if session_cookie:
            arguments["sessionCookie"] = session_cookie

        self.launch_agent(phantom_id, arguments)
        result = self.wait_for_completion(phantom_id)

        return result


def get_client() -> PhantombusterClient:
    """Get configured Phantombuster client"""
    return PhantombusterClient()


if __name__ == "__main__":
    # Test connection and list agents
    try:
        client = get_client()
        agents = client.get_agents()
        print(f"Found {len(agents)} Phantombuster agents:")
        for agent in agents:
            print(f"  - {agent.get('name')}: {agent.get('id')}")
    except Exception as e:
        print(f"Error: {e}")
        print("\nMake sure PHANTOMBUSTER_API_KEY is set in .env.approach3")
