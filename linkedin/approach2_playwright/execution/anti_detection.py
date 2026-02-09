"""
Anti-Detection Utilities for LinkedIn Browser Automation
Human-like behavior patterns to avoid detection
"""

import random
import time
from typing import Tuple, Optional
import numpy as np
from fake_useragent import UserAgent


class AntiDetection:
    """
    Utilities for making browser automation appear more human-like.
    """

    def __init__(
        self,
        min_delay: float = 1.0,
        max_delay: float = 3.0,
        typing_speed: float = 0.05
    ):
        """
        Initialize anti-detection settings.

        Args:
            min_delay: Minimum delay between actions (seconds)
            max_delay: Maximum delay between actions (seconds)
            typing_speed: Base delay between keystrokes (seconds)
        """
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.typing_speed = typing_speed
        self._ua = None
        self._action_count = 0
        self._session_start = time.time()

    @property
    def user_agent(self) -> str:
        """Get a random desktop user agent"""
        if self._ua is None:
            try:
                self._ua = UserAgent()
            except Exception:
                # Fallback user agent
                return "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        return self._ua.chrome

    def human_delay(self, base_delay: Optional[float] = None) -> float:
        """
        Generate a human-like delay using gaussian distribution.

        Args:
            base_delay: Center of the delay distribution (uses class defaults if None)

        Returns:
            Delay in seconds
        """
        if base_delay is None:
            base_delay = (self.min_delay + self.max_delay) / 2

        # Gaussian distribution centered on base_delay
        delay = np.random.normal(base_delay, base_delay * 0.3)

        # Clamp to reasonable bounds
        delay = max(self.min_delay * 0.5, min(delay, self.max_delay * 2))

        return delay

    def wait(self, base_delay: Optional[float] = None):
        """Sleep for a human-like duration"""
        time.sleep(self.human_delay(base_delay))
        self._action_count += 1

    def short_wait(self):
        """Short delay (0.5-1.5 seconds)"""
        time.sleep(self.human_delay(1.0))

    def medium_wait(self):
        """Medium delay (2-4 seconds)"""
        time.sleep(self.human_delay(3.0))

    def long_wait(self):
        """Long delay (5-10 seconds)"""
        time.sleep(self.human_delay(7.5))

    def random_scroll_pause(self):
        """Pause like a human reading content"""
        # Occasionally take longer pauses (reading)
        if random.random() < 0.2:
            time.sleep(self.human_delay(8.0))
        else:
            time.sleep(self.human_delay(2.0))

    def type_like_human(self, page, selector: str, text: str):
        """
        Type text with human-like delays between keystrokes.

        Args:
            page: Playwright page object
            selector: Element selector to type into
            text: Text to type
        """
        element = page.locator(selector)
        element.click()
        self.short_wait()

        for char in text:
            element.type(char, delay=self._keystroke_delay())

    def _keystroke_delay(self) -> int:
        """Get delay between keystrokes in milliseconds"""
        # Gaussian distribution around typing speed
        delay = np.random.normal(self.typing_speed, self.typing_speed * 0.4)
        delay = max(0.02, min(delay, 0.2))
        return int(delay * 1000)

    def random_mouse_movement(self, page) -> None:
        """
        Simulate random mouse movement on page.

        Args:
            page: Playwright page object
        """
        viewport = page.viewport_size
        if not viewport:
            return

        # Generate random points to move through
        for _ in range(random.randint(1, 3)):
            x = random.randint(100, viewport["width"] - 100)
            y = random.randint(100, viewport["height"] - 100)
            page.mouse.move(x, y)
            time.sleep(self.human_delay(0.3))

    def scroll_naturally(self, page, direction: str = "down", distance: int = None):
        """
        Scroll with human-like behavior.

        Args:
            page: Playwright page object
            direction: "down" or "up"
            distance: Pixels to scroll (random if None)
        """
        if distance is None:
            distance = random.randint(200, 600)

        if direction == "up":
            distance = -distance

        # Scroll in chunks with small pauses
        chunks = random.randint(2, 4)
        chunk_distance = distance // chunks

        for _ in range(chunks):
            page.mouse.wheel(0, chunk_distance)
            time.sleep(self.human_delay(0.2))

    def get_viewport_size(self) -> Tuple[int, int]:
        """Get randomized viewport size"""
        widths = [1366, 1440, 1536, 1920, 2560]
        heights = [768, 900, 864, 1080, 1440]

        idx = random.randint(0, len(widths) - 1)
        # Add slight randomization
        width = widths[idx] + random.randint(-20, 20)
        height = heights[idx] + random.randint(-20, 20)

        return width, height

    def should_take_break(self) -> bool:
        """
        Determine if we should take a longer break.

        Returns:
            True if a break is recommended
        """
        # Take break after many actions
        if self._action_count > 50:
            self._action_count = 0
            return True

        # Random chance of break
        if random.random() < 0.02:  # 2% chance
            return True

        return False

    def break_duration(self) -> float:
        """Get duration for a break (30-120 seconds)"""
        return self.human_delay(60.0)

    def session_duration(self) -> float:
        """Get how long the session has been running"""
        return time.time() - self._session_start

    def is_session_too_long(self, max_minutes: int = 30) -> bool:
        """Check if session has been running too long"""
        return self.session_duration() > (max_minutes * 60)

    def get_browser_args(self) -> list:
        """Get browser launch arguments for stealth"""
        return [
            "--disable-blink-features=AutomationControlled",
            "--disable-features=IsolateOrigins,site-per-process",
            "--disable-infobars",
            "--disable-background-networking",
            "--disable-background-timer-throttling",
            "--disable-backgrounding-occluded-windows",
            "--disable-breakpad",
            "--disable-component-extensions-with-background-pages",
            "--disable-component-update",
            "--disable-default-apps",
            "--disable-dev-shm-usage",
            "--disable-extensions",
            "--disable-features=TranslateUI",
            "--disable-hang-monitor",
            "--disable-ipc-flooding-protection",
            "--disable-popup-blocking",
            "--disable-prompt-on-repost",
            "--disable-renderer-backgrounding",
            "--disable-sync",
            "--enable-features=NetworkService,NetworkServiceInProcess",
            "--force-color-profile=srgb",
            "--metrics-recording-only",
            "--no-first-run",
            "--password-store=basic",
            "--use-mock-keychain",
        ]


class RateLimiter:
    """
    Rate limiting for LinkedIn actions.
    """

    def __init__(
        self,
        actions_per_hour: int = 20,
        profiles_per_session: int = 50,
        messages_per_day: int = 25,
        comments_per_day: int = 30
    ):
        self.actions_per_hour = actions_per_hour
        self.profiles_per_session = profiles_per_session
        self.messages_per_day = messages_per_day
        self.comments_per_day = comments_per_day

        self._action_timestamps = []
        self._profile_count = 0
        self._message_count = 0
        self._comment_count = 0
        self._daily_reset = time.time()

    def can_perform_action(self) -> bool:
        """Check if we can perform another action"""
        self._cleanup_old_actions()
        return len(self._action_timestamps) < self.actions_per_hour

    def can_scrape_profile(self) -> bool:
        """Check if we can scrape another profile"""
        return self._profile_count < self.profiles_per_session

    def can_send_message(self) -> bool:
        """Check if we can send another message"""
        self._check_daily_reset()
        return self._message_count < self.messages_per_day

    def can_post_comment(self) -> bool:
        """Check if we can post another comment"""
        self._check_daily_reset()
        return self._comment_count < self.comments_per_day

    def record_action(self):
        """Record that an action was performed"""
        self._action_timestamps.append(time.time())

    def record_profile_scrape(self):
        """Record that a profile was scraped"""
        self._profile_count += 1
        self.record_action()

    def record_message(self):
        """Record that a message was sent"""
        self._message_count += 1
        self.record_action()

    def record_comment(self):
        """Record that a comment was posted"""
        self._comment_count += 1
        self.record_action()

    def time_until_next_action(self) -> float:
        """Get seconds until we can perform another action"""
        if self.can_perform_action():
            return 0

        self._cleanup_old_actions()
        if self._action_timestamps:
            oldest = min(self._action_timestamps)
            return (oldest + 3600) - time.time()
        return 0

    def _cleanup_old_actions(self):
        """Remove actions older than 1 hour"""
        cutoff = time.time() - 3600
        self._action_timestamps = [t for t in self._action_timestamps if t > cutoff]

    def _check_daily_reset(self):
        """Reset daily counters if 24 hours have passed"""
        if time.time() - self._daily_reset > 86400:
            self._message_count = 0
            self._comment_count = 0
            self._daily_reset = time.time()

    def get_status(self) -> dict:
        """Get current rate limit status"""
        self._cleanup_old_actions()
        self._check_daily_reset()
        return {
            "actions_this_hour": len(self._action_timestamps),
            "actions_limit": self.actions_per_hour,
            "profiles_this_session": self._profile_count,
            "profiles_limit": self.profiles_per_session,
            "messages_today": self._message_count,
            "messages_limit": self.messages_per_day,
            "comments_today": self._comment_count,
            "comments_limit": self.comments_per_day,
            "can_act": self.can_perform_action(),
            "can_scrape": self.can_scrape_profile(),
            "can_message": self.can_send_message(),
            "can_comment": self.can_post_comment()
        }
