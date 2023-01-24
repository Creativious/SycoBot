import asyncio
from abc import ABC
from typing import Any

from creativiousUtilities.discord import BotClient

from extra.guild_manager import GuildManager


class CustomBotClient(BotClient, ABC):
    def __init__(self, **options: Any):
        super().__init__(**options)
        self.event_loop = asyncio.get_event_loop()
        self.guild_manager: GuildManager = GuildManager(self.event_loop)