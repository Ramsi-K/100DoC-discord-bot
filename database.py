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
                completed_at TEXT DEFAULT NULL
            )
        """
        )
        conn.commit()
        conn.close()

    def get_user_data(self, user_id: int) -> Optional[Dict]:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT user_id, username, current_day, last_post_timestamp, \
                   is_active, created_at, completed_at
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
                (user_id, username, current_day, last_post_timestamp, created_at)
                VALUES (?, ?, 1, ?, ?)
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
            SELECT user_id, username, current_day, last_post_timestamp
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
                (user_id, username, current_day, last_post_timestamp, created_at, completed_at)
                VALUES (?, ?, ?, ?, ?, ?)
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
