import discord
from discord.ext import commands, tasks

from bracket_run_tracker import BracketRunTracker
from upset_tracker import UpsetTracker
from start_gg import StartGG


class TrackerBot(commands.Bot):

    def __init__(self, startgg_token: str):
        self._upset_tournies = {}
        self._player_tournies = {}
        self._startgg_token = startgg_token
        self._startgg_client = StartGG(startgg_token)

        intents = discord.Intents.default()
        intents.message_content = True

        commands.Bot.__init__(self, command_prefix='!', intents=intents, help_command=None)
        self.add_commands()

    async def on_ready(self):
        self.check_for_completed_tournies.start()

    def add_commands(self):
        @self.command(name="track", pass_context=True)
        async def track(ctx, arg1, arg2, arg3=None):
            event_data = self._startgg_client.show_event_metadata(arg1, arg3)
            if event_data is not None:
                if not event_data['complete']:
                    player_id = self._startgg_client.find_player_in_bracket(event_data['event_id'], arg2)
                    if player_id is not None:
                        if player_id not in self._player_tournies:
                            self._player_tournies[player_id] = {event_data['event_id']: BracketRunTracker(event_data['event_id'], player_id, event_data['tourney_name'], event_data['event_name'], self._startgg_client, ctx.channel)}
                        else:
                            if event_data['event_id'] not in self._player_tournies[player_id]:
                                self._player_tournies[player_id][event_data['event_id']] = BracketRunTracker(event_data['event_id'], player_id, event_data['tourney_name'], event_data['event_name'], self._startgg_client, ctx.channel)
                                await ctx.channel.send("Now tracking bracket run for player '{}' for event {} in {}".format(arg2, event_data['event_name'], event_data['tourney_name']))
                            else:
                                await ctx.channel.send("Already tracking this bracket for player '{}'".format(arg2))
                    elif player_id is None:
                        await ctx.channel.send("Player '{}' not found in bracket".format(arg2))
                    elif player_id in self._player_tournies:
                        await ctx.channel.send("Bot is already tracking this player in this bracket or another bracket")
                else:
                    await ctx.channel.send("Unable to track player '{}' in this bracket; the bracket is already complete".format(arg2))
            else:
                await ctx.channel.send("Unable to find event in tourney. Please check your spelling or type !help for help on formatting.")

        @self.command(name="untrack", pass_context=True)
        async def untrack_player(ctx, arg1, arg2, arg3):
            event_data = self._startgg_client.show_event_metadata(arg1, arg3)
            if event_data is not None:
                if arg2 in self._player_tournies and event_data['event_id'] in self._player_tournies[arg2]:
                    del self._player_tournies[arg2][event_data['event_id']]
                    if len(self._player_tournies[arg2].keys()) == 0:
                        del self._player_tournies[arg2]
                    await ctx.channel.send("Stopped tracking player '{}' for event {} in {}".format(arg2, event_data['event_name'], event_data['tourney_name']))
                elif arg2 not in self._player_tournies:
                    await ctx.channel.send("Not currently tracking this player")
                else:
                    await ctx.channel.send("Not currently tracking this event for player '{}'".format(arg2))
            else:
                await ctx.channel.send("Unable to find event in tourney. Please check your spelling or type !help for help on formatting.")

        @self.command(name="upset", pass_context=True)
        async def upset(ctx, arg1, arg2=None):
            event_data = self._startgg_client.show_event_metadata(arg1, arg2)
            if event_data is not None:
                if event_data['event_id'] not in self._upset_tournies and not event_data['complete']:
                    self._upset_tournies[event_data['event_id']] = UpsetTracker(arg1, arg2, event_data['tourney_name'], event_data['event_name'], self._startgg_client, ctx.channel)
                    await ctx.channel.send("Now tracking upsets for {} in event {}".format(event_data['tourney_name'], event_data['event_name']))
                elif event_data['event_id'] in self._upset_tournies:
                    await ctx.channel.send("Bot is already tracking this event for upsets")
                else:
                    await ctx.channel.send("Unable to track upsets for event {} in {}; event is already complete.".format(event_data['event_name'], event_data['tourney_name']))
            else:
                await ctx.channel.send("Unable to find event in tourney. Please check your spelling or type !help for help on formatting.")

        @self.command(name="untrackupset", pass_context=True)
        async def untrack_upset(ctx, arg1, arg2):
            event_data = self._startgg_client.show_event_metadata(arg1, arg2)
            if event_data is not None:
                if event_data['event_id'] in self._upset_tournies:
                    del self._upset_tournies[event_data['event_id']]
                    await ctx.channel.send("Stopped tracking upsets for event {} in {}".format(event_data['event_name'], event_data['tourney_name']))
                else:
                    await ctx.channel.send("Bot is not currently tracking this event")
            else:
                await ctx.channel.send("Unable to find event in tourney. Please check your spelling or type !help for help on formatting.")

        @self.command(name="help", pass_context=True)
        async def bot_help(ctx):
            await ctx.channel.send("To track a player's run: !track {tourney name} {player name} {player event}\n" +
                                   "To untrack a player's run: !untrack {tourney name} {player name} {player event}\n" +
                                   "To track upsets: !upset {tourney name} {tourney event}\n" +
                                   "To untrack upsets: !untrackupset {tourney name} {tourney event}")

        @self.command(name="test", pass_context=True)
        async def test_query(ctx):
            # todo: remove this function right before revealing the bot to the public
            metadata = self._startgg_client.show_event_metadata("versus-reborn-202", "smash-ultimate-singles")
            player_id = self._startgg_client.find_player_in_bracket(metadata['event_id'], "Phire")
            print(self._startgg_client.show_player_sets(player_id, metadata['event_id'], 1))
            #await ctx.channel.send(embed=discord.Embed(title="UPSET", description="Player A 2-0 Player B\nUpset Factor 3", color=discord.Color.blue()))
            #sets = self._startgg_client.tournament_show_sets("brick-d-up-5", "ultimate-singles", 1)
            #for s in sets['sets']:
                #print(s['entrant1Name'] + " - " + s['entrant2Name'])

    @tasks.loop(seconds=30)
    async def check_for_completed_tournies(self):
        completed_upset_tournies = [k for k in self._upset_tournies.keys() if self._upset_tournies[k].complete]
        for tourney in completed_upset_tournies:
            del self._upset_tournies[tourney]
