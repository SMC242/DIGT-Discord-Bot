# DIGT-Discord-Bot

A Discord bot for DIGT (a Planetside 2 outfit on the Miller server's VS faction). Made by [DTWM] benmitchellmtbV5.

[Repo](https://github.com/SMC242/DIGT-Discord-Bot "DIGT Discord Bot repository on GitHub")

## Using this bot

Knaroef will have to generate and provide a bot token from the [Discord Developer Portal](https://discord.com/developers/applications "Developer portal"). Said token should be put into a file called `token.txt` in `secrets/`.

If running an uncompiled version of the bot (`.py`), you will need to open a terminal, `cd` into this directory, and run `py -m pip install -r ./text_files/requirements.txt` to install the dependencies. After that, run `main.py` and it should work. If you are using a compiled version (`.pyc`), you can run `main.pyc`.

## Maintaining this bot

### What does each file and folder do?

- `Extensions/`: These are hot-swappable components of the bot
- `secrets/`: Contains stuff that shouldn't be on the repo.
- `Utils/`: Modules that are used to make extensions but are not purely part of one extension
- `main.py`: Run this script to start the bot. Also contains admin commands
