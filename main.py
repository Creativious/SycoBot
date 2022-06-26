import discord
import utils.customLogger
import utils.sqlcontroller
from discord.ext import commands

""" Basic Setup """

loginToken = ""
with open("sensitive_files/token.txt", "r") as f:
    loginToken = str(f.read())

dbPassword = ""
with open("sensitive_files/dbpassword.txt", "r") as f:
    dbPassword = str(f.read())

class CoreBot(commands.Bot):
    def __init__(self, command_prefix, **options):
        super().__init__(command_prefix, **options)
        self.logger = utils.customLogger.Logger(name="Syco", subname="Core", debug=True).getLogger()
        self.logger.info("Startup!")
        self.sql = utils.sqlcontroller.SQLController(user="postgres", password=dbPassword, dbname="sycoDB")

    def shutdown(self):
        self.sql.shutdown()
        self.logger.info("Bot has shutdown!")


client = CoreBot("$", debug_guilds=[990041308368339015])

@client.event
async def on_ready():
    client.logger.info(f"Logged into {str(client.user.name)} ({str(client.user.id)})")
    activity = discord.Game(name="Message me with /help to get started!")
    client.intents.all()
    client.remove_command("help")
    await client.change_presence(activity=activity, status=discord.Status.idle)

@client.slash_command(name="help")
async def help(ctx):
    await ctx.respond("Hello")

@client.command()
async def test(ctx):
    client.logger.debug("This is a debug statement")
    await ctx.respond("Hello 2")

client.run(loginToken)
client.shutdown()