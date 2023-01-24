from abc import ABC
from typing import Dict
from os import path
import pickle
import json
from asyncio import ProactorEventLoop, AbstractEventLoop

from creativiousUtilities.memory import SelfPurgingObject


class ConfigOption:
    def __init__(self, config_version: int, data):
        self.data = data
        self.config_version = config_version

class GuildConfig:
    def __init__(self):
        self.current_config_version = 1 # Update whenever a new config option is released


        self.notification_when_new_config_options_are_released = ConfigOption(1, False)
        """Config setting that will send a message to the owner of the server whenever a new config option is released"""


        self.economy_functionality_for_guild = ConfigOption(1, False)
        """Config setting that will allow the Economy Cog to function in the guild"""




    def on_load(self):
        current_dict = self.__dict__.copy()
        self.__init__()
        self.__dict__.update(current_dict)




class Guild(SelfPurgingObject, ABC):
    def __init__(self, guild_id, guild_manager, event_loop: ProactorEventLoop | AbstractEventLoop, time_till_purge_in_seconds: int):
        super().__init__(event_loop, time_till_purge_in_seconds)
        self.guild_id = guild_id
        self.guild_manager = guild_manager
        self.config: GuildConfig = GuildConfig()

    def _save(self, auto = False):
        if auto:
            self.save_guild()
            self.guild_manager.loaded_guilds.pop(str(self.guild_id)) # After saving
        else:
            self.save_guild()

    def save_guild(self):
        with open(f"{path.join('data/guilds', str(self.guild_id) + '.guild')}", 'wb') as f:
            pickle.dump(self, f)

    def __getstate__(self):
        state = self.__dict__.copy()
        state['event_loop'] = None
        state['current_event_loop_call'] = None
        state['time_to_be_deleted'] = None
        state['guild_manager'] = None
        return state

    def __setstate__(self, state):
        self.__dict__.update(state)
        self.config.on_load()

        current_dict = self.__dict__.copy()
        self.__init__(self.guild_id, self.guild_manager, self.event_loop, self.purge_time_delay)
        self.__dict__.update(current_dict)


    def after_load(self, event_loop: ProactorEventLoop | AbstractEventLoop, guild_manager):
        self.setup_part_2(event_loop)
        self.guild_manager = guild_manager

    def get_config(self):
        self.reset_timer(False)
        return self.config

    def set_config(self, config: GuildConfig):
        self.config = config
        self.reset_timer()



class GuildManager:
    def __init__(self, event_loop: ProactorEventLoop | AbstractEventLoop):
        self.event_loop = event_loop
        self.guilds = []
        self.loaded_guilds: Dict[str, Guild] = {}
        self.max_time_till_purged = 60
        self.load_guild_list()

    def __load_guild(self, guild_id: int):
        guild: Guild
        with open(f"{path.join('data/guilds', str(guild_id) + '.guild')}", 'rb') as f:
            guild = pickle.load(f)
        guild.after_load(self.event_loop, self)
        self.loaded_guilds[str(guild_id)] = guild
        return guild

    def load_guild_list(self):
        with open("data/guilds/guild_list.json", "r") as f:
            thing: dict = json.loads(f.read())
            if thing.__contains__('list'):
                self.guilds = thing['list']

    def save_guild_list(self):
        with open("data/guilds/guild_list.json", "w+") as f:
            f.write(json.dumps({'list': self.guilds}))

    def _create_guild(self, guild_id: int):
        if str(guild_id) not in self.loaded_guilds and str(guild_id) not in self.guilds:
            guild = Guild(guild_id, self, self.event_loop, self.max_time_till_purged)
            guild.save_guild()
            self.guilds.append(str(guild_id))
            self.save()
            self.loaded_guilds[str(guild_id)] = guild
            return guild

        else:
            return self.get_guild(guild_id)

    def get_guild(self, guild_id: int):
        if str(guild_id) in self.loaded_guilds:

            self.loaded_guilds.get(str(guild_id)).reset_timer()
            return self.loaded_guilds.get(str(guild_id))
        elif str(guild_id) in self.guilds:
            return self.__load_guild(guild_id)
        else:
            return self._create_guild(guild_id)

    def save(self):
        self.save_guild_list()
        for guild in self.loaded_guilds:
            guild_obj: Guild = self.loaded_guilds[guild]
            guild_obj.save_guild()

    def load_all_guilds_and_check(self):
        for guild_identifier in self.guilds:
            guild: Guild = self.get_guild(int(guild_identifier))
            # @TODO For when we do notifications for config updates

    def after_load_functions(self):
        self.load_all_guilds_and_check()

    def get_guild_config(self, guild_id: int):
        return self.get_guild(guild_id).config

    def set_guild_config(self, guild_id: int, config: GuildConfig):
        self.get_guild(guild_id).set_config(config)