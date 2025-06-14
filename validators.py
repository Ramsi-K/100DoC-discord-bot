# validators.py: StreakValidator class
import re
import datetime
from typing import Optional, Tuple


class StreakValidator:
    """Validates streak posts and progression"""

    @staticmethod
    def parse_log_message(content: str) -> Optional[int]:
        pattern = r"^\[(\d+)/100\]"
        match = re.match(pattern, content.strip())
        if match:
            day = int(match.group(1))
            if 1 <= day <= 100:
                return day
        return None

    @staticmethod
    def is_valid_progression(
        current_day: int, new_day: int, is_new_user: bool
    ) -> Tuple[bool, str]:
        if is_new_user:
            if new_day == 1:
                return True, "Welcome to the 100 Days of Code challenge!"
            else:
                return False, "New participants must start with [1/100]"
        if new_day == current_day + 1:
            return True, f"Great progress! Day {new_day} logged successfully."
        elif new_day <= current_day:
            return (
                False,
                f"You've already completed day {current_day}. Next post should be [{current_day + 1}/100]",
            )
        else:
            return (
                False,
                f"You can't skip ahead! You're on day {current_day}, next should be [{current_day + 1}/100]",
            )

    @staticmethod
    def check_time_constraint(
        last_post_time: datetime.datetime,
    ) -> Tuple[bool, str]:
        now_utc = datetime.datetime.now(datetime.timezone.utc).date()
        last_post_day = last_post_time.date()
        if now_utc > last_post_day:
            return True, ""
        else:
            return (
                False,
                "⏰ You've already posted today. Please come back after 00:00 UTC [<t:1749859200:t>] for your next update!",
            )
