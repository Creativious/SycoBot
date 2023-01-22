import discord
from creativiousUtilities.discord import BotClient
from creativiousUtilities import discord as cdiscord
from cogs.economy import Economy
import sys

intents = discord.Intents.all()

client = BotClient(intents=intents)

economy = Economy(client)

client.add_cog(economy)

# cdiscord.loadAllCogs(client, "cogs/")

client.run("TOKEN ")
