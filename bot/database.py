# database.py: DatabaseManager class
import sqlite3
import datetime
from typing import Dict, List, Optional


class DatabaseManager:
    """Handles all database operations for user streaks"""

    def __init__(self, db_path: str = "streaks.db"):
        self.db_path = db_path
        self.init_database()

    def init_database(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS user_streaks (
                user_id INTEGER PRIMARY KEY,
                username TEXT NOT NULL,
                current_day INTEGER NOT NULL DEFAULT 1,
                last_post_timestamp TEXT NOT NULL,
                is_active BOOLEAN NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                completed_at TEXT DEFAULT NULL,
                reminders_enabled BOOLEAN NOT NULL DEFAULT 1
            )
        """
        )
        # Migration: add reminders_enabled if missing
        cursor.execute("PRAGMA table_info(user_streaks)")
        columns = [row[1] for row in cursor.fetchall()]
        if "reminders_enabled" not in columns:
            cursor.execute(
                "ALTER TABLE user_streaks ADD COLUMN reminders_enabled BOOLEAN NOT NULL DEFAULT 1"
            )
        conn.commit()
        conn.close()

    def get_user_data(self, user_id: int) -> Optional[Dict]:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT user_id, username, current_day, last_post_timestamp, \
                   is_active, created_at, completed_at, reminders_enabled
            FROM user_streaks WHERE user_id = ?
        """,
            (user_id,),
        )
        row = cursor.fetchone()
        conn.close()
        if row:
            return {
                "user_id": row[0],
                "username": row[1],
                "current_day": row[2],
                "last_post_timestamp": datetime.datetime.fromisoformat(row[3]),
                "is_active": bool(row[4]),
                "created_at": datetime.datetime.fromisoformat(row[5]),
                "completed_at": (
                    datetime.datetime.fromisoformat(row[6]) if row[6] else None
                ),
                "reminders_enabled": bool(row[7]),
            }
        return None

    def create_user(self, user_id: int, username: str) -> bool:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            now = datetime.datetime.now(datetime.timezone.utc).isoformat()
            cursor.execute(
                """
                INSERT INTO user_streaks 
                (user_id, username, current_day, last_post_timestamp, created_at, reminders_enabled)
                VALUES (?, ?, 1, ?, ?, 1)
            """,
                (user_id, username, now, now),
            )
            conn.commit()
            conn.close()
            return True
        except sqlite3.IntegrityError:
            conn.close()
            return False

    def update_user_progress(
        self, user_id: int, username: str, new_day: int
    ) -> bool:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        completed_at = now if new_day == 100 else None
        cursor.execute(
            """
            UPDATE user_streaks 
            SET username = ?, current_day = ?, last_post_timestamp = ?, completed_at = ?
            WHERE user_id = ?
        """,
            (username, new_day, now, completed_at, user_id),
        )
        success = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return success

    def get_leaderboard(self, limit: int = 5) -> List[Dict]:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT user_id, username, current_day, last_post_timestamp
            FROM user_streaks 
            WHERE is_active = 1 
            ORDER BY current_day DESC, last_post_timestamp ASC
            LIMIT ?
        """,
            (limit,),
        )
        rows = cursor.fetchall()
        conn.close()
        return [
            {
                "user_id": row[0],
                "username": row[1],
                "current_day": row[2],
                "last_post_timestamp": datetime.datetime.fromisoformat(row[3]),
            }
            for row in rows
        ]

    def get_inactive_users(self, days_threshold: int) -> List[Dict]:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        threshold_date = (
            datetime.datetime.now(datetime.timezone.utc)
            - datetime.timedelta(days=days_threshold)
        ).isoformat()
        cursor.execute(
            """
            SELECT user_id, username, current_day, last_post_timestamp, reminders_enabled
            FROM user_streaks 
            WHERE is_active = 1 AND last_post_timestamp < ?
        """,
            (threshold_date,),
        )
        rows = cursor.fetchall()
        conn.close()
        return [
            {
                "user_id": row[0],
                "username": row[1],
                "current_day": row[2],
                "last_post_timestamp": datetime.datetime.fromisoformat(row[3]),
                "reminders_enabled": bool(row[4]),
            }
            for row in rows
        ]

    def deactivate_user(self, user_id: int) -> bool:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE user_streaks SET is_active = 0 WHERE user_id = ?
        """,
            (user_id,),
        )
        success = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return success

    def reset_user(self, user_id: int) -> bool:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        cursor.execute(
            """
            UPDATE user_streaks 
            SET current_day = 1, last_post_timestamp = ?, completed_at = NULL, is_active = 1
            WHERE user_id = ?
        """,
            (now, user_id),
        )
        success = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return success

    def force_set_day(self, user_id: int, username: str, day: int) -> bool:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        completed_at = now if day == 100 else None
        user_data = self.get_user_data(user_id)
        if not user_data:
            cursor.execute(
                """
                INSERT INTO user_streaks 
                (user_id, username, current_day, last_post_timestamp, created_at, completed_at, reminders_enabled)
                VALUES (?, ?, ?, ?, ?, ?, 1)
            """,
                (user_id, username, day, now, now, completed_at),
            )
        else:
            cursor.execute(
                """
                UPDATE user_streaks 
                SET username = ?, current_day = ?, last_post_timestamp = ?, \
                    completed_at = ?, is_active = 1
                WHERE user_id = ?
            """,
                (username, day, now, completed_at, user_id),
            )
        conn.commit()
        success = cursor.rowcount > 0
        conn.close()
        return success

    def toggle_reminders(self, user_id: int) -> Optional[bool]:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT reminders_enabled FROM user_streaks WHERE user_id = ?",
            (user_id,),
        )
        result = cursor.fetchone()
        if result is None:
            conn.close()
            return None
        new_value = 0 if result[0] else 1
        cursor.execute(
            "UPDATE user_streaks SET reminders_enabled = ? WHERE user_id = ?",
            (new_value, user_id),
        )
        conn.commit()
        conn.close()
        return bool(new_value)

    def set_reminders_enabled(self, user_id: int, enabled: bool) -> bool:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE user_streaks SET reminders_enabled = ? WHERE user_id = ?",
            (1 if enabled else 0, user_id),
        )
        success = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return success
