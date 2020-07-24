from recordclass import recordclass
import datetime as dt
from enum import Enum
import os
import random
import shelve

import discord
from discord.ext import commands, tasks
from discord.utils import get
from dotenv import load_dotenv

load_dotenv()
token = os.getenv('DISCORD_TOKEN')

# Datatypes
Person = recordclass("Person", ["name", "email", "preferred_name"])

# Consts
channel_announcements = 732480582822395945
category_lab = 732094742447390734

# students is the list of SPIS students
students = [
    Person("David Cao", "dmcao@ucsd.edu", None),
    Person("Ethan Tan", "ettan@ucsd.edu", None)
]

# mentors is the list of SPIS mentors
mentors = [
    Person("Mentor A", "mentora@ucsd.edu", "Mentor")
]

# pairs is a list of tuples of the names of SPIS students who are paired,
# along with the name of their mentor.
pairs = [
    ("David Cao", "Ethan Tan", "Mentor A")
]

# TODO: Have a mentors map from mentor names to known user IDs?

# Global state
state_file = "state.shelf"
state = shelve.open(state_file, writeback=True)

# initialize our state elements if they aren't in the shelf
def shelf_init(key, val):
    if key not in state:
        state[key] = val

shelf_init("events", [])
shelf_init("queue", [])
# student_map is a map from discord user IDs to students
shelf_init("student_map", {})
# ea_count is the number of times we've each other'd someone
shelf_init("ea_count", 0)

# print our initial state
print(state["events"])
print(state["queue"])
print(state["student_map"])
print(state["ea_count"])

# Get this student's partner
def find_partner(name):
    p = next((x for x in pairs if name == x[0] or name == x[1]), None)
    n = p[0] if p[0] != name else p[1]
    if p:
        return next((x for x in students if n == x.name), None)
    else:
        return None

# Get this student's mentor
def find_mentor(name):
    m = next((x[2] for x in pairs if name == x[0] or name == x[1]), None)
    if m:
        return next((x for x in mentors if m == x.name), None)
    else:
        return None

# THE BOT
# Custom Bot class to override close
class Bot(commands.Bot):
    async def close(self):
        state.close()
        await super().close()

bot = Bot('/')
bot.remove_command("help")

@bot.event
async def on_ready():
    # activity = discord.Game(name="Netflix")
    activity = discord.Activity(type=discord.ActivityType.watching, name="your every move")
    await bot.change_presence(activity=activity)
    print("Bot is ready!")

@bot.event
async def on_member_join(member):
    if member.id not in state["student_map"]:
        await join(member)

# for testing
@bot.command(name="testjoin")
@commands.has_role("Mentor")
async def testjoin(ctx):
    await join(ctx.message.author)

async def join(member):
    intro = """
Yo yo yo! Welcome to SPIS 2020. I'm **Picobot**, an automated bot here to help you with all things related to the SPIS 2020 Discord!

For now, I'm here to help onboard you to the SPIS 2020 Discord server. Before you can get started and hang out with everyone else, I need to know who you are first. Then I'll introduce you to all the different parts of the Discord server.

If you need help at any point, just text me the word `/helpme` (with the slash!) and a mentor will come and help you. In case this bot breaks or you want to contact us directly, feel free to email any one of the mentors (our emails are on the SPIS People page).

With that being said, let's get started!
"""

    embed = discord.Embed(title="Welcome to SPIS!", description=intro)
    await member.send(embed=embed)

    email = """
In order to let you talk in the Discord server, I need to know who you are first!
**Please text me your `@ucsd.edu` email:**
"""
    embed = discord.Embed(title="Email verification", description=email)
    await member.send(embed=embed)

    await verify_email(member)

async def verify_email(member):
    def email_check(m):
        return member == m.author

    # Wait for a reply.
    message = await bot.wait_for("message", check=email_check)

    s = next((x for x in students if x.email == message.content), None)

    while not s:
        msg = "I couldn't find a SPIS student with that email... please try again (and/or check your spelling)!"
        await message.channel.send(msg)
        message = await bot.wait_for("message", check=email_check)
        s = next((x for x in students if x.email == message.content), None)

    # We found an email!
    # Preemptively add them to the student map
    state["student_map"][message.author.id] = s
    # Send back the user info so that they can verify it's correct
    msg = """
Thanks for the info! I found someone with a matching email. Please confirm that this person is you by *reacting* with a thumbs up or thumbs down emoji.
You can do this by clicking/tapping the thumbs up/thumbs down buttons below this message:
"""

    embed = discord.Embed(title="Student info confirmation", description=msg)
    embed.add_field(name="Name", value=s.name, inline=False)
    embed.add_field(name="Email", value=s.email, inline=False)

    reply = await message.channel.send(embed=embed)

    await reply.add_reaction('👍')
    await reply.add_reaction('👎')

    def check(reaction, user):
        return user == message.author and (str(reaction.emoji) == '👍' or str(reaction.emoji) == '👎')

    reaction, user = await bot.wait_for('reaction_add', check=check)

    if str(reaction.emoji) == '👍':
        # Confirmed!
        confirm_msg = f"""
Awesome! Welcome to SPIS, {state["student_map"][message.author.id].name}!

One last question: **What's your preferred name?** Please text the nickname you want other people to call you by; if you don't have one, just send your first name.

_(You can always change this later too!)_
"""

        embed = discord.Embed(title="Preferred name", description=confirm_msg)
        await message.channel.send(embed=embed)

        # Update their preferred name
        name_msg = await bot.wait_for("message")
        state["student_map"][message.author.id].preferred_name = name_msg.content

        # We first initialize their nickname
        # try so that it doesn't panic if we can't change nick (which won't
        # work for the server owner)
        try:
            await member.edit(nick=f"{state['student_map'][message.author.id].preferred_name} ({state['student_map'][message.author.id].name})")
        except:
            pass

        # We then create the roles and channels we need to create
        await init_roles(member)

        fin_msg = "Fin"
        await message.channel.send(fin_msg)

    else:
        msg = """Sorry about that! Please type in another email."""

        await message.channel.send(msg)
        await verify_email(member)

async def init_roles(member):
    # Get the student
    s = state["student_map"][member.id]

    # We don't use preferred names here since we might not have one for the
    # partner when creating these roles

    # Get their name
    n = s.email.split('@')[0].lower()

    # Get their partner
    p = find_partner(s.name).email.split('@')[0].lower()

    # Get their mentor
    m = find_mentor(s.name).email.split('@')[0].lower()

    # Make the student a Mentee
    await member.add_roles(get(member.guild.roles, name="Mentee"))

    # We need to create two roles:
    # pair-{min(s, p)}-{max(s, p)}
    # mentor-{mentor}
    pair_name = f"pair--{min(n, p)}-{max(n, p)}"
    mentor_name = f"mentor--{m}"

    if not get(member.guild.roles, name=pair_name):
        pair_role = await member.guild.create_role(name=pair_name, colour=discord.Color.purple())
        mentor_role = await member.guild.create_role(name=mentor_name, colour=discord.Color.dark_purple())
    
    # We also need to create a pair channel:
    labs = get(member.guild.categories, id=category_lab)

    if not get(member.guild.voice_channels, name=pair_name):
        nc = await member.guild.create_voice_channel(pair_name, category=labs)
        await nc.set_permissions(member.guild.default_role, view_channel=False)
        await nc.set_permissions(get(member.guild.roles, name="Professor"), view_channel=True)
        await nc.set_permissions(get(member.guild.roles, name="Mentor"), view_channel=True)
        await nc.set_permissions(pair_role, view_channel=True)

@bot.command(name='helpme')
async def onboarding_help(ctx):
    # TODO: only do something if this is a private channel
    pass

@bot.command(name='removeroles')
@commands.has_role("Mentor")
async def remove_roles(ctx):
    for role in ctx.guild.roles:
        if role.name.startswith("pair--") or role.name.startswith("mentor--"):
            await role.delete()
    
    for channel in ctx.guild.voice_channels:
        if channel.name.startswith("pair--") or channel.name.startswith("mentor--"):
            await channel.delete()

    for channel in ctx.guild.text_channels:
        if channel.name.startswith("pair--") or channel.name.startswith("mentor--"):
            await channel.delete()

@bot.command(name='help')
async def help(ctx):
    desc = """
This is where commands will go
"""
    embed = discord.Embed(title='Picobot General Help', description=desc)
    embed.set_footer(text="picobot 2020-07-23 | https://github.com/dcao/spisbot")

    await ctx.message.channel.send(embed=embed)

# Check if we have any events happening within the next hour.
# If so, post in the announcements channel about it.
@tasks.loop(hours=1)
async def check_events():
    message_channel = bot.get_channel(channel_announcements)
    # TODO
    pass

@bot.event
async def on_message(message):
    # What are we doing?
    if message.author.id != bot.user.id and what_doing(message.content):
        state["ea_count"] += 1
        await message.channel.send(f"each other! (count: {state['ea_count']})")

    await bot.process_commands(message)

def what_doing(text):
    text = text.lower()
    return ("what are" in text or "what am" in text) and "doin" in text

@bot.command(name='shutdown')
@commands.has_role("Mentor")
async def shutdown(ctx):
    await bot.close()

bot.run(token)
