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

#############
# DATATYPES #
#############

Ticket = recordclass("Ticket", "creator_id description state mentor_id")
TicketState = Enum("TicketState", "TODO PROG DONE")

class Mentee:
    def __init__(self, first, last, preferred, email, partners, mentor, instr):
        self.first = first
        self.last = last
        self.preferred = preferred
        self.email = email
        self.partners = partners
        self.mentor = mentor
        self.instr = instr

class Mentor:
    def __init__(self, first, last, preferred, email):
        self.first = first
        self.last = last
        self.preferred = preferred
        self.email = email

    def mentees(self, students):
        [x for x in students if x.mentor == self.email]

##########
# CONSTS #
##########

guild_id = 732094742447390732
channel_announcements = 732480582822395945
channel_mentor_queue = 735688058585874433
channel_need_help = 736802874075512853
category_lab = 732094742447390734

# students is a map from an email to the student info
students = {
    "vsastry@ucsd.edu": Mentee("Vibha", "Sastry", "Vibha", "vsastry@ucsd.edu", [], None, None),
    "kgromero@ucsd.edu": Mentee("Katherine", "Romero", "Katherine", "kgromero@ucsd.edu", [], None, None),
    "lmchen@ucsd.edu": Mentee("Lauren", "Chen", "Lauren", "lmchen@ucsd.edu", [], None, None),
    "aolsen@ucsd.edu": Mentee("Alexander", "Olsen", "Alex", "aolsen@ucsd.edu", [], None, None),
    "asierra@ucsd.edu": Mentee("Alyssa", "Sierra", "Alyssa", "asierra@ucsd.edu", [], None, None),
    "dam001@ucsd.edu": Mentee("Diego", "Martinez", "Diego", "dam001@ucsd.edu", [], None, None),
    "jftruong@ucsd.edu": Mentee("Jenelle", "Truong", "Jenelle", "jftruong@ucsd.edu", [], None, None),
    "jrusso@ucsd.edu": Mentee("John-David", "Russo", "John-David", "jrusso@ucsd.edu", [], None, None),
    "hluu@ucsd.edu": Mentee("Henry", "Luu", "Henry", "hluu@ucsd.edu", [], None, None),
    "areljic@ucsd.edu": Mentee("Andrija", "Reljic", "Andrija", "areljic@ucsd.edu", [], None, None),
    "jjdrisco@ucsd.edu": Mentee("John", "Driscoll", "John", "jjdrisco@ucsd.edu", [], None, None),
    "bchester@ucsd.edu": Mentee("Bradley", "Chester", "Bradley", "bchester@ucsd.edu", [], None, None),
    "h3tang@ucsd.edu": Mentee("Harry", "Tang", "Harry", "h3tang@ucsd.edu", [], None, None),
    "yahmad@ucsd.edu": Mentee("Younus", "Ahmad", "Younus", "yahmad@ucsd.edu", [], None, None),
    "mfrankne@ucsd.edu": Mentee("Misa", "Franknedy", "Misa", "mfrankne@ucsd.edu", [], None, None),
    "spapanas@ucsd.edu": Mentee("Sruthi", "Papanasa", "Sruthi", "spapanas@ucsd.edu", [], None, None),
    "ygupta@ucsd.edu": Mentee("Yukati", "Gupta", "Yukati", "ygupta@ucsd.edu", [], None, None),
    "bdittric@ucsd.edu": Mentee("Benjamin", "Dittrich", "Benjamin", "bdittric@ucsd.edu", [], None, None),
    "conti@ucsd.edu": Mentee("Sophia", "Conti", "Sophia", "conti@ucsd.edu", [], None, None),
    "nnazeem@ucsd.edu": Mentee("Nihal", "Nazeem", "Nihal", "nnazeem@ucsd.edu", [], None, None),
    "lmanzano@ucsd.edu": Mentee("Lindsey", "Manzano", "Lindsey", "lmanzano@ucsd.edu", [], None, None),
    "jyliu@ucsd.edu": Mentee("Jeffrey", "Liu", "Jeffrey", "jyliu@ucsd.edu", [], None, None),
    "n9patel@ucsd.edu": Mentee("Nikunjkumar", "Patel", "Nikunjkumar", "n9patel@ucsd.edu", [], None, None),
    "falu@ucsd.edu": Mentee("Faith", "Lu", "Faith", "falu@ucsd.edu", [], None, None),
    "ramartin@ucsd.edu": Mentee("Raul", "Martinez Beltran", "Raul", "ramartin@ucsd.edu", [], None, None),
    "v3patel@ucsd.edu": Mentee("Vedant", "Patel", "Vedant", "v3patel@ucsd.edu", [], None, None),
    "amsingh@ucsd.edu": Mentee("Amaan", "Singh", "Amaan", "amsingh@ucsd.edu", [], None, None),
    "adjensen@ucsd.edu": Mentee("Alexander", "Jensen", "Alexander", "adjensen@ucsd.edu", [], None, None),
    "cwl001@ucsd.edu": Mentee("Cody", "Lee", "Cody", "cwl001@ucsd.edu", [], None, None),
    "nkarter@ucsd.edu": Mentee("Nathaniel", "Karter", "Nathan", "nkarter@ucsd.edu", [], None, None),
    "abanwait@ucsd.edu": Mentee("Armaan", "Banwait", "Armaan", "abanwait@ucsd.edu", [], None, None),
    "y4bao@ucsd.edu": Mentee("James", "Bao", "James", "y4bao@ucsd.edu", [], None, None),
    "nkamalis@ucsd.edu": Mentee("Nima", "Kamali", "Nima", "nkamalis@ucsd.edu", [], None, None),
    "cashby@ucsd.edu": Mentee("Celina", "Ashby", "Celina", "cashby@ucsd.edu", [], None, None),
    "dpederso@ucsd.edu": Mentee("Deena", "Pederson", "Deena", "dpederso@ucsd.edu", [], None, None),
    "shperry@ucsd.edu": Mentee("Sean", "Perry", "Sean", "shperry@ucsd.edu", [], None, None),
    "j1wheele@ucsd.edu": Mentee("Jackson", "Wheeler", "Jackson", "j1wheele@ucsd.edu", [], None, None),
    "d6le@ucsd.edu": Mentee("Don", "Le", "Don", "d6le@ucsd.edu", [], None, None),
    "nfrankli@ucsd.edu": Mentee("Nathalie", "Franklin", "Nathalie", "nfrankli@ucsd.edu", [], None, None),
    "lwtaylor@ucsd.edu": Mentee("Luke", "Taylor", "Luke", "lwtaylor@ucsd.edu", [], None, None),
    "saramesh@ucsd.edu": Mentee("Shohan Aadithya", "Ramesh", "Shohan", "saramesh@ucsd.edu", [], None, None),
    "tchui@ucsd.edu": Mentee("Theodore", "Hui", "Theodore", "tchui@ucsd.edu", [], None, None),
    "gyuan@ucsd.edu": Mentee("Gavin", "Yuan", "Gavin", "gyuan@ucsd.edu", [], None, None),
    "ssrinath@ucsd.edu": Mentee("Sidharth", "Srinath", "Sidharth", "ssrinath@ucsd.edu", [], None, None),
    "b1ho@ucsd.edu": Mentee("Brandon", "Ho", "Brandon", "b1ho@ucsd.edu", [], None, None),
    "tmt003@ucsd.edu": Mentee("Tuan", "Tran", "Tony", "tmt003@ucsd.edu", [], None, None),
    "sttan@ucsd.edu": Mentee("Stephen", "Tan", "Stephen", "sttan@ucsd.edu", [], None, None),
    "psankesh@ucsd.edu": Mentee("Pratheek", "Sankeshi", "Pratheek", "psankesh@ucsd.edu", [], None, None),
    "kit002@ucsd.edu": Mentee("Kira", "Tran", "Kira", "kit002@ucsd.edu", [], None, None),
    "hgrehm@ucsd.edu": Mentee("Hannah", "Grehm", "Hannah", "hgrehm@ucsd.edu", [], None, None),
    "hxiao@ucsd.edu": Mentee("Henry", "Xiao", "Henry", "hxiao@ucsd.edu", [], None, None),
    "tsalud@ucsd.edu": Mentee("Travis", "Salud", "Travis", "tsalud@ucsd.edu", [], None, None),
    "alal@ucsd.edu": Mentee("Akshat", "Lal", "Akshat", "alal@ucsd.edu", [], None, None),
    "axyu@ucsd.edu": Mentee("Aaron", "Yu", "Aaron", "axyu@ucsd.edu", [], None, None),
}

# mentors is the map from mentors' email to their info.
mentors = {
    "unn002@ucsd.edu": Mentor("Nhi", "Nguyen", "Nhi", "unn002@ucsd.edu"),
    "clemarch@ucsd.edu": Mentor("Colin", "Lemarchand", "Colin", "clemarch@ucsd.edu"),
    "melin@ucsd.edu": Mentor("Matias", "Lin", "Matias", "melin@ucsd.edu"),
    "ejewik@ucsd.edu": Mentor("Emily", "Jewik", "Emily", "ejewik@ucsd.edu"),
    "erxiao@ucsd.edu": Mentor("Eric", "Xiao", "Eric", "erxiao@ucsd.edu"),
    "abruevic@ucsd.edu": Mentor("Alise", "Bruevich", "Alise", "abruevic@ucsd.edu"),
    "ambar@ucsd.edu": Mentor("Amit", "Bar", "Amit", "ambar@ucsd.edu"),
    "ddesu@ucsd.edu": Mentor("Dhanvi", "Desu", "Dhanvi", "ddesu@ucsd.edu"),
    "tgarry@ucsd.edu": Mentor("Thomas", "Garry", "Thomas", "tgarry@ucsd.edu"),
    "ettan@ucsd.edu": Mentor("Ethan", "Tan", "Ethan", "ettan@ucsd.edu"),
    "lsteiner@ucsd.edu": Mentor("Lily", "Steiner", "Lily", "lsteiner@ucsd.edu"),
    "l4gonzal@ucsd.edu": Mentor("Lailah", "Gonzalez", "Lailah", "l4gonzal@ucsd.edu"),
    "akatwal@ucsd.edu": Mentor("Anisha", "Atwal", "Anisha", "akatwal@ucsd.edu"),
    "acw011@ucsd.edu": Mentor("Alvin", "Wang", "Alvin", "acw011@ucsd.edu"),
}

################
# GLOBAL STATE #
################

state_file = "state.shelf"
state = shelve.open(state_file, writeback=True)

# initialize our state elements if they aren't in the shelf
def shelf_init(key, val):
    if key not in state:
        state[key] = val

shelf_init("tickets", [])
# student_map is a map from discord user IDs to student emails
shelf_init("student_map", {})
# ea_count is the number of times we've each other'd someone
shelf_init("ea_count", 0)

# print our initial state
print(state["tickets"])
print(state["student_map"])
print(state["ea_count"])

##################
# UTIL FUNCTIONS #
##################

def is_private(channel):
    return isinstance(channel, discord.abc.PrivateChannel)

###########
# THE BOT #
###########

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
    # Note that wait_for fires when the bot sees *any* message; thus, we have to check that
    # the same person sent this message via DMs.
    def email_check(m):
        return member == m.author and is_private(m.channel)

    # Wait for a reply.
    message = await bot.wait_for("message", check=email_check)

    s = students.get(message.content)

    while True:
        if not s:
            msg = "I couldn't find a SPIS student with that email... please try again (and/or check your spelling)!"
            await message.channel.send(msg)
        elif s.email in state["student_map"].values():
            msg = "A SPIS student with that email already exists... please try again (and/or check your spelling)!"
            await message.channel.send(msg)
        else:
            break

        message = await bot.wait_for("message", check=email_check)
        s = students.get(message.content)

    # We found an email!
    # Preemptively add it to the student map
    state["student_map"][message.author.id] = s.email
    # Send back the user info so that they can verify it's correct
    msg = """
Thanks for the info! I found someone with a matching email. Please confirm that this person is you by *reacting* with a thumbs up or thumbs down emoji.
You can do this by clicking/tapping the thumbs up/thumbs down buttons below this message:
"""

    embed = discord.Embed(title="Student info confirmation", description=msg)
    embed.add_field(name="Name", value=f"{s.first} {s.last}")
    embed.add_field(name="Preferred name", value=f"{s.preferred}")
    embed.add_field(name="Email", value=s.email)

    reply = await member.send(embed=embed)

    await reply.add_reaction('👍')
    await reply.add_reaction('👎')

    # The wait_for returns when *any* reaction is added anywhere; we have to make sure that
    # we're reacting to the correct message
    def check(reaction, user):
        return (user == message.author
                and reaction.message.id == reply.id
                and (str(reaction.emoji) == '👍' or str(reaction.emoji) == '👎'))

    reaction, _ = await bot.wait_for('reaction_add', check=check)

    if str(reaction.emoji) == '👍':
        # Confirmed!

        # We first initialize their nickname
        # try so that it doesn't panic if we can't change nick (which won't
        # work for the server owner)
        try:
            await member.edit(nick=f"{s.preferred}")
        except:
            pass

        # We then create the roles and channels we need to create
        await init_roles(member)

        desc = f"""
Congrats! You've finished the first-time setup. It's nice to meet you, {s.preferred} :)

Now that we've verified who you are, you now have access to all of the different text and voice chats in the Discord server. Eventually, we'll be showing you how to use all these different parts of the server through live walkthroughs and write-ups.

For now, you should read through the different informational text channels we have on the server:

- `#discord-info` has more information on what each of the channels in the Discord server are for.
- `#announcements` contains SPIS-wide announcements regarding assignment deadlines and other urgent info.

Beyond that, all there is to do now is to **jump in and start getting to know your mentors and your fellow mentees!** Our general text chat for hanging out is (appropriately) called `#hanging-out`, so hop on and introduce yourself!

Have fun, and welcome to SPIS!
"""
        embed = discord.Embed(title=f"Welcome to SPIS, {s.preferred}", description=desc)
        await member.send(embed=embed)

    else:
        msg = """Sorry about that! Please type in another email."""
        state["student_map"].pop(member.id, None)

        await member.send(msg)
        await verify_email(member)

async def init_roles(member):
    # Get the student
    s = students[state["student_map"][member.id]]

    # Get their email username
    su = s.email.split('@')[0].lower()

    # For each of the student's partners:
    # Get their joined names
    n = "-".join(sorted([su] + [x.email.split('@')[0].lower() for x in s.partners]))

    # Get their mentor, if exists
    m = s.mentor.split('@')[0].lower() if s.mentor != None else None

    # Make the student a Mentee
    await member.add_roles(get(member.guild.roles, name="Mentee"))

    # We need to create two roles:
    # pair-{min(s, p)}-{max(s, p)}
    # mentor-{mentor}
    pair_name = f"pair--{n}"
    pair_role = get(member.guild.roles, name=pair_name)
    pair_role = await member.guild.create_role(name=pair_name, colour=discord.Color.purple()) if not pair_role else pair_role
    await member.add_roles(pair_role)

    if m:
        mentor_name = f"mentor--{m}"
        mentor_role = get(member.guild.roles, name=mentor_name)
        mentor_role = await member.guild.create_role(name=mentor_name, colour=discord.Color.dark_purple()) if not mentor_role else mentor_role
        await member.add_roles(mentor_role)

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
    footer = "picobot 2020-07-28 | https://github.com/dcao/spisbot"

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
    if (is_private(ctx.channel)
            and id_not_in_q(ctx.message.author.id)
            and (ctx.author.id not in state['student_map']
                 or students[state['student_map'][ctx.author.id]].preferred is None)):
        await add_ticket(ctx.message.author, "Needs help with onboarding")

def id_not_in_q(id):
    return id not in [x.creator_id for x in state["tickets"] if x.state != TicketState.DONE]

async def add_ticket(creator, description):
    # Someone just asked for help. We need to add a ticket!
    t = Ticket(creator.id, description, TicketState.TODO, None)
    tid = len(state['tickets']) + 1
    state['tickets'].append(t)

    embed = discord.Embed(title=f"Ticket #{tid}", color=discord.Color.red())
    embed.add_field(name="Description", value=description, inline=False)
    if creator.id in state['student_map']:
        embed.add_field(name="Creator", value=students[state['student_map'][creator.id]].name, inline=True)
        for i, p in students[state["student_map"][creator.id]].partners:
            embed.add_field(name=f"Partner {i}", value=students[p].name, inline=True)
    else:
        embed.add_field(name="Creator", value=f"<@!{creator.id}>", inline=True)

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
                    and reaction.message.id == msg.id
                    and ((str(reaction.emoji) == '👍' and user.id not in [x.mentor_id for x in state["tickets"] if x.state == TicketState.PROG])
                         or str(reaction.emoji) == '☑️'))

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

        t.mentor_id = user.id

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
        new_embed = discord.Embed(title=f"Ticket #{tid}")
        new_embed.add_field(name="Current mentor", value=f"<@!{user.id}>", inline=False)
        new_embed.add_field(name="Description", value=description, inline=False)
        if creator.id in state['student_map']:
            new_embed.add_field(name="Creator", value=students[state['student_map'][creator.id]].name, inline=True)
            for i, p in students[state["student_map"][creator.id]].partners:
                new_embed.add_field(name=f"Partner {i}", value=students[p].name, inline=True)
        else:
            new_embed.add_field(name="Creator", value=f"<@!{creator.id}>", inline=True)

        await msg.edit(embed=new_embed)

        def add_check(reaction, ur):
            return (ur == user
                    and reaction.message.id == msg.id
                    and str(reaction.emoji) == '☑️')

        def remove_check(reaction, ur):
            return (ur == user
                    and reaction.message.id == msg.id
                    and str(reaction.emoji) == '👍')

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
                t.mentor_id = None

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
@bot.command(name='syncroles')
@commands.has_role("Mentor")
async def sync_roles(ctx):
    # TODO: sync roles in server with our data from
    # partner_map/mentor_map/instr_map
    pass

@bot.command(name='purgeroles')
@commands.has_role("Mentor")
async def purge_roles(ctx):
    for role in ctx.guild.roles:
        if role.name.startswith("pair--") or role.name.startswith("mentor--"):
            await role.delete()
    
    for channel in ctx.guild.voice_channels:
        if channel.name.startswith("pair--") or channel.name.startswith("mentor--"):
            await channel.delete()

    for channel in ctx.guild.text_channels:
        if channel.name.startswith("pair--") or channel.name.startswith("mentor--"):
            await channel.delete()

    # Reset the dictionary
    state["student_map"] = {}

    # Remove Mentee role
    role_names = ("Mentee",)
    roles = tuple(get(ctx.guild.roles, name=n) for n in role_names)
    for m in ctx.guild.members:
        try:
            await m.remove_roles(*roles)
        except:
            print(f"Couldn't remove roles from {m}")

@bot.command(name='shutdown')
@commands.has_role("Mentor")
async def shutdown(ctx):
    await bot.close()

bot.run(token)
