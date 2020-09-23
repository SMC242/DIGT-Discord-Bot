import os  # for loading the extensions
from discord.ext.commands import Bot, is_owner
from discord import Activity, ActivityType, AllowedMentions
from traceback import print_exc  # for error logging
from datetime import datetime  # for timestamps
from sys import exit  # for closing the script gracefully

# constants
# used to have different behaviour when testing to avoid causing problems for the active version
DEV_VERSION = True

# instantiate the bot
description = """This bot was designed for the DIGT Discord by [DTWM] benmitchellmtbV5.
GitHub repo:  https://github.com/SMC242/DIGT-Discord-Bot"""
bot = Bot(
    # command prefix changes depending on DEV_VERSION
    "devt!" if DEV_VERSION else "silent_t!",
    description=description,
    owner_ids=(
        395598378387636234,  # [DTWM] benmitchellmtbV5
        106982816276848640,  # [DIGT] Knaroef
    ),
    activity=Activity(
        # have a different status if currently testing
        name=f"Starting...{' [TESTING]' if DEV_VERSION else ''}",
        type=ActivityType.playing,
    ),
    case_insensitive=True,
    allowed_mentions=AllowedMentions(  # Discord will avoid mass ping injections
        everyone=False,
        roles=False,
        users=True,
    )
)
# load all extensions
for file in os.listdir("./Extensions"):
    # Assume all Python files in Extensions are extensions
    if not file.endswith(".py"):
        continue
    ext_name = file[:-3]
    # ignore __init__ because it's not a Cog but it must be in the directory
    if ext_name == "__init__":
        continue
    try:
        bot.load_extension(f"Extensions.{ext_name}")
        print(f"Extension ({ext_name}) loaded sucessfully")
    except:
        print(f"Extension ({ext_name}) failed to load")
        # log loading errors
        print_exc()

# admin stuff


@bot.before_invoke
async def log_command_info(ctx):
    """Log information about each command call."""
    # get time info
    today = datetime.today()
    day = today.strftime("%d.%m.%Y")
    time = today.strftime("%H:%M")
    print(
        f'Command: {ctx.command.qualified_name} called in "{ctx.guild.name}".{ctx.channel} on {day} at {time}')


@bot.command()
@is_owner()
async def close(ctx):
    """End me rightly."""
    # shut down the bot
    await ctx.send("Shutting down...")
    print(f"Bot closed by @{ctx.author}")
    await bot.logout()
    # close the script
    exit(0)


# running the bot
@bot.listen()
async def on_ready():
    """Control the behaviour when the bot starts."""
    # acknowledge startup in the terminal
    print("I am ready.\n---")

    # warn user if they're on the dev version
    if DEV_VERSION:
        print("WARNING: you are on the dev version. Change main.DEV_VERSION to False if you're a user")

if __name__ == "__main__":
    # get the token and start the bot
    with open("./secrets/token.txt") as f:
        TOKEN = f.readline().strip("\n")
    bot.run(TOKEN)
