from discord.ext import commands
from discord import Emoji, Role, Message, TextChannel, HTTPException, Member, Reaction, Forbidden, InvalidArgument
from json import load, dump, dumps  # for reading and writing to json files
from typing import Union, Dict, Optional, List
# Union[int, str] = either an integer or a string
# Dict[int, str] = dictionary in this format {integer key: string value}
from asyncio import create_task  # for executing something later


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
        bot.loop.create_task(self.load_settings())
        # NOTE: since the settings are loaded later, it's possible that someone could react
        # before it finishes loading but after the bot is ready
        # I chose to execute later to avoid blocking other cogs loading

    async def get_menu(self) -> Optional[Message]:
        """
        ### (method) get_menu()
        Get the bound menu.

        ### Returns
            `Discord.Message`:
                The Message object if it was successfully retrieved.
        """
        # make sure that the ids are set
        if not all((self._menu_msg_id, self._menu_chan_id)):
            return None

        channel: TextChannel = self.bot.get_channel(self._menu_chan_id)
        if not channel:  # the channel may fail to be retrieved
            return None

        # attempt to get the message
        try:
            return await channel.fetch_message(self._menu_msg_id)
        except HTTPException:  # failed to get message due to a Forbidden or NotFound response
            return None

    async def load_settings(self):
        """
        ### (method) load_settings()
        Load the currently saved `reaction_roles` dict and IDs for `role_menu`.
        Verify that `role_menu` still exists.
        """
        # read settings from the file
        with open("./text_files/reaction_roles.json", "r") as file:
            saved_settings = load(file)
            self._menu_msg_id = int(saved_settings["menu_msg_id"])
            self._menu_chan_id = int(saved_settings["menu_chan_id"])
            self.reaction_roles = {int(e_id): int(r_id) for e_id, r_id in
                                   saved_settings["reaction_role_ids"].items()}

        # verify the message
        # wait until the bot is ready or else `get_channel` will fail
        await self.bot.wait_until_ready()
        menu = await self.get_menu()
        # unbind the menu if it doesn't exist anymore
        if not menu:
            self._menu_msg_id, self._menu_chan_id = None, None

    async def save_settings(self):
        """
        ### (method) save_settings()
        Save the current `reaction_roles` dict and the IDs for the `role_menu`

        NOTE: accuracy could be traded off for performance by saving with a `discord.ext.tasks.Loop`
        instead of saving on each settings update
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

    @property
    def emotes(self) -> List[Emoji]:
        """
        ### (property) emotes()
        Convert the emote IDs in `reaction_roles` to Emoji instances

        ### Returns
            `List[Emoji]`:
                The Emojis
        """
        return list(filter(  # remove failed requests
            None,
            [self.bot.get_emoji(id) for id in self.reaction_roles]
        ))

    @commands.command(aliases=["BM"])
    # Discord will convert a message ID or link to a Message object
    async def bind_message(self, ctx: commands.Context, message: Message):
        """Set up the role menu message. Pass in a message ID or link.
        NOTE: if the bot can't see the channel anymore, it may throw 'No bound message' errors"""
        # check if already bound
        if self._menu_msg_id:
            return await ctx.send("Please unbind the current message first.")

        # bind the message
        try:
            # save the message and channel id
            self._menu_msg_id, self._menu_chan_id = message.id, message.channel.id
            # set up the reactions
            # the list comp. retrieves the emote objects
            for emote in self.emotes:
                await message.add_reaction(emote)
            await ctx.send("Successfully bound the message.")

            # save the new stuff
            create_task(self.save_settings())
        except:  # you can add better error handling logic here
            await ctx.send("Failed to bind to the message.")

    @commands.command(aliases=["UM"])
    async def unbind_message(self, ctx: commands.Context):
        """Unbind the currently bound message."""
        # check that there is a bound message
        if not self._menu_msg_id:
            return await ctx.send("There is no bound message. Bind one with `bind_message`.")
        # remove the current message
        self._menu_msg_id, self._menu_chan_id = None, None
        await ctx.send("Menu removed")

        # save the new stuff
        create_task(self.save_settings())

    @bind_message.error
    async def binding_error_handler(self, ctx: commands.Context, error):
        """Handle an invalid argument when (un)binding a message"""
        if isinstance(error, commands.BadArgument):
            # >={ at the user
            return await ctx.send("I can't see that message, "
                                  "or you haven't passed a message ID or link")
        elif isinstance(error, commands.MissingRequiredArgument):
            # one of the arguments was missed out
            return await ctx.send(f"I need more arguments. Missed argument: {error.param}")
        else:
            return await ctx.send("Internal error")

    @commands.command(aliases=["ARR"])  # register this function as a command
    async def add_reaction_role(self, ctx: commands.Context,  # the channel, invoker, etc
                                # discord will attempt to convert it to a role
                                role: Union[int, Role],
                                emoji: Emoji):
        """Add a new reaction role. You may pass mentions or ids for roles."""
        # get the id
        role_id = role if isinstance(role, int) else role.id
        emoji_id = emoji if isinstance(emoji, int) else emoji.id

        # check that they're not already registered
        if emoji_id in self.reaction_roles.keys() or role_id in self.reaction_roles.values():
            return await ctx.send("That emoji or role is already registered. "
                                  "Unregister it with `remove_reaction_role`")

        # check that role_menu_message has been assigned
        menu = await self.get_menu()
        if not menu:
            return await ctx.send("Bind a message with `bind_message` before using this command.")

        # register the role and set up the reaction
        self.reaction_roles[emoji_id] = role_id
        try:
            await menu.add_reaction(emoji)
        except Forbidden:  # bot doesn't have permissions to react on the message
            return await ctx.send("Reaction failed. Check my permissions and retry.")
        await ctx.send(f"I have added {emoji} as the reaction for the "
                       f"{ctx.guild.get_role(role_id)} role.")

        # save the new reaction_roles
        create_task(self.save_settings())

    @commands.command(aliases=["RRR"])
    async def remove_reaction_role(self, ctx, emoji: Emoji):
        """Remove a reaction role by its emoji."""
        # get the id
        emoji_id = emoji.id

        # check that they're not already registered
        if emoji_id not in self.reaction_roles.keys():
            return await ctx.send("That emoji or role isn't registered. "
                                  "Register it with `add_reaction_role`")

        # check that role_menu_message has been assigned
        menu = await self.get_menu()
        if not menu:
            return await ctx.send("Bind a message with `bind_message` before using this command.")

        # register the role and set up the reaction
        # for outputting the role name for the user
        role_id = self.reaction_roles[emoji_id]
        del self.reaction_roles[emoji_id]
        try:
            await menu.remove_reaction(emoji, self.bot.user)
        except Forbidden:  # bot doesn't have permissions to react on the message
            return await ctx.send("Reaction failed. Check my permissions and retry.")
        await ctx.send(f"I have removed {emoji} as the reaction for the {menu.guild.get_role(role_id)} role.")

        # save the new reaction_roles
        create_task(self.save_settings())

    @add_reaction_role.error
    @remove_reaction_role.error
    async def add_reaction_role_error_handler(self, ctx, error):
        """Give the user feedback if their arguments are shit."""
        if isinstance(error, commands.BadUnionArgument):
            # >={ at the user
            return await ctx.send(">={ I don't understand your arguments. "
                                  "Please use `help add_reaction_role`")

        elif isinstance(error, commands.MissingRequiredArgument):
            # one of the arguments was missed out
            return await ctx.send(f"I need more arguments. Missed argument: {error.param}")

        elif isinstance(error.original, InvalidArgument):
            return await ctx.send("I suspect that is not an emoji ID")

        else:  # unhandled error
            return await ctx.send("Internal error")  # fix your command cunt

    @commands.command(aliases=["CU"])
    async def current_menu(self, ctx):
        """Get the currently bound menu."""
        menu = await self.get_menu()
        if not menu:
            return await ctx.send("No bound menu. Bind one with `bind_message`")
        url = menu.jump_url
        await ctx.send(url)

    @commands.command(aliases=["check_perms", "cp"])
    async def check_permissions(self, ctx):
        """Check if I have sufficient permissions for adding reactions to the menu
        and adding roles."""
        reasons = []
        # check if the menu can be seen
        menu = await self.get_menu()
        if not menu:
            reasons.append("- I can't see the menu")

        # check if the menu can be reacted on
        chan_perms = ctx.me.permissions_in(menu.channel)
        if not chan_perms.add_reactions:
            reasons.append("- I can't react on the menu")

        # check if roles can be managed
        guild_perms = ctx.me.guild_permissions
        if not guild_perms.manage_roles:
            reasons.append("- I can't manage roles")

        # check if any of the roles are higher than the bot's highest role
        # you can't add roles that are higher than yours
        top_role_index = ctx.me.top_role.position
        for role in [ctx.guild.get_role(r_id) for r_id in self.reaction_roles.values()]:
            if top_role_index < role.position:
                reasons.append(
                    "- One or more of the reaction roles is above my top role")

        # send all the problems (if any)
        if not reasons:
            return await ctx.send("I have all the permissions I need :)")
        await ctx.send("\n".join(reasons))

    @commands.command(aliases=["SRR"])
    async def show_reaction_roles(self, ctx):
        """Show the current reaction roles."""
        # get all the names of the roles and emotes
        names = {}
        for e_id, r_id in self.reaction_roles.items():
            emote, role = self.bot.get_emoji(e_id), ctx.guild.get_role(r_id)
            if not all((emote, role)):  # check for failure to get either object
                continue
            names[emote.name] = role.name

        await ctx.send("Format: {emoji name : role name}\n"
                       + dumps(  # dumps for pretty JSON printing
                           names,
                           indent=4,
                           default=str,
                       )
                       )

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction: Reaction, person: Member):
        """
        ### (method) on_reaction_add(emote, person, )
        Check if the reaction was a role reaction, if so give the role.
        NOTE: this will not work for menus that were added before the bot was restarted.
              E.G you bind 758629659629584435, restart the bot, then react to it: it won't see the reaction event
              This is because that message isn't in the cache.

        ### Parameters
            - `reaction`: `Reaction`
                The reaction that was added to a message
            - `person`: `Member`
                The person who reacted
        """
        # ignore self
        if person == self.bot.user:
            return

        # NOTE: the menu is retrieved every time to make sure the message exists still
        # and that the bot still has permissions to see it
        menu = await self.get_menu()
        if not menu:  # the menu couldn't be retrieved
            return
        # check if the menu was reacted on
        if reaction.message.id != menu.id:
            return

        # check if the emote is registered
        role_id: Optional[int] = self.reaction_roles.get(reaction.emoji.id)
        if not role_id:
            return

        # check if the role still exists
        role = menu.guild.get_role(role_id)
        if not role:  # unbind the role if it's gone
            del self.reaction_roles[reaction.emoji.id]
            create_task(self.save_settings())
            return

        # attempt to add the role
        try:
            await person.add_roles(
                role,
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
