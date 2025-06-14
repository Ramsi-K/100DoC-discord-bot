# commands/admin.py: admin commands (reset, force-add, status)
import discord
from discord.ext import commands
import datetime
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

    @commands.command(name="status")
    @commands.has_permissions(administrator=True)
    async def user_status(self, ctx, member: discord.Member):
        if not ChannelConfig.is_command_allowed(ctx.channel.name):
            return
        user_data = self.bot.db.get_user_data(member.id)
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
