# commands/admin.py: admin commands (reset, force-add)
import discord
import datetime
from discord.ext import commands
from ..config import ChannelConfig


class AdminCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="reset")
    @commands.has_permissions(administrator=True)
    async def reset_user(self, ctx, member: discord.Member):
        if not ChannelConfig.is_command_allowed(ctx.channel.name):
            return
        success = self.bot.db.reset_user(member.id)
        if success:
            await ctx.send(f"✅ Reset {member.mention}'s streak back to day 1")
            try:
                await member.send(
                    "🔄 Your 100 Days of Code streak has been reset to Day 1 by an admin.  Please log your progress again starting with [1/100] or reach out to the admin team if you have questions."
                )
            except Exception:
                pass
        else:
            await ctx.send(
                f"❌ User {member.mention} not found in tracking system"
            )

    @commands.command(name="force-add")
    @commands.has_permissions(administrator=True)
    async def force_add_user(self, ctx, member: discord.Member, day: int):
        if not ChannelConfig.is_command_allowed(ctx.channel.name):
            return
        if not (1 <= day <= 100):
            await ctx.send("❌ Day must be between 1 and 100")
            return
        success = self.bot.db.force_set_day(member.id, str(member), day)
        if success:
            await ctx.send(f"✅ Set {member.mention} to day {day}")
        else:
            await ctx.send("❌ Error updating user data")

    @commands.command(name="list-users")
    @commands.has_permissions(administrator=True)
    async def list_users(self, ctx):
        all_users = self.bot.db.get_leaderboard(limit=1000)
        if not all_users:
            await ctx.send("📋 No tracked users in the database.")
            return

        lines = []
        for i, user in enumerate(all_users, 1):
            days_ago = (
                datetime.datetime.now(datetime.timezone.utc)
                - user["last_post_timestamp"]
            ).days
            lines.append(
                f"{i}. {user['username']} — Day {user['current_day']} ({days_ago}d ago)"
            )

        chunks = [lines[i : i + 10] for i in range(0, len(lines), 10)]
        for chunk in chunks:
            await ctx.send("\n".join(chunk))

    @commands.command(name="drop-user")
    @commands.has_permissions(administrator=True)
    async def drop_user(self, ctx, member: discord.Member):
        conn = self.bot.db.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM user_streaks WHERE user_id = ?", (member.id,)
        )
        conn.commit()
        conn.close()
        await ctx.send(
            f"🗑️ {member.display_name} has been removed from tracking."
        )
        try:
            await member.send(
                "🗑️ You have been removed from 100 Days of Code tracking by an admin. Please log your progress again starting with [1/100] or reach out to the admin team if you have questions."
            )
        except Exception:
            pass

    @commands.command(name="userstatus")
    @commands.has_permissions(administrator=True)
    async def user_status(self, ctx, member: discord.Member):
        user_data = self.bot.db.get_user_data(member.id)
        if not user_data:
            await ctx.send(
                f"❌ {member.mention} is not in the tracking system."
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

    @commands.command(name="inactive")
    @commands.has_permissions(administrator=True)
    async def list_inactive(self, ctx, days: int = 3):
        users = self.bot.db.get_inactive_users(days_threshold=days)
        if not users:
            await ctx.send("✅ No inactive users found.")
            return
        for u in users:
            await ctx.send(
                f"{u['username']} — Day {u['current_day']} (last seen {u['last_post_timestamp'].strftime('%b %d')})"
            )
