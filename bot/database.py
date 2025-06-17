# database.py: DatabaseManager class
import sqlite3
import datetime
import os
import logging
from typing import Dict, List, Optional, Tuple

# Try to import modal for volume operations
try:
    import modal
except ImportError:
    pass  # Modal not available in local development


class DatabaseManager:
    """Handles all database operations for user streaks"""

    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = os.environ.get("DB_PATH", "/data/streaks.db")
        self.db_path = db_path
        # Don't automatically initialize the database on creation
        # This allows us to connect to an existing database without recreating it

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
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS hall_of_fame (
                user_id INTEGER PRIMARY KEY,
                username TEXT NOT NULL,
                completed_at TEXT NOT NULL
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS user_repos (
                user_id INTEGER PRIMARY KEY,
                github_repo TEXT NOT NULL
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
        self.commit_to_volume()

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
            self.commit_to_volume()
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
        
        if success:
            self.commit_to_volume()
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
        if success:
            self.commit_to_volume()
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
        if success:
            self.commit_to_volume()
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
        # Get current value
        success, result = self.execute_safely(
            "SELECT reminders_enabled FROM user_streaks WHERE user_id = ?",
            (user_id,),
            'one'
        )
        
        if not success or result is None:
            return None
            
        # Toggle value
        new_value = 0 if result[0] else 1
        success, _ = self.execute_safely(
            "UPDATE user_streaks SET reminders_enabled = ? WHERE user_id = ?",
            (new_value, user_id)
        )
        
        if success:
            self.commit_to_volume()
            return bool(new_value)
        return None

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
        if success:
            self.commit_to_volume()
        return success

    def archive_to_hof(self, user_id: int, username: str) -> None:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        cursor.execute(
            """
            INSERT OR REPLACE INTO hall_of_fame (user_id, username, completed_at)
            VALUES (?, ?, ?)
            """,
            (user_id, username, now),
        )
        cursor.execute(
            "DELETE FROM user_streaks WHERE user_id = ?", (user_id,)
        )
        conn.commit()
        conn.close()
        self.commit_to_volume()

    def set_user_repo(self, user_id: int, github_repo: str) -> None:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO user_repos (user_id, github_repo) VALUES (?, ?)",
            (user_id, github_repo),
        )
        conn.commit()
        conn.close()
        self.commit_to_volume()

    def get_user_repo(self, user_id: int) -> Optional[str]:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT github_repo FROM user_repos WHERE user_id = ?",
            (user_id,),
        )
        row = cursor.fetchone()
        conn.close()
        if row:
            return row[0]
        return None

    def get_connection(self):
        """Get a database connection with timeout to prevent hanging"""
        return sqlite3.connect(self.db_path, timeout=10)
    
    def execute_safely(self, operation, params=None, fetch_type=None) -> Tuple[bool, any]:
        """Execute a database operation safely with proper error handling
        
        Args:
            operation: SQL statement to execute
            params: Parameters for the SQL statement
            fetch_type: None for no fetch, 'one' for fetchone, 'all' for fetchall
            
        Returns:
            Tuple of (success, result)
        """
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            if params:
                cursor.execute(operation, params)
            else:
                cursor.execute(operation)
                
            result = None
            if fetch_type == 'one':
                result = cursor.fetchone()
            elif fetch_type == 'all':
                result = cursor.fetchall()
            else:
                result = cursor.rowcount
                
            conn.commit()
            return True, result
        except sqlite3.Error as e:
            logging.error(f"Database error: {e}")
            return False, None
        finally:
            if conn:
                conn.close()
        
    def commit_to_volume(self):
        """Commit changes to the Modal volume if available"""
        try:
            if 'modal' in globals():
                modal.Volume.from_name("discord-bot-db").commit()
        except Exception as e:
            logging.error(f"Failed to commit to volume: {e}")
            # Continue operation even if volume commit fails
            # This ensures the bot keeps working with local DB
