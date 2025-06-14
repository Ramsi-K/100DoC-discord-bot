import discord
from discord.ext import commands, tasks
import json
import sqlite3
import re
import datetime

# from datetime import datetime, timedelta, timezone
import asyncio
from typing import Dict, List, Optional, Tuple
import logging
import os
from dotenv import load_dotenv


# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()
print("ENV loaded")
print("TOKEN =", os.getenv("DISCORD_BOT_TOKEN"))

TOKEN = os.getenv("DISCORD_BOT_TOKEN")


class ChannelConfig:
    """Channel configuration for feature control"""

    LOGGING_CHANNEL = "100-days-log"
    ALLOWED_COMMAND_CHANNELS = ["bot-commands", "general", "admin"]

    @classmethod
    def is_logging_channel(cls, channel_name: str) -> bool:
        return channel_name == cls.LOGGING_CHANNEL

    @classmethod
    def is_command_allowed(cls, channel_name: str) -> bool:
        return (
            channel_name in cls.ALLOWED_COMMAND_CHANNELS
            or channel_name == cls.LOGGING_CHANNEL
        )


class DatabaseManager:
    """Handles all database operations for user streaks"""

    def __init__(self, db_path: str = "streaks.db"):
        self.db_path = db_path
        self.init_database()

    def init_database(self):
        """Initialize the SQLite database"""
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
        """Get user streak data"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT user_id, username, current_day, last_post_timestamp, 
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
        """Create a new user entry"""
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
        """Update user's progress"""
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
        """Get top active users by current day"""
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
        """Get users who haven't posted in X days"""
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
        """Deactivate a user (remove from tracking)"""
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
        """Reset user's streak to day 1"""
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
        """Force set a user's day (admin function)"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        completed_at = now if day == 100 else None

        # Check if user exists
        user_data = self.get_user_data(user_id)
        if not user_data:
            # Create user first
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
                SET username = ?, current_day = ?, last_post_timestamp = ?, 
                    completed_at = ?, is_active = 1
                WHERE user_id = ?
            """,
                (username, day, now, completed_at, user_id),
            )

        conn.commit()
        success = cursor.rowcount > 0
        conn.close()
        return success


class StreakValidator:
    """Validates streak posts and progression"""

    @staticmethod
    def parse_log_message(content: str) -> Optional[int]:
        """Parse [x/100] format and return day number"""
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
        """Check if the day progression is valid"""
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
        """Check if enough time has passed since last post"""
        now = datetime.datetime.now(datetime.timezone.utc)

        now_utc = datetime.datetime.now(datetime.timezone.utc).date()
        last_post_day = last_post_time.date()

        if now_utc > last_post_day:
            return True, ""
        else:
            return (
                False,
                "⏰ You've already posted today. Please come back after 00:00 UTC [<t:1749859200:t>] for your next update!",
            )

        # time_diff = now - last_post_time

        # if time_diff >= datetime.timedelta(hours=24):
        #     return True, ""

        # remaining = datetime.timedelta(hours=24) - time_diff
        # hours = remaining.seconds // 3600
        # minutes = (remaining.seconds % 3600) // 60

        # return (
        #     False,
        #     f"Please wait {hours}h {minutes}m before your next post (24-hour cooldown)",
        # )


class HundredDoCBot(commands.Bot):
    """Main bot class for 100 Days of Code tracking"""

    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True

        super().__init__(command_prefix="!", intents=intents)

        self.db = DatabaseManager()
        self.validator = StreakValidator()

        # Remove default help command to create custom one
        self.remove_command("help")

    async def on_ready(self):
        """Called when bot is ready"""
        logger.info(f"{self.user} has connected to Discord!")

        # Start reminder task
        if not self.daily_reminder_check.is_running():
            self.daily_reminder_check.start()

    async def on_message(self, message):
        """Handle incoming messages"""
        # Ignore bot messages
        if message.author.bot:
            return

        # Check if message is in logging channel
        if ChannelConfig.is_logging_channel(message.channel.name):
            await self.handle_log_message(message)

        # Process commands
        await self.process_commands(message)

    async def handle_log_message(self, message):
        """Handle messages in the logging channel"""
        day_number = self.validator.parse_log_message(message.content)

        if day_number is None:
            return  # Ignore non-log messages

        user_id = message.author.id
        username = str(message.author)

        # Get existing user data
        user_data = self.db.get_user_data(user_id)
        is_new_user = user_data is None

        # Validate progression
        current_day = 0 if is_new_user else user_data["current_day"]
        is_valid, validation_msg = self.validator.is_valid_progression(
            current_day, day_number, is_new_user
        )

        if not is_valid:
            await message.reply(f"❌ {validation_msg}")
            return

        # Check time constraint for existing users
        if not is_new_user:
            time_valid, time_msg = self.validator.check_time_constraint(
                user_data["last_post_timestamp"]
            )
            if not time_valid:
                await message.reply(f"⏰ {time_msg}")
                return

        # Update database
        if is_new_user:
            success = self.db.create_user(user_id, username)
        else:
            success = self.db.update_user_progress(
                user_id, username, day_number
            )

        if success:
            if day_number == 100:
                await message.reply(
                    f"🎉 **CONGRATULATIONS {username}!** 🎉\n"
                    f"You've completed the 100 Days of Code challenge! "
                    f"What an incredible achievement! 🏆✨"
                )
            else:
                await message.add_reaction("✅")
                if (
                    day_number % 10 == 0 and day_number < 100
                ):  # Milestone celebrations
                    await message.reply(
                        f"🔥 Milestone reached! Day {day_number} - Keep going strong! 💪"
                    )
        else:
            await message.reply(
                "❌ Error updating your progress. Please try again."
            )

    @commands.command(name="leaderboard")
    async def leaderboard(self, ctx):
        """Show top 5 active streaks"""
        if not ChannelConfig.is_command_allowed(ctx.channel.name):
            return

        top_users = self.db.get_leaderboard(5)

        if not top_users:
            await ctx.send(
                "📊 No active streaks yet! Start logging with [1/100] in #100-days-log"
            )
            return

        embed = discord.Embed(
            title="🏆 100 Days of Code Leaderboard",
            color=0x00FF00,
            timestamp=datetime.datetime.now(datetime.timezone.utc),
        )

        medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]

        for i, user in enumerate(top_users):
            days_ago = (
                datetime.datetime.now(datetime.timezone.utc)
                - user["last_post_timestamp"]
            ).days
            status = f"Day {user['current_day']}"
            if days_ago > 0:
                status += f" (last post {days_ago} days ago)"

            embed.add_field(
                name=f"{medals[i]} {user['username']}",
                value=status,
                inline=False,
            )

        await ctx.send(embed=embed)

    @commands.command(name="100doc-help")
    async def help_command(self, ctx):
        """Show help information"""
        if not ChannelConfig.is_command_allowed(ctx.channel.name):
            return

        embed = discord.Embed(
            title="📚 100 Days of Code Bot Help",
            color=0x0099FF,
            description="Track your coding streak with this bot!",
        )

        embed.add_field(
            name="📝 How to Log Progress",
            value=(
                "• Post in #100-days-log channel only\n"
                "• Format: `[day/100] Your progress description`\n"
                "• Example: `[1/100] Started learning Python basics`\n"
                "• Must start with day 1: `[1/100]`\n"
                "• Only one post per 24 hours\n"
                "• No skipping days or going backwards"
            ),
            inline=False,
        )

        embed.add_field(
            name="🤖 Commands",
            value=(
                "• `!leaderboard` - View top 5 streaks\n"
                "• `!100doc-help` - Show this help message"
            ),
            inline=False,
        )

        embed.add_field(
            name="📋 Admin Commands",
            value=(
                "• `!reset @user` - Reset user's streak\n"
                "• `!force-add @user day` - Set user to specific day\n"
                "• `!status @user` - Check user's status"
            ),
            inline=False,
        )

        embed.add_field(
            name="🔔 Reminders",
            value=(
                "• 3 days inactive: Gentle reminder\n"
                "• 5 days inactive: Firmer reminder\n"
                "• 7 days inactive: Public warning\n"
                "• 14 days inactive: Removed from tracking"
            ),
            inline=False,
        )

        await ctx.send(embed=embed)

    @commands.command(name="reset")
    @commands.has_permissions(administrator=True)
    async def reset_user(self, ctx, member: discord.Member):
        """Reset a user's streak (Admin only)"""
        if not ChannelConfig.is_command_allowed(ctx.channel.name):
            return

        success = self.db.reset_user(member.id)

        if success:
            await ctx.send(f"✅ Reset {member.mention}'s streak back to day 1")
        else:
            await ctx.send(
                f"❌ User {member.mention} not found in tracking system"
            )

    @commands.command(name="force-add")
    @commands.has_permissions(administrator=True)
    async def force_add_user(self, ctx, member: discord.Member, day: int):
        """Force set a user's day (Admin only)"""
        if not ChannelConfig.is_command_allowed(ctx.channel.name):
            return

        if not (1 <= day <= 100):
            await ctx.send("❌ Day must be between 1 and 100")
            return

        success = self.db.force_set_day(member.id, str(member), day)

        if success:
            await ctx.send(f"✅ Set {member.mention} to day {day}")
        else:
            await ctx.send("❌ Error updating user data")

    @commands.command(name="status")
    @commands.has_permissions(administrator=True)
    async def user_status(self, ctx, member: discord.Member):
        """Check a user's status (Admin only)"""
        if not ChannelConfig.is_command_allowed(ctx.channel.name):
            return

        user_data = self.db.get_user_data(member.id)

        if not user_data:
            await ctx.send(
                f"❌ {member.mention} is not in the tracking system"
            )
            return

        days_ago = (
            datetime.datetime.now(datetime.timezone.utc)
            - user_data["last_post_timestamp"]
        ).days
        status = "Active" if user_data["is_active"] else "Inactive"

        embed = discord.Embed(
            title=f"📊 Status for {user_data['username']}",
            color=0x00FF00 if user_data["is_active"] else 0xFF0000,
        )

        embed.add_field(
            name="Current Day", value=user_data["current_day"], inline=True
        )
        embed.add_field(name="Status", value=status, inline=True)
        embed.add_field(
            name="Days Since Last Post", value=days_ago, inline=True
        )
        embed.add_field(
            name="Last Post",
            value=user_data["last_post_timestamp"].strftime(
                "%Y-%m-%d %H:%M UTC"
            ),
            inline=False,
        )

        if user_data["completed_at"]:
            embed.add_field(
                name="Completed",
                value=user_data["completed_at"].strftime("%Y-%m-%d %H:%M UTC"),
                inline=False,
            )

        await ctx.send(embed=embed)

    @tasks.loop(
        time=datetime.time(hour=10, minute=0, tzinfo=datetime.timezone.utc)
    )
    async def daily_reminder_check(self):
        """Daily task to check for inactive users and send reminders"""
        try:
            # Find the logging channel
            logging_channel = None
            for guild in self.guilds:
                for channel in guild.channels:
                    if ChannelConfig.is_logging_channel(channel.name):
                        logging_channel = channel
                        break
                if logging_channel:
                    break

            if not logging_channel:
                logger.warning(
                    "Could not find #100-days-log channel for reminders"
                )
                return

            # Check different inactivity thresholds
            reminders = [
                (
                    3,
                    "gentle",
                    "🌟 Hey there! Just a friendly reminder to log your coding progress. Keep up the great work!",
                ),
                (
                    5,
                    "firm",
                    "⚠️ You haven't posted in 5 days. Don't break your streak now - you've got this!",
                ),
                (
                    7,
                    "warning",
                    "🚨 **7 days without posting!** Your streak is at risk. Please post your progress soon!",
                ),
            ]

            for days, reminder_type, message in reminders:
                inactive_users = self.db.get_inactive_users(days)

                for user_data in inactive_users:
                    days_inactive = (
                        datetime.datetime.now(datetime.timezone.utc)
                        - user_data["last_post_timestamp"]
                    ).days

                    if days_inactive == days:  # Exact day match for reminder
                        try:
                            user = await self.fetch_user(user_data["user_id"])

                            if reminder_type == "warning":
                                # Public warning
                                await logging_channel.send(
                                    f"{message} {user.mention} - Currently on day {user_data['current_day']}"
                                )
                            else:
                                # Private DM
                                await user.send(
                                    f"{message}\n\n"
                                    f"You're currently on day {user_data['current_day']} of your 100-day challenge. "
                                    f"Post in #{ChannelConfig.LOGGING_CHANNEL} to continue your streak!"
                                )
                        except Exception as e:
                            logger.error(
                                f"Failed to send reminder to user {user_data['user_id']}: {e}"
                            )

            # Remove users inactive for 14+ days
            very_inactive = self.db.get_inactive_users(14)
            for user_data in very_inactive:
                self.db.deactivate_user(user_data["user_id"])

                try:
                    user = await self.fetch_user(user_data["user_id"])
                    await logging_channel.send(
                        f"💔 {user.mention} has been removed from tracking after 14 days of inactivity. "
                        f"You can restart anytime with [1/100]!"
                    )
                except Exception as e:
                    logger.error(
                        f"Failed to notify removal of user {user_data['user_id']}: {e}"
                    )

        except Exception as e:
            logger.error(f"Error in daily reminder check: {e}")

    @daily_reminder_check.before_loop
    async def before_reminder_check(self):
        """Wait for bot to be ready before starting reminder task"""
        await self.wait_until_ready()

    # async def setup_hook(self):
    #     #     self.add_command(self.leaderboard)
    #     #     self.add_command(self.help_command)
    #     #     self.add_command(self.reset_user)
    #     #     self.add_command(self.force_add_user)
    #     #     self.add_command(self.user_status)
    #     self.add_command(commands.Command(self.leaderboard))
    #     self.add_command(commands.Command(self.help_command))
    #     self.add_command(commands.Command(self.reset_user))
    #     self.add_command(commands.Command(self.force_add_user))
    #     self.add_command(commands.Command(self.user_status))

    # Error handlers
    async def on_command_error(self, ctx, error):
        """Handle command errors"""
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ You don't have permission to use this command.")
        elif isinstance(error, commands.MemberNotFound):
            await ctx.send("❌ Could not find that user.")
        elif isinstance(error, commands.BadArgument):
            await ctx.send("❌ Invalid argument provided.")
        else:
            logger.error(f"Unhandled error: {error}")
            await ctx.send(
                "❌ An error occurred while processing your command.", error
            )


# Main execution
if __name__ == "__main__":
    intents = discord.Intents.default()
    intents.message_content = True
    intents.members = True
    intents.presences = True

    # bot = HundredDoCBot(command_prefix="!", intents=intents)

    # Initialize and run the bot
    bot = HundredDoCBot()

    try:
        bot.run(TOKEN)
    except Exception as e:
        logger.error(f"Failed to start bot: {e}")
        print("\n🔧 Setup Instructions:")
        print(
            "1. Replace 'DISCORD_BOT_TOKEN' with your actual Discord bot token"
        )
        print("2. Install required packages: pip install discord.py")
        print("3. Create a #100-days-log channel in your Discord server")
        print(
            "4. Give the bot appropriate permissions (Send Messages, Add Reactions, etc.)"
        )
