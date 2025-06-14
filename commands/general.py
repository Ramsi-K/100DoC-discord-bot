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
