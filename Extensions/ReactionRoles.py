from discord.ext import commands
from discord import Emoji, Role, Message, TextChannel, HTTPException, Member, Reaction, Forbidden
from json import load, dump  # for reading and writing to
from typing import Union, Dict, Optional
# Union[int, str] = either an integer or a string
# Dict[int, str] = dictionary in this format {integer key: string value}


# Cogs are sets of commands or listeners that can be loaded into the bot
class ReactionRoles(commands.Cog):
    """Allows reaction menus for roles.
    NOTE: This was designed to be used for only 1 server.

    ### ATTRIBUTES
     - `reaction_roles (dict with int keys, int values): the emoji ids and their bound role ids.
        Format: {emoji_id: role_id}
     - `_menu_msg_id (int)`: the id of the bound message.
     - `_menu_chan_id (int)`: the id of the bound message's channel.
        This is needed to retrieve the message object.
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # the ids for the message that will have the reactions
        self._menu_msg_id: int = None
        self._menu_chan_id: int = None
        # dict with emoji ids as its keys keys and Role ids as their value
        self.reaction_roles: Dict[int, int] = {}

        # the settings are saved in text_files/reaction_roles.json for persistence
        with open("./text_files/reaction_roles.json", "r") as file:
            saved_settings = load(file)
            self._menu_msg_id = saved_settings["menu_msg_id"]
            self._menu_chan_id = saved_settings["menu_chan_id"]
            self.reaction_roles = saved_settings["reaction_role_ids"]

    async def get_menu(self) -> Optional[Message]:
        """
        ### (method) get_menu()
        Get the bound menu.

        ### Returns
            `Discord.Message`:
                The Message object if it was successfully retrieved.

        ### Raises
            ValueError: _menu_msg_id or _menu_chan_id isn't set
        """
        # make sure that the ids are set
        if not all((self._menu_msg_id, self._menu_chan_id)):
            raise ValueError(
                "Cannot get the menu without the channel and message id")

        channel: TextChannel = self.bot.get_channel(self._menu_chan_id)
        if not channel:  # the channel may fail to be retrieved
            return None

        # attempt to get the message
        try:
            msg = await channel.fetch_message()
        except HTTPException:
            return None

    async def save_settings(self):
        """
        ### (method) save_settings()
        Save the current `reaction_roles` dict and the IDs for the `role_menu`
        """
        # combine the channel and message IDs with the reaction roles
        to_save = {
            "menu_msg_id": self._menu_msg_id,
            "menu_chan_id": self._menu_chan_id,
            "reaction_role_ids": self.reaction_roles,
        }
        # open the file in write mode
        with open("./text_files/reaction_roles.json", "w") as file:
            dump(to_save, file)

    @commands.command()
    # Discord will convert a message ID or link to a Message object
    async def bind_message(self, ctx: commands.Context, message: Message):
        """Set up the role menu message. Pass in a message ID or link."""
        # check if already bound
        if self._menu_msg_id:
            return await ctx.send("Please unbind the current message first.")

        # bind the message
        try:
            # save the message and channel id
            self._menu_msg_id, self._menu_chan_id = message.id, message.channel.id
            # set up the reactions
            # retrieve the emote objects
            for emote in [self.bot.get_emoji(id) for id in self.reaction_roles.keys()]:
                await message.add_reaction(emote)
            await ctx.send("Successfully bound the message.")
        except:  # you can add better error handling logic here
            await ctx.send("Failed to bind to the message.")

    @commands.command()
    async def unbind_message(self, ctx: commands.Context):
        """Unbind the currently bound message."""
        # check that there is a bound message
        if not self._menu_msg_id:
            return await ctx.send("There is no bound message. Bind one with `bind_message`.")
        # remove the current message
        self._menu_msg_id, self._menu_chan_id = None, None

    @bind_message.error
    async def binding_error_handler(self, ctx: commands.Context, error):
        """Handle an invalid argument when (un)binding a message"""
        if isinstance(error, commands.BadArgument):
            # >={ at the user
            return await ctx.send(">={ Give me a message ID or link")

    @commands.command()  # register this function as a command
    async def add_reaction_role(self, ctx: commands.Context,  # the channel, invoker, etc
                                # discord will attempt to convert it to a role
                                role: Union[Role, int],
                                emoji: Union[Emoji, int]):
        """Add a new reaction role. You may pass mentions or ids for role and emoji"""
        # get the objects by id if ids were passed
        role_id = role if isinstance(role, int) else role.id
        emoji_id = emoji if isinstance(emoji, int) else emoji.id

        # check that they're not already registered
        if emoji_id in self.reaction_roles.keys() or role_id in self.reaction_roles.values():
            return await ctx.send("That emoji or role is already registered. "
                                  "Unregister it with `remove_reaction_role`")

        # check that role_menu_message has been assigned
        if not self._menu_msg_id:
            return await ctx.send("Bind a message with `bind_message` before using this command.")

        # register the role and set up the reaction
        self.reaction_roles[emoji_id] = role_id
        try:
            await self.role_menu_message.add_reaction(emoji)
        except Forbidden:  # bot doesn't have permissions to react on the message
            return await ctx.send("Reaction failed. Check my permissions and retry.")
        await ctx.send(f"I have added {emoji} as the reaction for the {role} role.")

    @add_reaction_role.error
    async def add_reaction_role_error_handler(ctx, error):
        """Give the user feedback if their arguments are shit."""
        if isinstance(error, commands.BadArgument):
            # >={ at the user
            return await ctx.send(">={ I don't understand your arguments")

        elif isinstance(error, commands.MissingRequiredArgument):
            # one of the arguments was missed out
            return await ctx.send(f"I need more arguments. Missed argument: {error.param}")

        elif isinstance(error, commands.CommandError):
            return await ctx.send("Internal error")  # fix your command cunt

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction: Reaction, person: Member):
        """
        ### (method) on_reaction_add(emote, person, )
        Check if the reaction was a role reaction, if so give the role

        ### Parameters
            - `reaction`: `Reaction`
                The reaction that was added to a message
            - `person`: `Member`
                The person who reacted
        """
        # ignore self
        if person == self.bot.user:
            return

        # make sure that the ids are set
        if not all((self._menu_msg_id, self._menu_chan_id)):
            return

        # NOTE: the menu is retrieved every time to make sure the message exists still
        # and that the bot still has permissions to see it
        menu = await self.get_menu()
        if not menu:  # the menu couldn't be retrieved
            return
        # check if the menu was reacted on
        if reaction.message != menu:
            return

        # check if the emote is registered
        role_id: Optional[int] = self.reaction_roles.get(reaction.emoji.id)
        if not role_id:
            return

        # attempt to add the role
        try:
            await person.add_roles(
                menu.guild.get_role(role_id),
                reason="Reacted on the role menu"
            )
        except Forbidden:  # bot doesn't have manage roles permissions
            return


def setup(bot: commands.Bot):
    """Load this extension into the bot."""
    cogs = (
        ReactionRoles(bot),
    )
    for cog in cogs:
        bot.add_cog(cog)
