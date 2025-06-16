import discord
from discord.ext import tasks

import utilities
from base_tracker import BaseTracker
from start_gg import StartGG

import asyncio


class BracketRunTracker(BaseTracker):

    def __init__(self, event_id: str, player_id: str, tourney_name: str, event_name: str, player_name: str, startgg_client: StartGG, channel: 'discord_channel'):
        self._event_id = event_id
        self._player_id = player_id
        self._tourney_name = tourney_name
        self._event_name = event_name
        self._player_name = player_name
        self._startgg_client = startgg_client
        self._channel = channel
        self._minutes_since_last_change = 0
        self.complete = False

        self.check_for_updates.start()

    @tasks.loop(seconds=60)
    async def check_for_updates(self):
        print("Checking for updates")
        current_page = 1

        while True:
            sets_dict = self._startgg_client.show_player_sets(self._player_id, self._event_id, current_page)
            sets_num = len(sets_dict)

            if current_page == 1 and sets_num == 0:
                self._minutes_since_last_change += 1
            elif sets_num == 0:
                # should only happen if the last page had exactly 10 sets
                return
            else:
                self._minutes_since_last_change = 0

            if sets_dict['complete'] or self._minutes_since_last_change >= 2880:
                self.complete = True
                await self._channel.send("Event {} in {} is complete and tracking for player {} has stopped.".format(self._event_name, self._tourney_name, self._player_name))
                self.check_for_updates.cancel()
                return

            if sets_num < 10:
                return
            current_page += 1

    async def _send_player_update_messages(self, sets: dict) -> None:
        for tourney_set in sets:
            upset_factor = utilities.calculate_upset_factor(tourney_set['entrant1Seed'], tourney_set['entrant2Seed'])
            if tourney_set['entrant1Players'][0]['playerId'] == self._player_id:
                entrant_id = tourney_set['entrant1Players'][0]['entrantId']
                player_score = tourney_set['entrant1Score']
                opponent_score = tourney_set['entrant2Score']
                opponent_name = tourney_set['entrant2Name']
            else:
                entrant_id = tourney_set['entrant2Players'][0]['entrantId']
                player_score = tourney_set['entrant2Score']
                opponent_score = tourney_set['entrant1Score']
                opponent_name = tourney_set['entrant1Name']

            if tourney_set['winnerId'] == entrant_id:
                embed_title = "{} DEFEATS {}".format(self._player_name, opponent_name)
                embed_color = discord.Color.green()
            elif player_score == -1:
                embed_title = "{} HAS DQ'D".format(self._player_name)
                embed_color = discord.Color.dark_gray()
            else:
                embed_title = "{} LOSES TO {}".format(self._player_name, opponent_name)
                embed_color = discord.Color.red()

            embed_desc = "Tournament: {}\nEvent: {}\nScore: {} - {}".format(self._tourney_name, self._event_name, player_score, opponent_score)
            if upset_factor > 0:
                embed_desc += "\nUpset Factor: {}".format(upset_factor)
            await self._channel.send(embed=discord.Embed(title=embed_title, description=embed_desc, color=embed_color))

            await asyncio.sleep(1)
