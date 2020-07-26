import asyncio
import datetime as dt
from enum import Enum
import os
import random
from recordclass import recordclass
import shelve

import discord
from discord.ext import commands, tasks
from discord.utils import get
from dotenv import load_dotenv

load_dotenv()
token = os.getenv('DISCORD_TOKEN')

# Datatypes
Person = recordclass("Person", ["name", "email", "preferred_name"])
Ticket = recordclass("Ticket", "creator_id description state")
TicketState = Enum("TicketState", "TODO PROG DONE")

# Consts
guild_id = 732094742447390732
channel_announcements = 732480582822395945
channel_mentor_queue = 735688058585874433
channel_need_help = 736802874075512853
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
# shelf_init("tickets", [])
state["tickets"] = []
# student_map is a map from discord user IDs to students
shelf_init("student_map", {})
# ea_count is the number of times we've each other'd someone
shelf_init("ea_count", 0)

# print our initial state
print(state["events"])
print(state["tickets"])
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
Yo yo yo! Welcome to SPIS 2020. I'm **Picobot**, an automated bot here to help manage and moderate the SPIS 2020 Discord!

For now, I'm here to help welcome you to the SPIS 2020 Discord server. You'll notice that as of right now, you can't type in any of the channels. Don't worry; this is so that we can protect ourselves against random people from joining our server, and so that we can verify who you are before you can talk in the Discord. Before you can get started and hang out with everyone else, I need to know who you are first.

If you need help at any point, just text me the word `/helpme` (with the slash!) and a mentor will come and help you. In case this bot breaks or you want to contact us directly, feel free to email any one of the mentors (our emails are on the SPIS People page).

With that being said, let's get started!
"""

    embed = discord.Embed(title="Welcome to SPIS!", description=intro)
    await member.send(embed=embed)

    registered = """
The first thing you should do is **claim your Discord account**. This basically means signing up for a permanent Discord account with an email and a password. If you already have a registered Discord account, you don't need to worry about this step. If you don't, you should be able to do this by clicking the big "Claim your account" button at the top of the window.

**Do not skip this step.** If you do, your SPIS student info will be associated with a Discord account you cannot access again.
"""

    embed = discord.Embed(title="Claim your Discord account", description=registered)
    await member.send(embed=embed)

    email = """
Now that that's out of the way, in order to let you talk in the Discord server, I need to know who you are first!
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
Awesome! One last question: **What's your preferred name?** Please text the nickname you want other people to call you by; if you don't have one, just send your first name.

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

        desc = f"""
Congrats! You've finished the first-time setup. It's nice to meet you, {state['student_map'][message.author.id].preferred_name} :)

Now that we've verified who you are, you now have access to all of the different text and voice chats in the Discord server. Eventually, we'll be showing you how to use all these different parts of the server through live walkthroughs and write-ups.

For now, you should read through the different informational text channels we have on the server:

- `#discord-info` has more information on what each of the channels in the Discord server are for.
- `#announcements` contains SPIS-wide announcements regarding assignment deadlines and other urgent info.
- `#useful-links` contains links to useful resources, e.g. the SPIS website and Piazza pages.

Beyond that, all there is to do now is to *jump in and start getting to know your mentors and your fellow mentees!* Our general text chat for hanging out is (appropriately) called `#hanging-out`, so hop on and introduce yourself!

Have fun, and welcome to SPIS!
"""
        embed = discord.Embed(title=f"Welcome to SPIS, {state['student_map'][message.author.id].preferred_name}", description=desc)
        await message.channel.send(embed=embed)

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

@bot.command(name='help')
async def help(ctx, arg1=None):
    footer = "picobot 2020-07-26 | https://github.com/dcao/spisbot"

    if arg1 == "tickets":
        desc = """
To accept a ticket, **add a thumbs up reaction**. You can do this by clicking on the thumbs up button under the ticket.

If you would like to later "unaccept" it, remove your thumbs up reaction by clicking the thumbs up again.

If you would to resolve it, click the check mark reaction (or react with the `:ballot_box_with_check:` emoji).
"""

        embed = discord.Embed(title='Picobot Help | Tickets', description=desc)
        embed.set_footer(text=footer)

        await ctx.message.channel.send(embed=embed)
    else:
        desc = """
Picobot is the custom-made robot designed to help manage the SPIS 2020 Discord server. While you can send me commands to make me do things, I'm also always sitting in the background to help welcome people to the SPIS server and manage queue tickets.

**General commands**

- `/icebreaker`: returns a random icebreaker question. Good for getting to know your fellow mentees!

**Other help categories**

- `/help tickets`: show help for managing queue tickets (intended for mentors only)
"""
        embed = discord.Embed(title='Picobot Help', description=desc)
        embed.set_footer(text=footer)

        await ctx.message.channel.send(embed=embed)

# Check if we have any events happening within the next hour.
# If so, post in the announcements channel about it.
@tasks.loop(hours=1)
async def check_events():
    message_channel = bot.get_channel(channel_announcements)
    # TODO
    pass

# Get a random icebreaker question!
@bot.command("icebreaker")
async def icebreaker(ctx):
    questions = [
        "What are some things you’ve heard about your respective colleges?",
        "If you had a sixth college pet raccoon, what would you name them?",
        "What’s something everyone would look dumb doing?",
        "Do you wipe your butt before or after you poop?",
        "What’s something you can say while coding and in the bedroom?",
        "Who was your childhood actor/actress crush?",
        "Which cartoon character do you relate to the most?",
        "What major would you choose if you did not have your current major?",
        "What’s the best tv series you have ever seen?",
        "The zombie apocalypse is coming, which 3 people are you taking to survive?",
    ]

    await ctx.channel.send(random.choice(questions))

def what_doing(text):
    text = text.lower()
    return ("what are" in text or "what am" in text) and "doin" in text

@bot.event
async def on_message(message):
    # What are we doing?
    if message.author.id != bot.user.id:
        if what_doing(message.content):
            state["ea_count"] += 1
            await message.channel.send(f"each other! (count: {state['ea_count']})")
        elif message.channel.id == channel_need_help:
            if id_not_in_q(message.author.id):
                await add_ticket(message.author, message.content)

    await bot.process_commands(message)

@bot.command(name='helpme')
async def onboarding_help(ctx):
    if (isinstance(ctx.channel, discord.abc.PrivateChannel)
            and id_not_in_q(ctx.message.author.id)
            and (ctx.author.id not in state['student_map']
                 or state['student_map'][ctx.author.id].preferred_name is None)):
        await add_ticket(ctx.message.author, "Needs help with onboarding")

def id_not_in_q(id):
    return id not in [x.creator_id for x in state["tickets"] if x.state != TicketState.DONE]

async def add_ticket(creator, description):
    # Someone just asked for help. We need to add a ticket!
    t = Ticket(creator.id, description, TicketState.TODO)
    tid = len(state['tickets']) + 1
    state['tickets'].append(t)

    embed = discord.Embed(title=f"Ticket #{tid}")
    embed.add_field(name="Description", value=description, inline=False)
    if creator.id in state['student_map']:
        embed.add_field(name="Creator", value=state['student_map'][creator.id].name, inline=True)
        embed.add_field(name="Partner", value=find_partner(state['student_map'][creator.id].name).name, inline=True)
    else:
        embed.add_field(name="Creator", value=creator.display_name, inline=True)

    msg = await bot.get_channel(channel_mentor_queue).send(embed=embed)

    await msg.add_reaction('👍')
    await msg.add_reaction('☑️')

    # Message user that their ticket was created
    await creator.send("Your ticket was created! A list of all the tickets in the queue is in the `#ticket-queue` channel.", embed=embed)

    resolved = False
    
    while not resolved:
        def check(reaction, user):
            return ((get(bot.get_guild(guild_id).roles, name="Mentor") in user.roles
                    or get(bot.get_guild(guild_id).roles, name="Professor") in user.roles)
                    and (str(reaction.emoji) == '👍' or str(reaction.emoji) == '☑️'))

        reaction, user = await bot.wait_for('reaction_add', check=check)

        if str(reaction.emoji) == '☑️':
            # Ticket closed without resolution
            t.state = TicketState.DONE
            await msg.delete()

            # Message user that their ticket was closed
            closed_desc = f"Your ticket was closed without resolution by <@!{user.id}>. You can contact them directly via DM for more information."
            closed_embed = discord.Embed(title=f"Ticket #{tid} closed", description=closed_desc)

            await creator.send(embed=closed_embed)

            return

        if (hasattr(creator, 'voice')
                and creator.voice is not None
                and creator.voice.channel is not None):
            if user.voice is not None:
                await user.move_to(creator.voice.channel)
            else:
                voice_desc = f"Student <@!{creator.id}> is currently located in voice channel `{creator.voice.channel}.`"
                voice_embed = discord.Embed(title=f"Ticket #{tid} accepted", description=voice_desc)
                await user.send(embed=voice_embed)
        else:
            voice_desc = f"Student <@!{creator.id}> is not located in a voice channel."
            voice_embed = discord.Embed(title=f"Ticket #{tid} accepted", description=voice_desc)
            await user.send(embed=voice_embed)

        # Notify student
        accept_desc = f"Your ticket has been accepted by <@!{user.id}>; you'll be receiving assistance from them shortly."
        accept_embed = discord.Embed(title=f"Ticket #{tid} accepted", description=accept_desc)
        await creator.send(embed=accept_embed)

        # Edit the original message to reflect the current mentor
        new_embed = embed.copy()
        new_embed.add_field(name="Mentor", value=user.display_name)
        await msg.edit(embed=new_embed)

        def add_check(reaction, ur):
            return ur == user and str(reaction.emoji) == '☑️'

        def remove_check(reaction, ur):
            return ur == user and str(reaction.emoji) == '👍'

        # Wait for either unaccept or resolve
        pending = [bot.wait_for('reaction_add',check=add_check),
                bot.wait_for('reaction_remove',check=remove_check)]
        done, pending = await asyncio.wait(pending, return_when=asyncio.FIRST_COMPLETED)

        for task in pending:
            task.cancel()

        for task in done:
            rr, user = await task

            if str(rr.emoji) == '☑️':
                # This ticket is complete!
                # Delete it and set its state accordingly
                t.state = TicketState.DONE
                await msg.delete()

                # Message user that their ticket was closed
                resolved_desc = f"Your ticket was resolved by <@!{user.id}>."
                resolved_embed = discord.Embed(title=f"Ticket #{tid} resolved", description=resolved_desc)

                await creator.send(embed=resolved_embed)

                return
            else:
                # This ticket isn't complete
                # Set its embed back to the original embed
                await msg.edit(embed=embed)

                # Message user that their ticket was unaccepted
                unaccepted_desc = f"Your ticket could not be resolved by <@!{user.id}>. It has been added back to the queue."
                unaccepted_embed = discord.Embed(title=f"Ticket #{tid} unaccepted", description=unaccepted_desc)

                await creator.send(embed=unaccepted_embed)

    # TODO: Commands for on/off-duty
    
@bot.command(name='cleartickets')
@commands.has_role("Mentor")
async def clear_tickets(ctx):
    for x in state["tickets"]:
        x.state = TicketState.DONE

    # TODO: msg ppl individually?

    await bot.get_channel(channel_mentor_queue).purge()

# Purge all messages from a channel
@bot.command(name='purge')
@commands.has_role("Mentor")
async def purge(ctx):
    await ctx.channel.purge()

# Administrative commands - use with care!
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

@bot.command(name='shutdown')
@commands.has_role("Mentor")
async def shutdown(ctx):
    await bot.close()

bot.run(token)
