# main.py: initializes and runs the bot
import logging
from bot.bot_core import HundredDoCBot
from bot.config import TOKEN
from bot.commands.general import GeneralCommands
from bot.commands.admin import AdminCommands

logging.basicConfig(level=logging.INFO)

if __name__ == "__main__":
    bot = HundredDoCBot()
    bot.add_cog(GeneralCommands(bot))
    bot.add_cog(AdminCommands(bot))
    try:
        bot.run(TOKEN)
    except Exception as e:
        logging.error(f"Failed to start bot: {e}")
        print("\n🔧 Setup Instructions:")
        print(
            "1. Replace 'DISCORD_BOT_TOKEN' with your actual Discord bot token"
        )
        print(
            "2. Install required packages: pip install discord.py python-dotenv"
        )
        print("3. Create a #100-days-log channel in your Discord server")
        print(
            "4. Give the bot appropriate permissions (Send Messages, Add Reactions, etc.)"
        )
