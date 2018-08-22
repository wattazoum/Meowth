import asyncio

import discord
from discord.ext import commands


from meowth import utils
from meowth import checks

class Tutorial:
    def __init__(self, bot):
        self.bot = bot

    async def wait_for_cmd(self, tutorial_channel, newbie, command_name):

        # build check relevant to command
        def check(c):
            if not c.channel == tutorial_channel:
                return False
            if not c.author == newbie:
                return False
            if c.command.name == command_name:
                return True
            return False

        # wait for the command to complete
        cmd_ctx = await self.bot.wait_for(
            'command_completion', check=check, timeout=300)

        return cmd_ctx

    def get_overwrites(self, guild, member):
        return {
            guild.default_role: discord.PermissionOverwrite(
                read_messages=False),
            member: discord.PermissionOverwrite(
                read_messages=True,
                send_messages=True,
                manage_channels=True),
            guild.me: discord.PermissionOverwrite(
                read_messages=True)
            }

    async def want_tutorial(self, ctx, config):
        report_channels = config['want']['report_channels']
        report_channels.append(ctx.tutorial_channel.id)

        await ctx.tutorial_channel.send(
            f"This server utilizes the **{ctx.prefix}want** command to help "
            "members receive push notifications about Pokemon they want! "
            "I create Discord roles for each Pokemon that people want, "
            "and @mentioning these roles will send a notification to "
            f"anyone who **{ctx.prefix}want**-ed that Pokemon!\n"
            f"Try the {ctx.prefix}want command!\n"
            f"Ex: `{ctx.prefix}want unown`")

        try:
            await self.wait_for_cmd(ctx.tutorial_channel, ctx.author, 'want')

            # acknowledge and wait a second before continuing
            await ctx.tutorial_channel.send("Great job!")
            await asyncio.sleep(1)

        # if no response for 5 minutes, close tutorial
        except asyncio.TimeoutError:
            await ctx.tutorial_channel.send(
                f"You took too long to complete the **{ctx.prefix}want** "
                "command! This channel will be deleted in ten seconds.")
            await asyncio.sleep(10)
            await ctx.tutorial_channel.delete()

            return False

        # clean up by removing tutorial from report channel config
        finally:
            report_channels.remove(ctx.tutorial_channel.id)

        return True

    async def wild_tutorial(self, ctx, config):
        report_channels = config['wild']['report_channels']
        report_channels[ctx.tutorial_channel.id] = 'test'

        await ctx.tutorial_channel.send(
            f"This server utilizes the **{ctx.prefix}wild** command to "
            "report wild spawns! When you use it, I will send a message "
            "summarizing the report and containing a link to my best "
            "guess of the spawn location. If the reported Pokemon has "
            "an associated role on the server, I will @mention the role "
            "in my message! Your report must contain the name of the "
            "Pokemon followed by its location. "
            "Try reporting a wild spawn!\n"
            f"Ex: `{ctx.prefix}wild magikarp some park`")

        try:
            await self.wait_for_cmd(ctx.tutorial_channel, ctx.author, 'wild')

            # acknowledge and wait a second before continuing
            await ctx.tutorial_channel.send("Great job!")
            await asyncio.sleep(1)

        # if no response for 5 minutes, close tutorial
        except asyncio.TimeoutError:
            await ctx.tutorial_channel.send(
                f"You took too long to complete the **{ctx.prefix}wild** "
                "command! This channel will be deleted in ten seconds.")
            await asyncio.sleep(10)
            await ctx.tutorial_channel.delete()
            return False

        # clean up by removing tutorial from report channel config
        finally:
            del report_channels[ctx.tutorial_channel.id]

        return True

    async def raid_tutorial(self, ctx, config):
        report_channels = config['raid']['report_channels']
        category_dict = config['raid']['category_dict']
        tutorial_channel = ctx.tutorial_channel
        prefix = ctx.prefix
        raid_channel = None

        # add tutorial channel to valid want report channels
        report_channels[tutorial_channel.id] = 'test'

        if config['raid']['categories'] == "region":
            category_dict[tutorial_channel.id] = tutorial_channel.category_id

        async def timeout_raid(cmd):
            await tutorial_channel.send(_(
                "You took too long to complete the **{prefix}{cmd}** "
                "command! This channel will be deleted in ten seconds.").format(prefix=prefix, cmd=cmd))
            await asyncio.sleep(10)
            await tutorial_channel.delete()
            del report_channels[tutorial_channel.id]
            del category_dict[tutorial_channel.id]
            if raid_channel:
                await raid_channel.delete()
                ctx.bot.loop.create_task(self.bot.expire_channel(raid_channel))
            return

        await tutorial_channel.send(_(
            "This server utilizes the **{prefix}raid** command to "
            "report raids! When you use it, I will send a message "
            "summarizing the report and create a text channel for "
            "coordination. \n"
            "The report must contain, in this order: The Pokemon (if an "
            "active raid) or raid level (if an egg), and the location;\n"
            "the report may optionally contain the weather (see "
            "**{prefix}help weather** for accepted options) and the "
            "minutes remaining until hatch or expiry (at the end of the "
            "report) \n\n"
            "Try reporting a raid!\n"
            "Ex: `{prefix}raid magikarp local church cloudy 42`\n"
            "`{prefix}raid 3 local church sunny 27`").format(prefix=prefix))

        try:
            while True:
                raid_ctx = await self.wait_for_cmd(
                    tutorial_channel, ctx.author, 'raid')

                # get the generated raid channel
                raid_channel = raid_ctx.raid_channel

                if raid_channel:
                    break

                # acknowledge failure and redo wait_for
                await tutorial_channel.send(_(
                    "Doesn't look like it worked. Make sure you're not "
                    "missing any arguments from your raid command and "
                    "try again."))

            # acknowledge and redirect to new raid channel
            await tutorial_channel.send(_(
                "Great job! Let's head into the new raid channel you just "
                "created: {raid_channel_mention}").format(raid_channel_mention=raid_channel.mention))
            await asyncio.sleep(1)

        # if no response for 5 minutes, close tutorial
        except asyncio.TimeoutError:
            await timeout_raid('raid')
            return False

        # post raid help info prefix, avatar, user
        helpembed = await utils.get_raid_help(
            ctx.prefix, ctx.bot.user.avatar_url)

        await raid_channel.send(_(
            "This is an example of a raid channel. Here is a list of "
            "commands that can be used in here:"), embed=helpembed)

        await raid_channel.send(_(
            "Try expressing interest in this raid!\n\n"
            "Ex: `{prefix}interested 5 m3 i1 v1` would mean 5 trainers: "
            "3 Mystic, 1 Instinct, 1 Valor").format(prefix=prefix))

        # wait for interested status update
        try:
            await self.wait_for_cmd(
                raid_channel, ctx.author, _('interested'))

        # if no response for 5 minutes, close tutorial
        except asyncio.TimeoutError:
            await timeout_raid(_('interested'))
            return False

        # acknowledge and continue with pauses between
        await asyncio.sleep(1)
        await raid_channel.send(_(
            "Great job! To save time, you can also use **{prefix}i** "
            "as an alias for **{prefix}interested**.").format(prefix=prefix))

        await asyncio.sleep(1)
        await raid_channel.send(_(
            "Now try letting people know that you are on your way!\n\n"
            "Ex: `{prefix}coming`").format(prefix=prefix))

        # wait for coming status update
        try:
            await self.wait_for_cmd(
                raid_channel, ctx.author, _('coming'))

        # if no response for 5 minutes, close tutorial
        except asyncio.TimeoutError:
            await timeout_raid(_('coming'))
            return False

        # acknowledge and continue with pauses between
        await asyncio.sleep(1)
        await raid_channel.send(_(
            "Great! Note that if you have already specified your party "
            "in a previous command, you do not have to again for the "
            "current raid unless you are changing it. Also, "
            "**{prefix}c** is an alias for **{prefix}coming**.").format(prefix=prefix))

        await asyncio.sleep(1)
        await raid_channel.send(_(
            "Now try letting people know that you have arrived at the "
            "raid!\n\n"
            "Ex: `{prefix}here`").format(prefix=prefix))

        # wait for here status update
        try:
            await self.wait_for_cmd(
                raid_channel, ctx.author, _('here'))

        # if no response for 5 minutes, close tutorial
        except asyncio.TimeoutError:
            await timeout_raid(_('here'))
            return False

        # acknowledge and continue with pauses between
        await asyncio.sleep(1)
        await raid_channel.send(_(
            "Good! Please note that **{prefix}h** is an alias for "
            "**{prefix}here**").format(prefix=prefix))

        await asyncio.sleep(1)
        await raid_channel.send(_(
            "Now try checking to see everyone's RSVP status for this "
            "raid!\n\nEx: `{prefix}list`").format(prefix=prefix))

        # wait for list command completion
        try:
            await self.wait_for_cmd(
                raid_channel, ctx.author, _('list'))

        # if no response for 5 minutes, close tutorial
        except asyncio.TimeoutError:
            await timeout_raid(_('list'))
            return False

        # acknowledge and continue with pauses between
        await asyncio.sleep(1)
        await raid_channel.send(_(
            "Awesome! Since no one else is on their way, try using the "
            "**{prefix}starting** command to move everyone on the "
            "'here' list to a lobby!").format(prefix=prefix))

        # wait for starting command completion
        try:
            await self.wait_for_cmd(
                raid_channel, ctx.author, _('starting'))

        # if no response for 5 minutes, close tutorial
        except asyncio.TimeoutError:
            await timeout_raid(_('starting'))
            return False

        # acknowledge and continue with pauses between
        await asyncio.sleep(1)
        await raid_channel.send(_(
            "Great! You are now listed as being 'in the lobby', where "
            "you will remain for two minutes until the raid begins. In "
            "that time, anyone can request a backout with the "
            "**{prefix}backout** command. If the person requesting is "
            "in the lobby, the backout is automatic. If it is someone "
            "who arrived at the raid afterward, confirmation will be "
            "requested from a lobby member. When a backout is confirmed, "
            "all members will be returned to the 'here' list.").format(prefix=prefix))

        await asyncio.sleep(1)
        await raid_channel.send(_(
            "A couple of notes about raid channels. Meowth has "
            "partnered with Pokebattler to give you the best counters "
            "for each raid boss in every situation. You can set the "
            "weather in the initial raid report, or with the "
            "**{prefix}weather** command. You can select the moveset "
            "using the reactions in the initial counters message. If "
            "you have a Pokebattler account, you can use **{prefix}set "
            "pokebattler <id>** to link them! After that, the "
            "**{prefix}counters**  command will DM you your own counters "
            "pulled from your Pokebox.").format(prefix=prefix))

        await asyncio.sleep(1)
        await raid_channel.send(_(
            "Last thing: if you need to update the expiry time, use "
            "**{prefix}timerset <minutes left>**\n\n"
            "Feel free to play around with the commands here for a while. "
            "When you're finished, type `{prefix}timerset 0` and the "
            "raid will expire.").format(prefix=prefix))

        # wait for timerset command completion
        try:
            await self.wait_for_cmd(
                raid_channel, ctx.author, _('timerset'))

        # if no response for 5 minutes, close tutorial
        except asyncio.TimeoutError:
            await timeout_raid('timerset')
            return False

        # acknowledge and direct member back to tutorial channel
        await raid_channel.send(_(
            "Great! Now return to {tutorial_channel_mention} to "
            "continue the tutorial. This channel will be deleted in "
            "ten seconds.").format(tutorial_channel_mention=tutorial_channel.mention))

        await tutorial_channel.send(_(
            "Hey {mention}, once I'm done cleaning up the "
            "raid channel, the tutorial will continue here!").format(mention=ctx.author.mention))

        await asyncio.sleep(10)

        # remove tutorial raid channel
        await raid_channel.delete()
        raid_channel = None
        del report_channels[tutorial_channel.id]

        return True

    async def research_tutorial(self, ctx, config):
        report_channels = config['research']['report_channels']
        report_channels[ctx.tutorial_channel.id] = 'test'

        await ctx.tutorial_channel.send(_(
            "This server utilizes the **{prefix}research** command to "
            "report field research tasks! There are two ways to use this "
            "command: **{prefix}research** will start an interactive "
            "session where I will prompt you for the task, location, and "
            "reward of the research task. You can also use "
            "**{prefix}research <pokestop>, <task>, <reward>** to "
            "submit the report all at once.\n\n"
            "Try it out by typing `{prefix}research`").format(prefix=ctx.prefix))

        # wait for research command completion
        try:
            await self.wait_for_cmd(
                ctx.tutorial_channel, ctx.author, 'research')

            # acknowledge and wait a second before continuing
            await ctx.tutorial_channel.send(_("Great job!"))
            await asyncio.sleep(1)

        # if no response for 5 minutes, close tutorial
        except asyncio.TimeoutError:
            await ctx.tutorial_channel.send(_(
                "You took too long to use the **{prefix}research** "
                "command! This channel will be deleted in ten seconds.").format(prefix=ctx.prefix))
            await asyncio.sleep(10)
            await ctx.tutorial_channel.delete()
            return False

        # clean up by removing tutorial from report channel config
        finally:
            del report_channels[ctx.tutorial_channel.id]

        return True

    async def team_tutorial(self, ctx):
        await ctx.tutorial_channel.send(_(
            "This server utilizes the **{prefix}team** command to "
            "allow members to select which Pokemon Go team they belong "
            "to! Type `{prefix}team mystic` for example if you are in "
            "Team Mystic.").format(prefix=ctx.prefix))

        # wait for team command completion
        try:
            await self.wait_for_cmd(
                ctx.tutorial_channel, ctx.author, _('team'))

            # acknowledge and wait a second before continuing
            await ctx.tutorial_channel.send(_("Great job!"))
            await asyncio.sleep(1)

        # if no response for 5 minutes, close tutorial
        except asyncio.TimeoutError:
            await ctx.tutorial_channel.send(_(
                "You took too long to use the **{prefix}team** command! "
                "This channel will be deleted in ten seconds.").format(prefix=ctx.prefix))
            await asyncio.sleep(10)
            await ctx.tutorial_channel.delete()
            return False

        return True

    @commands.group(name=_('tutorial'), invoke_without_command=True, help=_("""Launches an interactive tutorial session for Meowth.

        Meowth will create a private channel and initiate a
        conversation that walks you through the various commands
        that are enabled on the current server."""))
    async def tutorial(self, ctx):

        newbie = ctx.author
        guild = ctx.guild
        prefix = ctx.prefix

        # get channel overwrites
        ows = self.get_overwrites(guild, newbie)

        # create tutorial channel
        name = utils.sanitize_channel_name(newbie.display_name+"-tutorial")
        ctx.tutorial_channel = await guild.create_text_channel(
            name, overwrites=ows)
        await ctx.message.delete()
        await ctx.send(
            (_("Meowth! I've created a private tutorial channel for "
             "you! Continue in {channel}").format(channel=ctx.tutorial_channel.mention)),
            delete_after=20.0)

        # get tutorial settings
        cfg = self.bot.guild_dict[guild.id]['configure_dict']
        enabled = [k for k, v in cfg.items() if v.get('enabled', False)]

        await ctx.tutorial_channel.send(_(
            "Hi {author}! I'm Meowth, a Discord helper bot for "
            "Pokemon Go communities! I created this channel to teach you all "
            "about the things I can do to help you on this server! You can "
            "abandon this tutorial at any time and I'll delete this channel "
            "after five minutes. Let's get started!").format(author=ctx.author.mention))

        try:

            # start want tutorial
            if 'want' in enabled:
                completed = await self.want_tutorial(ctx, cfg)
                if not completed:
                    return

            # start wild tutorial
            if 'wild' in enabled:
                completed = await self.wild_tutorial(ctx, cfg)
                if not completed:
                    return

            # start raid
            if 'raid' in enabled:
                completed = await self.raid_tutorial(ctx, cfg)
                if not completed:
                    return

            # start exraid
            if 'exraid' in enabled:
                invitestr = ""

                if 'invite' in enabled:
                    invitestr = (_(
                        "The text channels that are created with this command "
                        "are read-only until members use the **{prefix}invite** "
                        "command.").format(prefix=prefix))

                await ctx.tutorial_channel.send(_(
                    "This server utilizes the **{prefix}exraid** command to "
                    "report EX raids! When you use it, I will send a message "
                    "summarizing the report and create a text channel for "
                    "coordination. {invitestr}\n"
                    "The report must contain only the location of the EX raid.\n\n"
                    "Due to the longer-term nature of EX raid channels, we won't "
                    "try this command out right now.").format(prefix=prefix, invitestr=invitestr))

            # start research
            if 'research' in enabled:
                completed = await self.research_tutorial(ctx, cfg)
                if not completed:
                    return

            # start team
            if 'team' in enabled:
                completed = await self.team_tutorial(ctx)
                if not completed:
                    return

            # finish tutorial
            await ctx.tutorial_channel.send(_(
                "This concludes the Meowth tutorial! "
                "This channel will be deleted in 30 seconds."))
            await asyncio.sleep(30)

        finally:
            await ctx.tutorial_channel.delete()

    @tutorial.command(name=_("want"), help=_("""Launches an tutorial session for the want feature.

        Meowth will create a private channel and initiate a
        conversation that walks you through the various commands
        that are enabled on the current server."""))
    @checks.feature_enabled('want')
    async def want(self, ctx):

        newbie = ctx.author
        guild = ctx.guild

        # get channel overwrites
        ows = self.get_overwrites(guild, newbie)

        # create tutorial channel
        name = utils.sanitize_channel_name(newbie.display_name+"-tutorial")
        ctx.tutorial_channel = await guild.create_text_channel(
            name, overwrites=ows)
        await ctx.message.delete()
        await ctx.send(
            (_("Meowth! I've created a private tutorial channel for "
             "you! Continue in {channel}").format(channel=ctx.tutorial_channel.mention)),
            delete_after=20.0)

        # get tutorial settings
        cfg = self.bot.guild_dict[guild.id]['configure_dict']

        await ctx.tutorial_channel.send(_(
            "Hi {author}! I'm Meowth, a Discord helper bot for "
            "Pokemon Go communities! I created this channel to teach you "
            "about the want command! You can abandon this tutorial at any time "
            "and I'll delete this channel after five minutes. "
            "Let's get started!").format(author=ctx.author.mention))

        try:
            await self.want_tutorial(ctx, cfg)
            await ctx.tutorial_channel.send(_(
                "This concludes the Meowth tutorial! "
                "This channel will be deleted in ten seconds."))
            await asyncio.sleep(10)
        finally:
            await ctx.tutorial_channel.delete()

    @tutorial.command(name=_("wild"), help=_("""Launches an tutorial session for the wild feature.

        Meowth will create a private channel and initiate a
        conversation that walks you through wild command."""))
    @checks.feature_enabled('wild')
    async def wild(self, ctx):

        newbie = ctx.author
        guild = ctx.guild

        # get channel overwrites
        ows = self.get_overwrites(guild, newbie)

        # create tutorial channel
        name = utils.sanitize_channel_name(newbie.display_name+"-tutorial")
        ctx.tutorial_channel = await guild.create_text_channel(
            name, overwrites=ows)
        await ctx.message.delete()
        await ctx.send(
            (_("Meowth! I've created a private tutorial channel for "
             "you! Continue in {channel}").format(channel=ctx.tutorial_channel.mention)),
            delete_after=20.0)

        # get tutorial settings
        cfg = self.bot.guild_dict[guild.id]['configure_dict']

        await ctx.tutorial_channel.send(_(
            "Hi {author}! I'm Meowth, a Discord helper bot for "
            "Pokemon Go communities! I created this channel to teach you "
            "about the wild command! You can abandon this tutorial at any time "
            "and I'll delete this channel after five minutes. "
            "Let's get started!").format(author=ctx.author.mention))

        try:
            await self.wild_tutorial(ctx, cfg)
            await ctx.tutorial_channel.send(_(
                "This concludes the Meowth tutorial! "
                "This channel will be deleted in ten seconds."))
            await asyncio.sleep(10)
        finally:
            await ctx.tutorial_channel.delete()

    @tutorial.command(name=_("raid"), help=_("""Launches an tutorial session for the raid feature.

        Meowth will create a private channel and initiate a
        conversation that walks you through the raid commands."""))
    @checks.feature_enabled('raid')
    async def raid(self, ctx):

        newbie = ctx.author
        guild = ctx.guild

        # get channel overwrites
        ows = self.get_overwrites(guild, newbie)

        # create tutorial channel
        name = utils.sanitize_channel_name(newbie.display_name+"-tutorial")
        ctx.tutorial_channel = await guild.create_text_channel(
            name, overwrites=ows)
        await ctx.message.delete()
        await ctx.send(
            (_("Meowth! I've created a private tutorial channel for "
             "you! Continue in {channel}").format(channel=ctx.tutorial_channel.mention)),
            delete_after=20.0)

        # get tutorial settings
        cfg = self.bot.guild_dict[guild.id]['configure_dict']

        await ctx.tutorial_channel.send(_(
            "Hi {author}! I'm Meowth, a Discord helper bot for "
            "Pokemon Go communities! I created this channel to teach you "
            "about the raid command! You can abandon this tutorial at any time "
            "and I'll delete this channel after five minutes. "
            "Let's get started!").format(author=ctx.author.mention))

        try:
            await self.raid_tutorial(ctx, cfg)
            await ctx.tutorial_channel.send(_(
                "This concludes the Meowth tutorial! "
                "This channel will be deleted in ten seconds."))
            await asyncio.sleep(10)
        finally:
            await ctx.tutorial_channel.delete()

    @tutorial.command(name=_('research'), help=_("""Launches an tutorial session for the research feature.

        Meowth will create a private channel and initiate a
        conversation that walks you through the research command."""))
    @checks.feature_enabled('research')
    async def research(self, ctx):

        newbie = ctx.author
        guild = ctx.guild

        # get channel overwrites
        ows = self.get_overwrites(guild, newbie)

        # create tutorial channel
        name = utils.sanitize_channel_name(newbie.display_name+"-tutorial")
        ctx.tutorial_channel = await guild.create_text_channel(
            name, overwrites=ows)
        await ctx.message.delete()
        await ctx.send(
            (_("Meowth! I've created a private tutorial channel for "
             "you! Continue in {channel}").format(channel=ctx.tutorial_channel.mention)),
            delete_after=20.0)

        # get tutorial settings
        cfg = self.bot.guild_dict[guild.id]['configure_dict']

        await ctx.tutorial_channel.send(_(
            "Hi {author}! I'm Meowth, a Discord helper bot for "
            "Pokemon Go communities! I created this channel to teach you "
            "about the research command! You can abandon this tutorial at "
            "any time and I'll delete this channel after five minutes. "
            "Let's get started!").format(author=ctx.author.mention))

        try:
            await self.research_tutorial(ctx, cfg)
            await ctx.tutorial_channel.send(_(
                "This concludes the Meowth tutorial! "
                "This channel will be deleted in ten seconds."))
            await asyncio.sleep(10)
        finally:
            await ctx.tutorial_channel.delete()

    @tutorial.command(name=_("team"), help=_("""Launches an tutorial session for the team feature.

        Meowth will create a private channel and initiate a
        conversation that walks you through the team command."""))
    @checks.feature_enabled('team')
    async def team(self, ctx):


        newbie = ctx.author
        guild = ctx.guild

        # get channel overwrites
        ows = self.get_overwrites(guild, newbie)

        # create tutorial channel
        name = utils.sanitize_channel_name(newbie.display_name+"-tutorial")
        ctx.tutorial_channel = await guild.create_text_channel(
            name, overwrites=ows)
        await ctx.message.delete()
        await ctx.send(
            (_("Meowth! I've created a private tutorial channel for "
             "you! Continue in {channel}").format(channel=ctx.tutorial_channel.mention)),
            delete_after=20.0)

        await ctx.tutorial_channel.send(_(
            "Hi {author}! I'm Meowth, a Discord helper bot for "
            "Pokemon Go communities! I created this channel to teach you "
            "about the team command! You can abandon this tutorial at any time "
            "and I'll delete this channel after five minutes. "
            "Let's get started!").format(author=ctx.author.mention))

        try:
            await self.team_tutorial(ctx)
            await ctx.tutorial_channel.send(_(
                "This concludes the Meowth tutorial! "
                "This channel will be deleted in ten seconds."))
            await asyncio.sleep(10)
        finally:
            await ctx.tutorial_channel.delete()

def setup(bot):
    bot.add_cog(Tutorial(bot))
