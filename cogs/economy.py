import asyncio
from abc import ABC, abstractmethod
from typing import Dict

from discord.ext import commands
import pickle
import time
from os import path
from creativiousUtilities.memory import SelfPurgingObject
from asyncio.windows_events import ProactorEventLoop
from asyncio.events import AbstractEventLoop
import json

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
        self.coins = 0
        self.discord_id = discord_id
        self.player_manager = player_manager

    def set_coins(self, i: int):
        self.reset_timer()
        self.coins = i

    def add_coins(self, i: int):
        self.set_coins(self.coins + i)
    def remove_coins(self, i: int):
        self.set_coins(self.coins - i)

    def remove_coins_if_enough(self, i: int):
        """Returns a boolean, true if the player had enough and the amount was removed and false if they didn't have enough and nothing was removed"""
        if self.coins - i >= i:
            self.remove_coins(i)
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
        player.after_load(self.event_loop, self)
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
    def __init__(self, bot):
        self.bot = bot
        self.event_loop = asyncio.get_event_loop()
        self.player_manager = PlayerManager(self.event_loop)