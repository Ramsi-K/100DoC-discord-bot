# config.py: ChannelConfig and constants
import os
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_BOT_TOKEN")


class ChannelConfig:
    """Channel configuration for feature control"""

    LOGGING_CHANNEL = "100-days-log"
    ALLOWED_COMMAND_CHANNELS = [
        "debug-room",  # for testing
        "cloud-chat",  # main discussion
        "off-topic",
        "quick-help",
        "sheclouds",
    ]

    @classmethod
    def is_logging_channel(cls, channel_name: str) -> bool:
        return channel_name == cls.LOGGING_CHANNEL

    @classmethod
    def is_command_allowed(cls, channel_name: str) -> bool:
        return (
            channel_name in cls.ALLOWED_COMMAND_CHANNELS
            or channel_name == cls.LOGGING_CHANNEL
        )
