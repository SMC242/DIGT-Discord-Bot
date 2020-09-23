"""A global error handler for Cogs that don't implement their own error handlers."""

from discord.ext import commands
from discord import Forbidden
from typing import Union, Iterable
from fuzzywuzzy import process


def list_join(to_join: Iterable[str], connective: str = "and") -> str:
    """
    Join a list into a grammatically-correct string.
    ARGUMENTS
    to_join:
        The items to join together.
    connective:
        The connective to join the last two elements.
        Example where 'and' is connective:
        'one, two, three, four and five'
    """
    # ensure it's a list
    if not isinstance(to_join, list):
        to_join = list(to_join)
    return ', '.join(to_join[:-2] + [f' {connective} '.join(to_join[-2:])])


class ErrorHandler(commands.Cog):
    """Handles responding to erorrs raised by commands."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_command_error(self, ctx,
                               error: Union[commands.CommandError,
                                            commands.CheckFailure]):
        """Handle an exception raised during command invokation."""
        # Only use this error handler if the current context does not provide its
        # own error handler
        if hasattr(ctx.command, 'on_error'):
            return

        # Only use this error handler if the current cog does not implement its
        # own error handler
        if ctx.cog and commands.Cog._get_overridden_method(
                ctx.cog.cog_command_error) is not None:
            return

        # if command on cooldown
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f"Try again in {int(error.retry_after)} seconds!")

        # if command is unknown
        elif isinstance(error, commands.CommandNotFound):
            if '@' in ctx.invoked_with:
                await ctx.send("How dare you try to use me to annoy others!")
            else:
                # get close matches
                cmd_names = [cmd.name for cmd in self.bot.walk_commands()]
                suggestion = process.extractOne(ctx.invoked_with, cmd_names)[0]
                await ctx.send(f'Command not found "`{ctx.invoked_with}`" ' +
                               f"Did you mean `{ctx.prefix}{suggestion}`?")

        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"I need more arguments")

        elif isinstance(error, commands.MissingAnyRole):
            # create a grammatically correct list of the required roles
            # ensure it's a list for join()
            missing_roles = list(*error.missing_roles)
            await ctx.send("You need to be " +
                           f"{'an ' if missing_roles[0][0].lower() in 'aeiou' else 'a '}" +
                           f"{list_join(missing_roles, 'or')}" +
                           " to use that command!")

        elif isinstance(error, commands.DisabledCommand):
            await ctx.send(f"Command in maintenance.")

        elif isinstance(error, commands.NotOwner):
            await ctx.send("Only admins can use that command.")

        elif isinstance(error, commands.BadArgument):
            await ctx.send(f"I don't understand your argument.")

        elif isinstance(error, commands.UnexpectedQuoteError):
            await ctx.send(f"There was a weird quote in your command.")

        # if bot can't access the channel
        elif isinstance(error, Forbidden):
            await ctx.send("I can't access one or more of those channels TwT")

        # if a command is malfunctioning
        elif isinstance(error.original, AssertionError):
            await ctx.send(f"My diagnostics report a failure in {ctx.command.name}" +
                           "Please inform the admins.")

        # custom checks will handle their own failures
        elif isinstance(error, commands.CheckFailure):
            pass

        # if the error hasn't been handled
        else:
            # tell the user
            await ctx.send(f"Internal error.")

            print(error.original)


def setup(bot: commands.Bot):
    """Load the error handler into the bot"""
    bot.add_cog(ErrorHandler(bot))
