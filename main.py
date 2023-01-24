import discord
from cogs.economy import Economy


from extra.bot_client import CustomBotClient
from extra.guild_manager import GuildConfig, ConfigOption

intents = discord.Intents.all()



client = CustomBotClient(intents=intents)

economy = Economy(client)

client.add_cog(economy)


@client.event
async def on_guild_join(guild: discord.Guild):
    await guild.owner.send("Test")

@client.slash_command(name="setup", description="Setup for Discord Guilds")
async def setup(ctx: discord.ApplicationContext):
    if ctx.author.id == 356159646136008704: # Again shut up PyCharm this works fine
        guild_config: GuildConfig = client.guild_manager.get_guild_config(ctx.guild_id)
        guild_config.economy_functionality_for_guild.data = True
        client.guild_manager.set_guild_config(ctx.guild_id, guild_config)
        await ctx.interaction.response.send_message("Auto setting up the config for Creativious for testing", ephemeral=True)
    # @TODO: Create an interface that allows the server owner to manage the guild config




if __name__ == "__main__":
    client.run("TOKEN")
