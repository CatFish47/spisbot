import asyncio
from collections import defaultdict
import datetime as dt
from enum import Enum
import itertools as it
import os
import random
from recordclass import recordclass
import shelve

import discord
from discord.ext import commands, tasks
from discord.utils import get
from dotenv import load_dotenv
from discord import ActionRow, Button, ButtonColor

# for /wide
import requests
import io
from PIL import Image
from tempfile import NamedTemporaryFile

import time

# watch yo profanity
from better_profanity import profanity

load_dotenv()
token = os.getenv("DISCORD_TOKEN")

#############
# DATATYPES #
#############

Ticket = recordclass("Ticket", "creator_id description state mentor_id")
TicketState = Enum("TicketState", "TODO PROG DONE")


class Mentee:
    def __init__(
        self, first, last, preferred, email, partner_emails, mentor_emails, instr
    ):
        self.first = first
        self.last = last
        self.preferred = preferred
        self.email = email
        self.partner_emails = partner_emails
        self.mentor_emails = mentor_emails
        self.instr = instr

    # Return the mentee's unique identifier - the part before their @ucsd.edu
    def ident(self):
        return self.email.split("@")[0].lower()

    # Return the unique identifier for the "group" of the student
    # (i.e. the student and their partners)
    def group_ident(self, students):
        return "-".join(
            sorted([self.first] + [students[x].first for x in self.partner_emails])
        )

    def partners(self, students):
        return [students[x] for x in self.partner_emails]

    def mentors(self, mentors):
        return [mentors[x] for x in self.mentor_emails]

class Mentor:
    def __init__(self, first, last, preferred, email):
        self.first = first
        self.last = last
        self.preferred = preferred
        self.email = email

    def mentees(self, students):
        return [x for x in students if x.mentor == self.email]

    # Return the mentor's unique identifier - the part before their @ucsd.edu
    def ident(self):
        return self.email.split("@")[0].lower()


##########
# CONSTS #
##########

channel_announcements = 1003017006162907246
channel_mentor_queue = 1003078378154377256
channel_need_help = 1003077822161629274
category_breakout = 1003078148566552636
category_lab = 1003077628623847424
category_mentors = 1003078093205946429

mentor_role_name = "Mentors"
mentee_role_name = "Mentees"
professor_role_name = "Instructors"

# students is a map from an email to the student info
'''
Structure:
ucsd_email: Mentee(
    first_name,
    last_name,
    preferred_name,
    ucsd_email,
    [partner_email],
    [mentor_email],
    professor_name
),
'''
students = {
    "haj008@ucsd.edu": Mentee(
		"Haesol",
		"Jung",
		"Haesol",
		"haj008@ucsd.edu",
		["anh034@ucsd.edu"],
		["gxcheng@ucsd.edu"],
		"phill"
	),
    "chn021@ucsd.edu": Mentee(
		"Chuong",
		"Nguyen",
		"Chuong",
		"chn021@ucsd.edu",
		["ryl001@ucsd.edu"],
		["rurioste@ucsd.edu"],
		"phill"
	),
    "nxwang@ucsd.edu": Mentee(
		"Nathan",
		"Wang",
		"Nathan",
		"nxwang@ucsd.edu",
		["jqxiang@ucsd.edu"],
		["j7bui@ucsd.edu"],
		"curt"
	),
    "ezxiong@ucsd.edu": Mentee(
		"Eddie",
		"Xiong",
		"Eddie",
		"ezxiong@ucsd.edu",
		["mazab@ucsd.edu"],
		["bchester@ucsd.edu", "jsimpauco@ucsd.edu"],
		"niema"
	),
    "szhai@ucsd.edu": Mentee(
		"Steven",
		"Zhai",
		"Steven",
		"szhai@ucsd.edu",
		["e7han@ucsd.edu"],
		["a1wang@ucsd.edu"],
		"niema"
	),
    "m6chu@ucsd.edu": Mentee(
		"Michael",
		"Chu",
		"Michael",
		"m6chu@ucsd.edu",
		["adapsay@ucsd.edu"],
		["adhami@ucsd.edu"],
		"phill"
	),
    "daji@ucsd.edu": Mentee(
		"Daniel",
		"Ji",
		"Daniel",
		"daji@ucsd.edu",
		["aimai@ucsd.edu"],
		["nnazeem@ucsd.edu"],
		"niema"
	),
    "omiller@ucsd.edu": Mentee(
		"Owen",
		"Miller",
		"Owen",
		"omiller@ucsd.edu",
		["cjfan@ucsd.edu"],
		["j7bui@ucsd.edu"],
		"curt"
	),
    "nipillai@ucsd.edu": Mentee(
		"Nitya",
		"Pillai",
		"Nitya",
		"nipillai@ucsd.edu",
		["mekumar@ucsd.edu"],
		["ehcho@ucsd.edu"],
		"curt"
	),
    "jqxiang@ucsd.edu": Mentee(
		"Jonathan",
		"Xiang",
		"Jonathan",
		"jqxiang@ucsd.edu",
		["nxwang@ucsd.edu"],
		["j7bui@ucsd.edu"],
		"curt"
	),
    "natrinh@ucsd.edu": Mentee( # nancy?
		"Warren",
		"Trinh",
		"Warren",
		"natrinh@ucsd.edu",
		["bryoon@ucsd.edu"],
		["sil045@ucsd.edu"],
		"phill"
	),
    "anh034@ucsd.edu": Mentee(
		"Andy",
		"Ho",
		"Andy",
		"anh034@ucsd.edu",
		["haj008@ucsd.edu"],
		["gxcheng@ucsd.edu"],
		"phill"
	),
    "dwumendez@ucsd.edu": Mentee(
		"Denise",
		"Wu-Mendez",
		"Denise",
		"dwumendez@ucsd.edu",
		["jeemi@ucsd.edu"],
		["nseyoum@ucsd.edu"],
		"curt"
	),
    "p2do@ucsd.edu": Mentee(
		"Phuc",
		"Do",
		"Kevin",
		"p2do@ucsd.edu",
		["avn011@ucsd.edu"],
		["ehcho@ucsd.edu"],
		"curt"
	),
    "mazab@ucsd.edu": Mentee(
		"Mohammed",
		"Azab",
		"Mohammed",
		"mazab@ucsd.edu",
		["ezxiong@ucsd.edu"],
		["bchester@ucsd.edu", "jsimpauco@ucsd.edu"],
		"niema"
	),
    "tzchuang@ucsd.edu": Mentee(
		"Tzy-Harn",
		"Chuang",
		"Serena",
		"tzchuang@ucsd.edu",
		["dregmi@ucsd.edu"],
		["rkafle@ucsd.edu"],
		"phill"
	),
    "hisayama@ucsd.edu": Mentee(
		"Hikaru",
		"Isayama",
		"Sean",
		"hisayama@ucsd.edu",
		["bscheerger@ucsd.edu"],
		["adhami@ucsd.edu"],
		"phill"
	),
    "aimai@ucsd.edu": Mentee(
		"Aidan",
		"Mai",
		"Aidan",
		"aimai@ucsd.edu",
		["daji@ucsd.edu"],
		["nnazeem@ucsd.edu"],
		"niema"
	),
    "adapsay@ucsd.edu": Mentee(
		"Adrian",
		"Apsay",
		"Adrian",
		"adapsay@ucsd.edu",
		["m6chu@ucsd.edu"],
		["adhami@ucsd.edu"],
		"phill"
	),
    "kkeertipati@ucsd.edu": Mentee(
		"Kiran",
		"Keertipati",
		"Kiran",
		"kkeertipati@ucsd.edu",
		["msoares@ucsd.edu"],
		["jlk004@ucsd.edu"],
		"niema"
	),
    "bryoon@ucsd.edu": Mentee(
		"Brandon",
		"Yoon",
		"Brandon",
		"bryoon@ucsd.edu",
		["natrinh@ucsd.edu"],
		["sil045@ucsd.edu"],
		"phill"
	),
    "arsureshkumar@ucsd.edu": Mentee(
		"Arjun",
		"Suresh Kumar",
		"Arjun",
		"arsureshkumar@ucsd.edu",
		["jscrook@ucsd.edu"],
		["rurioste@ucsd.edu"],
		"phill"
	),
    "a4padilla@ucsd.edu": Mentee(
		"Ashley",
		"Padilla",
		"Ashley",
		"a4padilla@ucsd.edu",
		["averthein@ucsd.edu"],
		["jlk004@ucsd.edu"],
		"niema"
	),
    "zroland@ucsd.edu": Mentee(
		"Zack",
		"Roland",
		"Zack",
		"zroland@ucsd.edu",
		["emirandaramirez@ucsd.edu"],
		["bchester@ucsd.edu", "jsimpauco@ucsd.edu"],
		"niema"
	),
    "ruchandrupatla@ucsd.edu": Mentee(
		"Rushil",
		"Chandrupatla",
		"Rushil",
		"ruchandrupatla@ucsd.edu",
		["ryding@ucsd.edu"],
		["aawelch@ucsd.edu"],
		"curt"
	),
    "ryding@ucsd.edu": Mentee(
		"Ryan",
		"Ding",
		"Ryan D",
		"ryding@ucsd.edu",
		["ruchandrupatla@ucsd.edu"],
		["aawelch@ucsd.edu"],
		"curt"
	),
    "bmdunn@ucsd.edu": Mentee(
		"Brenton",
		"Dunn",
		"Brenton",
		"bmdunn@ucsd.edu",
		["g7xu@ucsd.edu"],
		["nnazeem@ucsd.edu"],
		"niema"
	),
    "jeemi@ucsd.edu": Mentee(
		"Jensen",
		"Emi",
		"Jensen",
		"jeemi@ucsd.edu",
		["dwumendez@ucsd.edu"],
		["nseyoum@ucsd.edu"],
		"curt"
	),
    "etflores@ucsd.edu": Mentee(
		"Ethan",
		"Flores",
		"Ethan F",
		"etflores@ucsd.edu",
		["gvidra@ucsd.edu"],
		["bchester@ucsd.edu", "jsimpauco@ucsd.edu"],
		"niema"
	),
    "mekumar@ucsd.edu": Mentee(
		"Megha",
		"Kumar",
		"Megha",
		"mekumar@ucsd.edu",
		["nipillai@ucsd.edu"],
		["ehcho@ucsd.edu"],
		"curt"
	),
    "ril006@ucsd.edu": Mentee(
		"Richard",
		"Li",
		"Richard",
		"ril006@ucsd.edu",
		["igross@ucsd.edu"],
		["sil045@ucsd.edu"],
		"phill"
	),
    "syl010@ucsd.edu": Mentee(
		"Stephanie",
		"Li",
		"Stephanie",
		"syl010@ucsd.edu",
		["yvtang@ucsd.edu"],
		["rkafle@ucsd.edu"],
		"phill"
	),
    "rpanaparambil@ucsd.edu": Mentee(
		"Ravina",
		"Panaparambil",
		"Ravina",
		"rpanaparambil@ucsd.edu",
		["vit008@ucsd.edu"],
		["nseyoum@ucsd.edu"],
		"curt"
	),
    "dregmi@ucsd.edu": Mentee(
		"Drishti",
		"Regmi",
		"Drishti",
		"dregmi@ucsd.edu",
		["tzchuang@ucsd.edu"],
		["rkafle@ucsd.edu"],
		"phill"
	),
    "bscheerger@ucsd.edu": Mentee(
		"Benjamin",
		"Scheerger",
		"Benjamin",
		"bscheerger@ucsd.edu",
		["hisayama@ucsd.edu"],
		["adhami@ucsd.edu"],
		"phill"
	),
    "yvtang@ucsd.edu": Mentee(
		"Ying",
		"Tang",
		"Vicky",
		"yvtang@ucsd.edu",
		["syl010@ucsd.edu"],
		["rkafle@ucsd.edu"],
		"phill"
	),
    "gvidra@ucsd.edu": Mentee(
		"Gavriel",
		"Vidra",
		"Gavi",
		"gvidra@ucsd.edu",
		["etflores@ucsd.edu"],
		["bchester@ucsd.edu", "jsimpauco@ucsd.edu"],
		"niema"
	),
    "emirandaramirez@ucsd.edu": Mentee(
		"Emerson",
		"Miranda-Ramirez",
		"Emerson",
		"emirandaramirez@ucsd.edu",
		["zroland@ucsd.edu"],
		["bchester@ucsd.edu", "jsimpauco@ucsd.edu"],
		"niema"
	),
    "pcl004@ucsd.edu": Mentee(
		"Peter",
		"Lee",
		"Peter",
		"pcl004@ucsd.edu",
		["v9sharma@ucsd.edu"],
		"aawelch@ucsd.edu",
		"curt"
	),
    "jscrook@ucsd.edu": Mentee(
		"James",
		"Crook",
		"James",
		"jscrook@ucsd.edu",
		["arsureshkumar@ucsd.edu"],
		["rurioste@ucsd.edu"],
		"phill"
	),
    "g7xu@ucsd.edu": Mentee(
		"Guoxuan",
		"Xu",
		"Jason",
		"g7xu@ucsd.edu",
		["bmdunn@ucsd.edu"],
		["nnazeem@ucsd.edu"],
		"niema"
	),
    "tot005@ucsd.edu": Mentee(
		"Tony",
		"Tran",
		"Tony",
		"tot005@ucsd.edu",
		["idelarosa@ucsd.edu"],
		"gxcheng@ucsd.edu",
		"phil"
	),
    "cjfan@ucsd.edu": Mentee(
		"Connor",
		"Fan",
		"Connor",
		"cjfan@ucsd.edu",
		["omiller@ucsd.edu"],
		["j7bui@ucsd.edu"],
		"curt"
	),
    "avn011@ucsd.edu": Mentee(
		"Addy",
		"Ngo",
		"Addy",
		"avn011@ucsd.edu",
		["p2do@ucsd.edu"],
		["ehcho@ucsd.edu"],
		"curt"
	),
    "msoares@ucsd.edu": Mentee(
		"Madeline",
		"Soares",
		"Madeline",
		"msoares@ucsd.edu",
		["kkeertipati@ucsd.edu"],
		["jlk004@ucsd.edu"],
		"niema"
	),
    "vit008@ucsd.edu": Mentee(
		"Vivian",
		"Tran",
		"Vivian",
		"vit008@ucsd.edu",
		["rpanaparambil@ucsd.edu"],
		["nseyoum@ucsd.edu"],
		"curt"
	),
    "yalbaker@ucsd.edu": Mentee(
		"Yaser",
		"Albaker",
		"Yaser",
		"yalbaker@ucsd.edu",
		["empangan@ucsd.edu"],
		"a1wang@ucsd.edu",
		"niema"
	),
    "igross@ucsd.edu": Mentee(
		"Ian",
		"Gross",
		"Ian",
		"igross@ucsd.edu",
		["ril006@ucsd.edu"],
		["sil045@ucsd.edu"],
		"phill"
	),
    "v9sharma@ucsd.edu": Mentee(
		"Vinayak",
		"Sharma",
		"Vinayak",
		"v9sharma@ucsd.edu",
		["pcl004@ucsd.edu"],
		"aawelch@ucsd.edu",
		"curt"
	),
    "averthein@ucsd.edu": Mentee(
		"Anastasiya",
		"Verthein",
		"Nata",
		"averthein@ucsd.edu",
		["a4padilla@ucsd.edu"],
		["jlk004@ucsd.edu"],
		"niema"
	),
    "ryl001@ucsd.edu": Mentee(
		"Ryan",
		"Liu",
		"Ryan L",
		"ryl001@ucsd.edu",
		["chn021@ucsd.edu"],
		["rurioste@ucsd.edu"],
		"phill"
	),
    "e7han@ucsd.edu": Mentee(
		"Ethan",
		"Han",
		"Ethan H",
		"e7han@ucsd.edu",
		["szhai@ucsd.edu"],
		["a1wang@ucsd.edu"],
		"niema"
	),
    "empangan@ucsd.edu": Mentee(
		"Emmett",
		"Pangan",
		"Emmett",
		"empangan@ucsd.edu",
		["yalbaker@ucsd.edu"],
		"a1wang@ucsd.edu",
		"niema"
	),
    "idelarosa@ucsd.edu": Mentee(
		"Isaiah",
		"De La Rosa",
		"Isaiah",
		"idelarosa@ucsd.edu",
		["tot005@ucsd.edu"],
		"gxcheng@ucsd.edu",
		"phil"
	),

}

# mentors is the map from mentors' email to their info.
'''
Structure:
ucsd_email: Mentor(first_name, last_name, preferred_name, ucsd_email),
'''
mentors = {
    "aasapra@ucsd.edu": Mentor("Aammya", "Sapra", "Aammya", "aasapra@ucsd.edu"),
    "aawelch@ucsd.edu": Mentor("Alessia", "Welch", "Alessia", "aawelch@ucsd.edu"),
    "adhami@ucsd.edu": Mentor("Amir", "Dhami", "Amir", "adhami@ucsd.edu"),
    "a1wang@ucsd.edu": Mentor("Anthony", "Wang", "Anthony", "a1wang@ucsd.edu"),
    "bchester@ucsd.edu": Mentor("Bradley", "Chester", "Bradley", "bchester@ucsd.edu"),
    "cachiu@ucsd.edu": Mentor("Aerin", "Chiu", "Aerin", "cachiu@ucsd.edu"),
    "ehcho@ucsd.edu": Mentor("Esther", "Cho", "Esther", "ehcho@ucsd.edu"),
    "gxcheng@ucsd.edu": Mentor("Grant", "Cheng", "Grant", "gxcheng@ucsd.edu"),
    "jjose@ucsd.edu": Mentor("Jared", "Jose", "Jared J", "jjose@ucsd.edu"),
    "jsimpauco@ucsd.edu": Mentor("Jared", "Simpauco", "Jared S", "jsimpauco@ucsd.edu"),
    "jlk004@ucsd.edu": Mentor("Jeannie", "Kim", "Jeannie", "jlk004@ucsd.edu"),
    "j7bui@ucsd.edu": Mentor("Jett", "Bui", "Jett", "j7bui@ucsd.edu"),
    "nnazeem@ucsd.edu": Mentor("Nihal", "Nazeem", "Nihal", "nnazeem@ucsd.edu"),
    "nseyoum@ucsd.edu": Mentor("Nola", "Seyoum", "Nola", "nseyoum@ucsd.edu"),
    "rurioste@ucsd.edu": Mentor("Raul", "Uriostegui", "Raul", "rurioste@ucsd.edu"),
    "rkafle@ucsd.edu": Mentor("Richa", "Kafle", "Richa", "rkafle@ucsd.edu"),
    "sil045@ucsd.edu": Mentor("Sizhe", "Li", "Steven", "sil045@ucsd.edu")
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


def in_voice_channel(ctx):  # check to make sure ctx.author.voice.channel exists
    return ctx.author.voice and ctx.author.voice.channel


def chunks(l, n):
    """Yield n number of striped chunks from l."""
    for i in range(0, n):
        yield l[i::n]


def has_role(guild, member, **kwargs):
    role = get(guild.roles, **kwargs)
    return role in member.roles


def full_group_by(l, key=lambda x: x):
    d = defaultdict(list)
    for item in l:
        d[key(item)].append(item)
    return d.items()


###########
# THE BOT #
###########

# Custom Bot class to override close
class Bot(commands.Bot):
    async def close(self):
        state.close()
        await super().close()

intents = discord.Intents.default()
intents.members = True

bot = Bot("!", intents=intents)
bot.remove_command("help")


@bot.event
async def on_ready():
    activity = discord.Game(name="Dodging the spam flag")
    # activity = discord.Activity(
    #     type=discord.ActivityType.watching, name="your every move"
    # )
    await bot.change_presence(activity=activity)
    print("Bot is ready!")


################
# VERIFY STATE #
################


def fmt_students():
    res = ""
    for s in students.values():
        res += "{}\t{}\t{}\t{}".format(
            s.preferred,
            "\t".join([x.preferred for x in s.partners(students)]),
            "-".join([mentee.first for mentee in s.mentors(mentors)]),
            s.instr,
        )
        res += "\n"

    return res


def fmt_state():
    res = ""
    for uid, email in state["student_map"].items():
        s = students[email]
        res += "{}\t{}\t{}\t{}\t{}".format(
            s.preferred,
            uid,
            "\t".join([x.preferred for x in s.partners(students)]),
            "-".join([mentee.first for mentee in s.mentors(mentors)]),
            s.instr,
        )
        res += "\n"

    return res

@bot.command("verifyroster")
@commands.has_role(mentor_role_name)
async def verify_roster(ctx):
    await ctx.send("```\n" + fmt_students() + "```")

@bot.command("verifystate")
@commands.has_role(mentor_role_name)
async def verify_state(ctx):
    print("```\n" + fmt_state() + "```")


##############
# ONBOARDING #
##############

@bot.event
async def on_member_join(member):
    if member.id not in state["student_map"]:
        await join(member)

# for testing
@bot.command(name="verify")
# @commands.has_role(mentor_role)
async def testjoin(ctx):
    if ctx.message.author.id not in state["student_map"]:
        await join(ctx.message.author)


async def join(member):
    print("Verifying student...")

    intro = """
Yo yo yo! Welcome to SPIS 2022. I'm **SPISBot**, an automated bot here to help manage and moderate the SPIS 2022 Discord!

For now, I'm here to help welcome you to the SPIS 2022 Discord server. You'll notice that as of right now, you can't type in any of the channels. Don't worry; this is so that we can protect ourselves against random people from joining our server, and so that we can verify who you are before you can talk in the Discord. Before you can get started and hang out with everyone else, I need to know who you are first.

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
**Please send me your `@ucsd.edu` email:**
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
            await member.send(msg)
        elif s.email in state["student_map"].values():
            msg = "A SPIS student with that email already exists... please try again (and/or check your spelling)!"
            await member.send(msg)
        else:
            break

        message = await bot.wait_for("message", check=email_check)
        s = students.get(message.content)

    # We found an email!
    # Preemptively add it to the student map
    state["student_map"][message.author.id] = s.email
    # Send back the user info so that they can verify it's correct
    msg = """
Thanks for the info! I found someone with a matching email. Please confirm that this person is you by clicking one of the buttons below this message.

_If the preferred name is incorrect, just let your mentor know and we'll fix it after opening day._
"""

    embed = discord.Embed(title="Student info confirmation", description=msg)
    embed.add_field(name="Name", value=f"{s.first} {s.last}")
    embed.add_field(name="Preferred name", value=f"{s.preferred}")
    embed.add_field(name="Email", value=s.email)

    components = ActionRow(
        Button(
            label="This is me!",
            custom_id="confirm_identity",
            emoji="✅",
            style=ButtonColor.green
        ),
        Button(
            label="This isn't me!",
            custom_id="deny_identity",
            emoji="❌",
            style=ButtonColor.red
        )
    )

    reply = await member.send(embed=embed, components=components)

    # The wait_for returns when *any* reaction is added anywhere; we have to make sure that
    # we're reacting to the correct message
    def check(i: discord.Interaction, b: discord.ButtonClick):
        return (
            i.author == member
            and i.message == reply
            and (b.custom_id == "confirm_identity" or b.custom_id == "deny_identity")
        )

    interaction, button = await bot.wait_for("button_click", check=check)
    user = interaction.author
    button_id = button.custom_id

    await interaction.edit(components=[])

    if button_id == "confirm_identity":
        # Confirmed!
        print(f"Verified {s.first} {s.last}!")

        # We first initialize their nickname
        # try so that it doesn't panic if we can't change nick (which won't
        # work for the server owner)
        try:
            await user.edit(nick=f"{s.preferred}")
        except:
            pass

        # We then create the roles and channels we need to create
        await init_roles(member)

        desc = f"""
Congrats! You've finished the first-time setup. It's nice to meet you, {s.preferred} :)

Now that we've verified who you are, you now have access to all of the text and voice chats in the Discord server. Eventually, we'll be showing you how to use all these different parts of the server through live walkthroughs and write-ups.

For now, you should read through the informational text channels we have on the server:

- <#1003016905289891921> has more information on what each of the channels in the Discord server is for.
- <#1003017006162907246> contains SPIS-wide announcements regarding assignment deadlines and other urgent info.
- <#1003020435442642995> is the go-to channel for any questions, urgent or otherwise, that you need answered.

Beyond that, all there is to do now is to **jump in and start getting to know your mentors and your fellow mentees!** Our general text chat for hanging out is (appropriately) called <#1003018705606803677>, so hop on and introduce yourself!

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
    if member == None:
        return;

    # Get the student
    s = students[state["student_map"][member.id]]

    # Get the group ident
    n = s.group_ident(students)

    # Get their mentor, if exists
    m = "-".join([mentee.first for mentee in s.mentors(mentors)]) if len(s.mentor_emails) != 0 else None
    

    # Make the student a Mentee
    await member.add_roles(get(member.guild.roles, name=mentee_role_name))

    # We need to create two roles:
    # pair-{min(s, p)}-{max(s, p)}
    # mentor-{mentor}
    pair_name = f"pair--{n}"
    pair_role = get(member.guild.roles, name=pair_name)
    pair_role = (
        await member.guild.create_role(name=pair_name, colour=discord.Color.purple())
        if not pair_role
        else pair_role
    )
    await member.add_roles(pair_role)

    # We also need to create a pair channel:
    labs = get(member.guild.categories, id=category_lab)

    if not get(member.guild.voice_channels, name=pair_name):
        nc = await member.guild.create_voice_channel(pair_name, bitrate=64000, user_limit=0, category=labs)
        await nc.set_permissions(member.guild.default_role, view_channel=False)
        await nc.set_permissions(
            get(member.guild.roles, name=professor_role_name), view_channel=True
        )
        await nc.set_permissions(
            get(member.guild.roles, name=mentor_role_name), view_channel=True
        )
        await nc.set_permissions(pair_role, view_channel=True)

    if m:
        mentor_name = f"mentor--{m}"
        mentor_role = get(member.guild.roles, name=mentor_name)
        mentor_role = (
            await member.guild.create_role(
                name=mentor_name, colour=discord.Color.dark_purple()
            )
            if not mentor_role
            else mentor_role
        )
        await member.add_roles(mentor_role)

        # And a mentor channel:
        mentor_cat = get(member.guild.categories, id=category_mentors)

        if not get(member.guild.voice_channels, name=mentor_name):
            nc = await member.guild.create_voice_channel(mentor_name, bitrate=64000, user_limit=0, category=mentor_cat)
            await nc.set_permissions(member.guild.default_role, view_channel=False)
            await nc.set_permissions(
                get(member.guild.roles, name=professor_role_name), view_channel=True
            )
            await nc.set_permissions(
                get(member.guild.roles, name=mentor_role_name), view_channel=True
            )
            await nc.set_permissions(mentor_role, view_channel=True)


###########
# TICKETS #
###########


def id_not_in_q(id):
    return id not in [
        x.creator_id for x in state["tickets"] if x.state != TicketState.DONE
    ]


async def add_ticket(creator, description, admin_roles):
    # Someone just asked for help. We need to add a ticket!
    t = Ticket(creator.id, description, TicketState.TODO, None)
    tid = len(state["tickets"]) + 1
    state["tickets"].append(t)

    embed = discord.Embed(
        title=f"#{tid}", description=description, color=discord.Color.red()
    )
    embed.add_field(name="Creator", value=f"<@!{creator.id}>", inline=True)
    if creator.id in state["student_map"]:
        for i, p in enumerate(
            students[state["student_map"][creator.id]].partners(students)
        ):
            embed.add_field(name=f"Partner {i}", value=p.preferred, inline=True)
    
    acceptButton = Button(label="Accept", custom_id="accept_ticket", emoji="🧑‍💻", style=ButtonColor.blurple)
    returnToQueue = Button(label="Return to Queue", custom_id="return_ticket", emoji="❌", style=ButtonColor.red)
    completeButton = Button(label="Complete", custom_id="finish_ticket", emoji="✅", style=ButtonColor.green)

    msg = await bot.get_channel(channel_mentor_queue).send(embed=embed, components=ActionRow(acceptButton, completeButton))

    # await msg.add_reaction("👍")
    # await msg.add_reaction("☑️")

    # Message user that their ticket was created
    # TODO: Add back after appeal
    await creator.send(
        "Your ticket was created! A list of all the tickets in the queue is in the `#ticket-queue` channel.",
        embed=embed
    )

    def _check(i: discord.Interaction, b: discord.ButtonClick):
        print("Checking", tid, b.custom_id, i.member)
        return (
            i.message == msg 
            and
            any([x in i.member.roles for x in admin_roles])
            and
            (
                (
                    b.custom_id == "accept_ticket" or b.custom_id == "return_ticket"
                    and i.member.id
                    not in [
                        x.mentor_id
                        for x in state["tickets"]
                        if x.state == TicketState.PROG
                    ]
                )
                or b.custom_id == "finish_ticket"
            )
        )

    resolved = False
    accepted = False
    while not resolved:
        print("In loop for ticket", tid)
        interaction, button = await bot.wait_for("button_click", check=_check)
        print("Received interaction for ticket", tid)
        user = interaction.member
        button_id = button.custom_id

        await interaction.defer()

        if button_id == "finish_ticket":
            print("Ticket", tid, "Finish")
            if not accepted:
                print("Ticket", tid, "Close")
                # Ticket closed without resolution
                t.state = TicketState.DONE
                resolved = True
                await msg.delete()

                # Message user that their ticket was closed
                closed_desc = f"Your ticket was closed without resolution by <@!{user.id}>. You can contact them directly via DM for more information."
                closed_embed = discord.Embed(
                    title=f"Ticket #{tid} closed", description=closed_desc
                )

                # TODO: Add back after appeal
                await creator.send(embed=closed_embed)

                return
            else:
                print("Ticket", tid, "Complete")
                # This ticket is complete!
                # Delete it and set its state accordingly
                t.state = TicketState.DONE
                resolved = True
                await msg.delete()

                # Message user that their ticket was closed
                resolved_desc = f"Your ticket was resolved by <@!{user.id}>."
                resolved_embed = discord.Embed(
                    title=f"Ticket #{tid} resolved", description=resolved_desc
                )

                # TODO: Add back after appeal
                await creator.send(embed=resolved_embed)

                return

        if accepted:
            print("Ticket", tid, "Return to queue")
            # This ticket isn't complete
            t.mentor_id = None
            accepted = False

            # Set its embed back to the original embed
            await msg.edit(embed=embed, components=ActionRow(acceptButton, completeButton))

            # Message user that their ticket was unaccepted
            unaccepted_desc = f"Your ticket could not be resolved by <@!{user.id}>. It has been added back to the queue."
            unaccepted_embed = discord.Embed(
                title=f"Ticket #{tid} unaccepted", description=unaccepted_desc
            )

            # TODO: Add back after appeal
            await creator.send(embed=unaccepted_embed)
        else:
            print("Ticket", tid, "Accept")
            # Accept this ticket
            t.mentor_id = user.id
            accepted = True

            if (
                hasattr(creator, "voice")
                and creator.voice is not None
                and creator.voice.channel is not None
            ):
                if user.voice is not None:
                    await user.move_to(creator.voice.channel)
                else:
                    voice_desc = f"Student <@!{creator.id}> is currently located in voice channel `{creator.voice.channel}.`"
                    voice_embed = discord.Embed(
                        title=f"Ticket #{tid} accepted", description=voice_desc
                    )
                    await user.send(embed=voice_embed)
            else:
                voice_desc = f"Student <@!{creator.id}> is not located in a voice channel."
                voice_embed = discord.Embed(
                    title=f"Ticket #{tid} accepted", description=voice_desc
                )
                await user.send(embed=voice_embed)

            # Notify student
            accept_desc = f"Your ticket has been accepted by <@!{user.id}>; you'll be receiving assistance from them shortly."
            accept_embed = discord.Embed(
                title=f"Ticket #{tid} accepted", description=accept_desc
            )
            # TODO: Add back after appeal
            await creator.send(embed=accept_embed)

            # Edit the original message to reflect the current mentor
            new_embed = discord.Embed(title=f"#{tid}", description=description)
            new_embed.add_field(name="Current mentor", value=f"<@!{user.id}>", inline=False)
            new_embed.add_field(name="Creator", value=f"<@!{creator.id}>", inline=True)
            if creator.id in state["student_map"]:
                for i, p in enumerate(
                    students[state["student_map"][creator.id]].partners(students)
                ):
                    new_embed.add_field(name=f"Partner {i}", value=p.preferred, inline=True)

            await msg.edit(embed=new_embed, components=ActionRow(returnToQueue, completeButton))
    

@bot.command(name="onduty")
@commands.has_role(mentor_role_name)
async def on_duty(ctx):
    duty_role = get(ctx.author.guild.roles, name="On Duty")
    await ctx.author.add_roles(duty_role)


@bot.command(name="offduty")
@commands.has_role(mentor_role_name)
async def off_duty(ctx):
    duty_role = get(ctx.author.guild.roles, name="On Duty")
    await ctx.author.remove_roles(duty_role)


@bot.command(name="cleartickets")
@commands.has_role(mentor_role_name)
async def clear_tickets(ctx):
    state["tickets"] = []

    await bot.get_channel(channel_mentor_queue).purge()

@bot.command(name="dumptickets")
@commands.has_role(mentor_role_name)
async def dump_tickets(ctx):
    print(state["tickets"])

#############
# BREAKOUTS #
#############


def breakout_ident():
    return "".join(random.choices("0123456789abcdef", k=3))


def breakout_prefix(ident):
    if ident is None:
        return "breakout-"
    else:
        return f"breakout--{ident}"


@commands.check(in_voice_channel)
@bot.command(name="recall")
@commands.has_role(mentor_role_name)
async def recall(ctx, ident=None):
    # We move everyone to the voice channel of the person who invoked recall
    for member in ctx.guild.members:
        if member.voice is not None and member.voice.channel is not None:
            await member.move_to(ctx.author.voice.channel)


@commands.check(in_voice_channel)
@bot.command(name="bkclose")
@commands.has_role(mentor_role_name)
async def bkclose(ctx, ident=None):
    # For each matching breakout channel:
    prefix = breakout_prefix(ident)
    for vc in ctx.guild.voice_channels:
        if vc.name.startswith(prefix):
            # We first move all its members to the VC of the person who
            # invoked recall.
            for member in vc.members:
                await member.move_to(ctx.author.voice.channel)

            # We then delete this channel.
            await vc.delete()


@commands.check(in_voice_channel)
@bot.command(name="breakout")
@commands.has_role(mentor_role_name)
async def breakout(ctx, arg=None):
    # arg is either a category (mentor, pair, etc.) or a number, denoting the max size of the randomly assigned breakout rooms
    if arg is None:
        embed = discord.Embed(
            title="Couldn't create breakouts",
            description="Please provide an argument to specify the number of breakouts (e.g. `!breakout 4`) or the category by which to create the breakouts (e.g. `!breakout mentor`, `!breakout pair`, or `!breakout prof`)",
            color=discord.Color.red(),
        )
        await ctx.send(embed=embed)
        return None

    # We create a random identifier for this breakout session
    prefix = breakout_prefix(ctx.author.nick)

    split_members = []

    # If dividing randomly:
    if arg.isdigit():
        groups = int(arg)
        members = ctx.author.voice.channel.members
        random.shuffle(members)

        mentees = [x for x in members if has_role(ctx.guild, x, name=mentee_role_name)]
        admins = [x for x in members if not has_role(ctx.guild, x, name=mentee_role_name)]

        split_mentees = list(chunks(mentees, groups))
        split_admins = list(chunks(admins, groups))

        split_members = [
            x + y for x, y in it.zip_longest(split_admins, split_mentees, fillvalue=[])
        ]

    elif arg == "pair" or arg == "mentor" or arg == "prof":
        members = ctx.author.voice.channel.members

        def groupfn(m):
            for role in m.roles:
                if role.name.startswith(f"{arg}--"):
                    return role.name

        split_members = full_group_by(members, key=groupfn)

    else:
        embed = discord.Embed(
            title="Couldn't create breakouts",
            description="Please provide a valid argument to specify the number of breakouts (e.g. `!breakout 4`) or the category by which to create the breakouts (e.g. `!breakout mentor`, `!breakout pair`, or `!breakout prof`)",
            color=discord.Color.red(),
        )
        await ctx.send(embed=embed)
        return

    for i, ms in enumerate(split_members):
        # Create a breakout channel
        breakout = get(ctx.guild.categories, id=category_breakout)

        vc = await ctx.guild.create_voice_channel(f"{prefix}-{i + 1}", bitrate=64000, user_limit=0, category=breakout)
        for m in ms:
            await m.move_to(vc)


##################
# TIMEOUT CORNER #
##################
@bot.command(name="timeout")
async def timeout(ctx, member: discord.Member, secs):
    timeout_channel = 869462241093771326
    c = discord.utils.get(ctx.guild.voice_channels, id=timeout_channel)

    if member.voice is not None and member.voice.channel is not None:
        og = member.voice.channel

        t_end = time.time() + float(secs)
        while time.time() < t_end:
            if member.voice is not None:
                await member.move_to(c)
                await asyncio.sleep(1)

        await member.move_to(og)


#########
# POLLS #
#########


@bot.command(name="poll")
async def start_poll(ctx, name=None, *args):
    if name is None:
        # Error out: Polls need a name
        embed = discord.Embed(
            title="Poll creation error",
            description="Polls must have a title! Specify a title like so: `!poll Title`",
            color=discord.Color.red(),
        )
        await ctx.send(embed=embed)
        return
    elif len(args) > 10:
        embed = discord.Embed(
            title="Poll creation error",
            description="Polls cannot have more than 10 options.",
            color=discord.Color.red(),
        )
        await ctx.send(embed=embed)
        return

    num_emojis = ["1⃣", "2⃣", "3⃣", "4⃣", "5⃣", "6⃣", "7⃣", "8⃣", "9⃣", "🔟"]
    hand_emojis = ["👍", "👎"]

    options = list(
        zip(num_emojis, args) if len(args) > 0 else zip(hand_emojis, ["Yes", "No"])
    )

    embed = discord.Embed(
        title=name,
        description="\n".join([f"{x} :: {y}" for x, y in options]),
        color=discord.Color.green(),
    )
    embed.set_author(name="New poll")
    embed.set_footer(text="Choose an option by reacting with the emojis below")

    poll = await ctx.send(embed=embed)

    # Add reactions
    for emoji, _ in options:
        await poll.add_reaction(emoji)


##################
# MISC. COMMANDS #
##################


@bot.command(name="help")
async def help(ctx):
    footer = "spisbot 2022-07-30 | https://github.com/CatFish47/spisbot"

    desc = """
spisbot is the custom-made robot designed to help manage the SPIS 2022 Discord server. While you can send me commands to make me do things, I'm also always sitting in the background to help welcome people to the SPIS server and manage queue tickets.

**General commands**

- `!help`: opens this menu, which shows information about the bot!
- `!emojify <text>`: turns some text into emojis :)
- `!wide`: when called as the comment on an image: widens the image :))
    
**Mentor commands**

- `!onduty`: add the "On Duty" role to show that you're on duty.
- `!offduty`: add the "Off Duty" role to show that you're off duty.
- `!breakout n`: create `n` breakout rooms, for example, `!breakout 2` creates `2` breakout rooms.
- `!breakout type`: create breakout rooms based on type specified. `mentor` divides based on Mentor and `prof` divides based on assigned Professor. 
- `!bkclose [ident]`: close breakout rooms with identifier `ident` if specified; closes all breakout rooms otherwise
- `!recall`: move all people in a Voice Channel to your current Voice Channel.

If you're trying to call any other commands, keep this in mind:

- You should probably ask before running a suspicious-looking command.
- You probably **shouldn't** run a command that starts with `sync` or `purge`.

"""
    embed = discord.Embed(title="spisbot help", description=desc)
    embed.set_footer(text=footer)

    await ctx.message.channel.send(embed=embed)



@bot.command("emojify")
async def emojify(ctx, arg):
    letters = [
        "🇦",
        "🇧",
        "🇨",
        "🇩",
        "🇪",
        "🇫",
        "🇬",
        "🇭",
        "🇮",
        "🇯",
        "🇰",
        "🇱",
        "🇲",
        "🇳",
        "🇴",
        "🇵",
        "🇶",
        "🇷",
        "🇸",
        "🇹",
        "🇺",
        "🇻",
        "🇼",
        "🇽",
        "🇾",
        "🇿",
    ]
    await ctx.send(" ".join([letters[ord(x) - 97] for x in arg.lower() if x.isalpha()]))


def what_doing(text):
    text = text.lower()
    return ("what are" in text or "what am" in text) and "doin" in text


"""@bot.event
async def on_message(message):
    # What are we doing?
    if message.author.id != bot.user.id:
        if message.channel.id == channel_need_help:
            admin_roles = [
                get(message.guild.roles, name=mentor_role),
                get(message.guild.roles, name=professor_role),
            ]
            if id_not_in_q(message.author.id):
                await add_ticket(message.author, message.content, admin_roles)

    await bot.process_commands(message)
"""

@bot.listen("on_message")
async def process_tickets(message):
    if message.author.id != bot.user.id:
        if message.channel.id == channel_need_help:
            admin_roles = [
                get(message.guild.roles, name=mentor_role_name),
                get(message.guild.roles, name=professor_role_name),
            ]
            if id_not_in_q(message.author.id):
                await add_ticket(message.author, message.content, admin_roles)

@bot.command("wide")
async def wide(ctx):
    attachment_url = ctx.message.attachments[0].url
    file_request = requests.get(attachment_url)
    with Image.open(io.BytesIO(file_request.content)) as im:
        imr = im.resize((im.size[0] * 5, im.size[1]))
        with io.BytesIO() as buf:
            imr.save(buf, format='PNG')
            buf.seek(0)
            await ctx.send(file=discord.File(buf, "wide.png"))

@bot.command("presence")
@commands.has_role(mentor_role_name)
async def presence(ctx, *args):
    status = args[-1]
    if hasattr(discord.Status, status):
        status = getattr(discord.Status, status)
        args = args[:-1]
    else:
        status = discord.Status.online
    
    await bot.change_presence(activity=discord.Game(name=" ".join(args)), status=status)
            
            
"""@bot.command("goodbye")
async def goodbye(ctx):
    message = '''
@everyone

```
It's been a long day without you, my friend
And I'll tell you all about it when I see you again
We've come a long way from where we began
Oh, I'll tell you all about it when I see you again
When I see you again...
```
'''
    await ctx.send(message)
"""

##################
# ADMIN COMMANDS #
##################

# Purge all messages from a channel
@bot.command(name="purge")
@commands.has_role(mentor_role_name)
async def purge(ctx, limit=10):
    if limit == None or int(limit) > 50:
        limit = 50
    await ctx.channel.purge(limit=int(limit))


@bot.command(name="rmuser")
@commands.has_role(mentor_role_name)
async def rm_user(ctx, uid):
    uid = int(uid)
    state["student_map"].pop(uid, None)

    m = await ctx.guild.fetch_member(uid)

    await m.remove_roles(*(m.roles))


@bot.command(name="adduser")
@commands.has_role(mentor_role_name)
async def add_user(ctx, uid, email):
    uid = int(uid)
    state["student_map"][uid] = email

    m = await ctx.guild.fetch_member(uid)

    await init_roles(m)


@bot.command(name="userinfo")
@commands.has_role(mentor_role_name)
async def user_info(ctx, uid):
    for k, v in state["student_map"].items():
        if str(k) == uid or v == uid:
            s = students[state["student_map"][int(uid)]] if str(k) == uid else students[v]

            embed = discord.Embed(title=f"{s.first} {s.last} ({s.preferred})")
            embed.add_field(name=mentor_role_name, value="-".join([mentee.first for mentee in s.mentors(mentors)]))
            embed.add_field(name="Email", value=s.email)
            embed.add_field(name="Instr", value=s.instr)
            embed.add_field(name="Group ident", value=s.group_ident(students))

            for i, p in enumerate(s.partners(students)):
                embed.add_field(name=f"Partner {i}", value=p.preferred)

            await ctx.send(embed=embed)
            return
    
    embed = discord.Embed(title="User not found")
    await ctx.send(embed=embed)


@bot.command(name="syncmentorchannels")
@commands.has_role(mentor_role_name)
async def sync_mentor_channels(ctx):
    for channel in ctx.guild.voice_channels:
        if channel.name.startswith("mentor--"):
            await channel.delete()

    mentors = get(ctx.guild.categories, id=category_mentors)
    for role in ctx.guild.roles:
        if role.name.startswith("mentor--"):

            if not get(ctx.guild.voice_channels, name=role):
                nc = await ctx.guild.create_voice_channel(role.name, bitrate=64000, user_limit=0, category=mentors)
                await nc.set_permissions(ctx.guild.default_role, view_channel=False)
                await nc.set_permissions(
                    get(ctx.guild.roles, name=professor_role_name), view_channel=True
                )
                await nc.set_permissions(
                    get(ctx.guild.roles, name=mentor_role_name), view_channel=True
                )
                await nc.set_permissions(role, view_channel=True)

    print("sync complete")

@bot.command(name="syncroles")
@commands.has_role(mentor_role_name)
async def sync_roles(ctx):
    # We first purge all roles
    for role in ctx.guild.roles:
        if role.name.startswith("pair--") or role.name.startswith("mentor--"):
            await role.delete()

    for channel in ctx.guild.voice_channels:
        if channel.name.startswith("pair--") or channel.name.startswith("mentor--"):
            await channel.delete()

    for channel in ctx.guild.text_channels:
        if channel.name.startswith("pair--") or channel.name.startswith("mentor--"):
            await channel.delete()

    # Remove Mentee role
    role = get(ctx.guild.roles, name=mentee_role_name)
    for m in ctx.guild.members:
        try:
            await m.remove_roles(role)
        except:
            print(f"Couldn't remove roles from {m}")

    # We then re-add everything based on our internal state and consts
    for disc_id in state["student_map"].keys():
        print(disc_id)
        print(await ctx.guild.fetch_member(disc_id))
        await init_roles(await ctx.guild.fetch_member(disc_id))

    print("sync complete")


@bot.command(name="purgeroles")
@commands.has_role(mentor_role_name)
async def purge_roles(ctx):
    print("Purging all roles")

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
    role_names = (mentee_role_name,)
    roles = tuple(get(ctx.guild.roles, name=n) for n in role_names)
    for m in ctx.guild.members:
        try:
            await m.remove_roles(*roles)
        except:
            print(f"Couldn't remove roles from {m}")

@bot.command(name="clearstudents")
@commands.has_role(mentor_role_name)
async def clear_students(ctx):
    state["student_map"] = {}

@bot.command(name="shutdown")
@commands.has_role(mentor_role_name)
async def shutdown(ctx):
    await bot.close()

bot.run(token)
