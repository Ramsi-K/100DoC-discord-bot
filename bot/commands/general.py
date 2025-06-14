# commands/general.py: general commands (help, leaderboard)
import discord
from discord.ext import commands
import datetime
from ..config import ChannelConfig


class GeneralCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="leaderboard")
    async def leaderboard(self, ctx):
        if not ChannelConfig.is_command_allowed(ctx.channel.name):
            return
        top_users = self.bot.db.get_leaderboard(5)
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
                "• Only one post in a 24 hour period\n"
                "• Clock resets at 00:00 UTC\n"
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

    @commands.command(name="remind-toggle")
    async def remind_toggle(self, ctx):
        user_id = ctx.author.id
        user_data = self.bot.db.get_user_data(user_id)
        if not user_data:
            await ctx.send(
                "❌ You're not being tracked yet. Start with `[1/100]` in #100-days-log."
            )
            return
        enabled = user_data.get("reminders_enabled", True)
        new_enabled = not enabled
        self.bot.db.set_reminders_enabled(user_id, new_enabled)
        if new_enabled:
            await ctx.send(
                "🔔 Reminders enabled! We'll notify you if you go inactive."
            )
        else:
            await ctx.send(
                "🔕 Reminders disabled. You won't receive inactivity messages anymore."
            )

    @commands.command(name="myrank")
    async def my_rank(self, ctx):
        user_id = ctx.author.id
        user_data = self.bot.db.get_user_data(user_id)
        if not user_data:
            await ctx.send("❌ You're not being tracked yet.")
            return
        leaderboard = self.bot.db.get_leaderboard(limit=1000)
        rank = next(
            (
                i
                for i, u in enumerate(leaderboard, 1)
                if u["user_id"] == user_id
            ),
            None,
        )
        if rank:
            await ctx.send(
                f"📊 You are currently ranked **#{rank}**, on day {user_data['current_day']}."
            )
        else:
            await ctx.send("You're not on the leaderboard right now.")

    @commands.command(name="status")
    async def self_status(self, ctx):
        user_id = ctx.author.id
        user_data = self.bot.db.get_user_data(user_id)
        if not user_data:
            await ctx.send(
                "❌ You're not being tracked yet. Start with `[1/100]` in #100-days-log."
            )
            return
        days_ago = (
            datetime.datetime.now(datetime.timezone.utc)
            - user_data["last_post_timestamp"]
        ).days
        status = "Active" if user_data["is_active"] else "Inactive"
        embed = discord.Embed(
            title=f"🔎 Status for {user_data['username']}",
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
