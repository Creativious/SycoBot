import discord
from discord.ext import commands

"""Basic Setup"""

loginToken = ""
with open("token.txt", "r") as f:
    loginToken = str(f.read())

bot = discord.Client()
