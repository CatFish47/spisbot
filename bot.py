import os
import datetime as dt
import random

from discord.ext import commands, tasks
from dotenv import load_dotenv

load_dotenv()
token = os.getenv('DISCORD_TOKEN')

# global vars
events = []
channel_announcements = 732480582822395945

bot = commands.Bot('/')

@bot.command(name='about')
async def about(ctx):
    await ctx.send("spisbot 2020-07-18")

# Check if we have any events happening within the next hour.
# If so, post in the announcements channel about it.
@tasks.loop(hours=1)
async def check_events():
    message_channel = bot.get_channel(channel_announcements)
    # TODO
    pass

bot.run(token)