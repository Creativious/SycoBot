import asyncio
import datetime
import math
from abc import ABC, abstractmethod
from typing import Dict

import discord
from discord.ext import commands
import pickle
import time
from os import path
import random
from creativiousUtilities.memory import SelfPurgingObject
from asyncio.windows_events import ProactorEventLoop
from asyncio.events import AbstractEventLoop
import json

from extra.bot_client import CustomBotClient
from extra.guild_manager import GuildConfig


class Item:
    def __init__(self, name: str, worth: int):
        self.name = name
        self.worth = worth
        self.sell_worth = self._get_sell_worth()

    def _get_sell_worth(self):
        return round(self.worth * .9) # 10% value deduction for selling


class Player(SelfPurgingObject, ABC):
    def __init__(self, discord_id: int, player_manager, event_loop: ProactorEventLoop | AbstractEventLoop, time_till_purge_in_seconds: int):
        super().__init__(time_till_purge_in_seconds=time_till_purge_in_seconds, event_loop=event_loop)
        self.credits = 0
        self.discord_id = discord_id
        self.player_manager = player_manager

        self.last_message_time_as_int = 0
        self.joined_vc_at_time_as_int = None
        self.last_time_daily_was_used = 0

    def set_credits(self, i: int):
        self.reset_timer()
        self.credits = i

    def reset_daily_timer(self):
        self.reset_timer()
        self.last_time_daily_was_used = time.time()

    def get_daily_time(self):
        self.reset_timer(False)
        return self.last_time_daily_was_used

    def reset_joined_vc_time(self, wipe: bool = False):
        self.reset_timer()
        if wipe:
            self.joined_vc_at_time_as_int = None
        else:
            self.joined_vc_at_time_as_int = time.time()

    def get_joined_vc_time(self):
        self.reset_timer(False)
        return self.joined_vc_at_time_as_int

    def reset_last_message_time(self):
        self.last_message_time_as_int = time.time()
        self.reset_timer()

    def get_last_message_time(self):
        self.reset_timer(False)
        return self.last_message_time_as_int


    def add_credits(self, i: int):
        self.set_credits(self.credits + i)
    def remove_credits(self, i: int):
        self.set_credits(self.credits - i)

    def get_credits(self):
        self.reset_timer(False)
        return self.credits

    def remove_credits_if_enough(self, i: int):
        """Returns a boolean, true if the player had enough and the amount was removed and false if they didn't have enough and nothing was removed"""
        if self.credits - i >= i:
            self.remove_credits(i)
            return True
        else:
            self.reset_timer()
            return False

    def _save(self, auto=False):
        if auto:
            self.save_player()
            self.player_manager.loaded_players.pop(str(self.discord_id))
        else:
            self.save_player()

    def save_player(self):
        with open(f"{path.join('data/players/', str(self.discord_id) + '.player')}", "wb") as f:
            pickle.dump(self, f)
        pass

    def __getstate__(self):
        state = self.__dict__.copy()
        state['event_loop'] = None
        state['current_event_loop_call'] = None
        state['time_to_be_deleted'] = None
        state['player_manager'] = None
        return state

    def __setstate__(self, state):
        self.__dict__.update(state)

        # SOLVES CLASS BEING UPDATED AND PICKLE THROWING A FIT
        current_dict = self.__dict__.copy()
        self.__init__(self.discord_id, self.player_manager, self.event_loop, self.purge_time_delay)
        self.__dict__.update(current_dict)


    def after_load(self, event_loop: ProactorEventLoop | AbstractEventLoop, player_manager):
        self.setup_part_2(event_loop)
        self.player_manager = player_manager




class PlayerManager:
    def __init__(self, event_loop: ProactorEventLoop | AbstractEventLoop):
        self.loaded_players: Dict[str, Player] = {} # Players loaded in memory
        self.players = [] # List of player IDs, likely will be faster than searching through directories
        self.max_time_till_purged = 300 # 5 minutes, maybe 10 minute for future premium users???
        self.event_loop = event_loop
        self.load_player_list()

    def __load_player(self, discord_id: int):
        player: Player
        with open(f"{path.join('data/players/', str(discord_id) + '.player')}", "rb") as f:
            player = pickle.load(f)
        player.after_load(event_loop=self.event_loop, player_manager=self)
        self.loaded_players[str(discord_id)] = player
        return player

    def get_player(self, discord_id: int):
        if str(discord_id) in self.loaded_players:
            self.loaded_players.get(str(discord_id)).reset_timer()
            return self.loaded_players.get(str(discord_id))
        elif str(discord_id) in self.players:
            return self.__load_player(discord_id)
        else:
            return self._create_player(discord_id)

    def save_player_list(self):
        with open("data/players/player_list.json", "w+") as f:
            f.write(json.dumps({'list': self.players}))

    def load_player_list(self):
        with open("data/players/player_list.json", "r") as f:
            thing: dict = json.loads(f.read())
            if thing.__contains__('list'):
                self.players = thing['list']

    def _create_player(self, discord_id: int):
        if str(discord_id) not in self.loaded_players and str(discord_id) not in self.players:
            player = Player(discord_id=discord_id, event_loop=self.event_loop, player_manager=self, time_till_purge_in_seconds=self.max_time_till_purged)
            player.save_player()
            self.players.append(str(discord_id))
            self.save()
            self.loaded_players[str(discord_id)] = player
            return player
        else:
            return self.get_player(discord_id)

    def save(self):
        self.save_player_list()
        for player in self.loaded_players:
            player_obj: Player = self.loaded_players[player]
            player_obj.save_player()


class Economy(commands.Cog):

    def __init__(self, bot: CustomBotClient):
        self.bot: CustomBotClient = bot
        self.player_manager: PlayerManager = PlayerManager(self.bot.event_loop)

    @discord.Cog.listener()
    async def on_message(self, message: discord.Message):

        if message.author.id != self.bot.user.id and not message.author.bot:
            guild_config: GuildConfig = self.bot.guild_manager.get_guild_config(message.guild.id)
            if guild_config.economy_functionality_for_guild.data:
                player: Player = self.player_manager.get_player(message.author.id)

                if player.get_last_message_time() <= time.time() - 60: # Messages older than one minute
                    reward_amount = random.randint(1, 10)
                    self.player_manager.get_player(message.author.id).add_credits(reward_amount)
                    self.player_manager.get_player(message.author.id).reset_last_message_time()

    @discord.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):

        if member.id != self.bot.user.id and not member.bot:
            guild_config: GuildConfig = self.bot.guild_manager.get_guild_config(member.guild.id)
            if guild_config.economy_functionality_for_guild.data:
                if before.channel != after.channel:
                    time_elapsed = 0
                    player: Player = self.player_manager.get_player(member.id)
                    if after.channel is not None and before.channel is None:
                        player.reset_joined_vc_time()
                    elif after.channel is not None and before.channel is not None and player.get_joined_vc_time() is not None:
                        time_elapsed = time.time() - player.get_joined_vc_time()
                        player.reset_joined_vc_time()
                    elif after.channel is None and before.channel is not None and player.get_joined_vc_time() is not None:
                        time_elapsed = time.time() - player.get_joined_vc_time()
                        player.reset_joined_vc_time(True)
                    else:
                        player.reset_joined_vc_time(True)
                        reward_amount = random.randint(1, 5) # Pity reward for when we didn't catch it
                        print(f"{member.name} ({member.id}) got a pity reward of {reward_amount}")

                    if time_elapsed != 0 and time_elapsed >= 900: # 900 seconds or 15 minutes
                        reward_times = math.floor(time_elapsed / 900)
                        reward_amount = 0
                        i = 0
                        while i < reward_times:
                            reward_amount += random.randint(3, 10)
                            i += 1
                        self.player_manager.get_player(member.id).add_credits(reward_amount)

    @discord.slash_command(description="Gives your balance or the person mentioned balance")
    async def bal(self, ctx: discord.ApplicationContext, *, member: discord.Member = None):
        if member is None:
            player: Player = self.player_manager.get_player(ctx.author.id)
            await ctx.interaction.response.send_message(
                    f"Your balance is `{player.get_credits()}`", ephemeral=True)
        else:
            if not member.bot:
                player: Player = self.player_manager.get_player(member.id)
                await ctx.interaction.response.send_message(
                    f"{member.name}'s balance is `{player.get_credits()}`", ephemeral=True)
            else:
                await ctx.interaction.response.send_message("Sorry you can't get the balance of a bot, please try it on an actual person!", ephemeral=True)

    @discord.slash_command(description="Gives you your daily allowance!")
    async def daily(self, ctx: discord.ApplicationContext):
        player: Player = self.player_manager.get_player(ctx.author.id)
        daily_timer = 86400 # 1 Day
        if player.get_daily_time() <= time.time() - daily_timer:
            player.reset_daily_timer()
            reward_amount = random.randint(50, 100) # Maybe will raise this later but not now
            player.add_credits(reward_amount)
            await ctx.interaction.response.send_message(
                f"You've been awarded `{reward_amount}` credits!", ephemeral=True)
        else:
            time_left = player.get_daily_time() - (time.time() - daily_timer)
            await ctx.interaction.response.send_message(
                f"{round(time_left)} seconds left till you can use daily again (*note from dev* : Going to make this more user readable soon)", ephemeral=True)