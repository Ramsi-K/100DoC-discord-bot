# bot_core.py: HundredDoCBot class
import discord
from discord.ext import commands, tasks
import datetime
import logging
import os
from .config import ChannelConfig
from .database import DatabaseManager
from .validators import StreakValidator

logger = logging.getLogger(__name__)


class HundredDoCBot(commands.Bot):
    """Main bot class for 100 Days of Cloud tracking"""

    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)
        # Use the DB_PATH environment variable which is set in run_bot()
        self.db = DatabaseManager(os.environ.get("DB_PATH", "/data/streaks.db"))
        self.validator = StreakValidator()
        self.remove_command("help")

    async def on_ready(self):
        logger.info(f"{self.user} has connected to Discord!")
        if not self.daily_reminder_check.is_running():
            self.daily_reminder_check.start()

    async def on_message(self, message):
        if message.author.bot:
            return
        if ChannelConfig.is_logging_channel(message.channel.name):
            await self.handle_log_message(message)
        await self.process_commands(message)

    async def handle_log_message(self, message):
        day_number = self.validator.parse_log_message(message.content)
        if day_number is None:
            return
        user_id = message.author.id
        username = str(message.author)
        user_data = self.db.get_user_data(user_id)
        is_new_user = user_data is None
        current_day = 0 if is_new_user else user_data["current_day"]
        is_valid, validation_msg = self.validator.is_valid_progression(
            current_day, day_number, is_new_user
        )
        if not is_valid:
            await message.reply(f"❌ {validation_msg}")
            return
        if not is_new_user:
            time_valid, time_msg = self.validator.check_time_constraint(
                user_data["last_post_timestamp"]
            )
            if not time_valid:
                await message.reply(f"⏰ {time_msg}")
                return
        if is_new_user:
            success = self.db.create_user(user_id, username)
        else:
            success = self.db.update_user_progress(
                user_id, username, day_number
            )
        if success:
            if day_number == 100:
                self.db.archive_to_hof(user_id, username)

                await message.reply(
                    f"🎉 **CONGRATULATIONS {username}!** 🎉\n"
                    f"You've completed the 100 Days of Cloud challenge! "
                    f"What an incredible achievement! ✨"
                    f"Welcome to the Hall of Fame! 🏆"
                )
            else:
                await message.add_reaction("✅")
                if day_number % 10 == 0 and day_number < 100:
                    await message.reply(
                        f"🔥 Milestone reached! Day {day_number} - Keep going strong! 💪"
                    )
        else:
            await message.reply(
                "❌ Error updating your progress. Please try again."
            )

    @tasks.loop(
        time=datetime.time(hour=10, minute=0, tzinfo=datetime.timezone.utc)
    )
    async def daily_reminder_check(self):
        try:
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
                    if not user_data.get("reminders_enabled", True):
                        continue  # Skip users with reminders disabled
                    days_inactive = (
                        datetime.datetime.now(datetime.timezone.utc)
                        - user_data["last_post_timestamp"]
                    ).days
                    if days_inactive == days:
                        try:
                            user = await self.fetch_user(user_data["user_id"])
                            if reminder_type == "warning":
                                await logging_channel.send(
                                    f"{message} {user.mention} - Currently on day {user_data['current_day']}"
                                )
                            else:
                                await user.send(
                                    f"{message}\n\n"
                                    f"You're currently on day {user_data['current_day']} of your 100-day challenge. "
                                    f"Post in #{ChannelConfig.LOGGING_CHANNEL} to continue your streak!"
                                )
                        except Exception as e:
                            logger.error(
                                f"Failed to send reminder to user {user_data['user_id']}: {e}"
                            )
            very_inactive = self.db.get_inactive_users(14)
            for user_data in very_inactive:
                self.db.deactivate_user(user_data["user_id"])
                try:
                    user = await self.fetch_user(user_data["user_id"])
                    await logging_channel.send(
                        f"💔 {user.mention} has been removed from tracking after 14 days of inactivity. "
                        f"You can restart anytime with [1/100]!"
                    )
                    try:
                        await user.send(
                            "💔 You’ve been removed from 100 Days of Code tracking after 14 days of inactivity. This challenge is tough, but every attempt is progress! When you’re ready, you can always start again with [1/100]. We believe in you!"
                        )
                    except Exception:
                        pass
                except Exception as e:
                    logger.error(
                        f"Failed to notify removal of user {user_data['user_id']}: {e}"
                    )
        except Exception as e:
            logger.error(f"Error in daily reminder check: {e}")

    @daily_reminder_check.before_loop
    async def before_reminder_check(self):
        await self.wait_until_ready()

    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ You don't have permission to use this command.")
        elif isinstance(error, commands.MemberNotFound):
            await ctx.send("❌ Could not find that user.")
        elif isinstance(error, commands.BadArgument):
            await ctx.send("❌ Invalid argument provided.")
        else:
            logger.error(f"Unhandled error: {error}")
            await ctx.send(
                "❌ An error occurred while processing your command."
            )
