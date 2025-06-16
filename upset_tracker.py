import discord
from discord.ext import tasks

from base_tracker import BaseTracker
from start_gg import StartGG

import utilities

import asyncio


class UpsetTracker(BaseTracker):

    def __init__(self, tourney: str, event: str, tourney_name: str, event_name: str, startgg_client: StartGG, channel: 'discord channel'):
        self._tourney = tourney
        self._event = event
        self._tourney_name = tourney_name
        self._event_name = event_name
        self._startgg_client = startgg_client
        self._channel = channel
        self._minutes_since_last_change = 0
        self.complete = False

        self.check_for_updates.start()

    @tasks.loop(seconds=60)
    async def check_for_updates(self):
        """Checks for newly completed tournament sets every 60 seconds"""
        print("Checking for updates")
        current_page = 1

        while True:
            sets_dict = self._startgg_client.tournament_show_sets(self._tourney, self._event, current_page)
            sets_num = len(sets_dict['sets'])

            if current_page == 1 and sets_num == 0:
                self._minutes_since_last_change += 1
            elif sets_num == 0:
                # should only occur if the last page had exactly 18 sets
                return
            else:
                self._minutes_since_last_change = 0

            if sets_dict['complete'] or self._minutes_since_last_change >= 2880:
                self.complete = True
                await self._channel.send("Event {} in {} is complete and upset tracking has stopped.".format(self._event_name, self._tourney_name))
                self.check_for_updates.cancel()
                return

            await self._send_upset_messages(sets_dict['sets'])

            # if less than 18 sets, it was the last page; otherwise go to the next page
            if sets_num < 18:
                return
            current_page += 1

    async def _send_upset_messages(self, sets: dict) -> None:
        """Checks if the lower seed won and sends messages to the Discord channel if so"""
        for tourney_set in sets:
            print("Set completed: {} - {}".format(tourney_set['entrant1Name'], tourney_set['entrant2Name']))
            upset_factor = utilities.calculate_upset_factor(tourney_set['entrant1Seed'], tourney_set['entrant2Seed'])
            if upset_factor > 0:
                embed_title = "UPSET in {} {}".format(self._tourney_name, self._event_name)
                winner_name = None
                winner_score = None
                loser_name = None
                loser_score = None

                if tourney_set['winnerId'] == tourney_set['entrant1Id'] and tourney_set['entrant1Seed'] > tourney_set['entrant2Seed'] and tourney_set['entrant2Score'] > -1:
                    winner_name = tourney_set['entrant1Name']
                    winner_score = tourney_set['entrant1Score']
                    loser_name = tourney_set['entrant2Name']
                    loser_score = tourney_set['entrant2Score']
                elif tourney_set['winnerId'] == tourney_set['entrant2Id'] and tourney_set['entrant2Seed'] > tourney_set['entrant1Seed'] and tourney_set['entrant1Score'] > -1:
                    winner_name = tourney_set['entrant2Name']
                    winner_score = tourney_set['entrant2Score']
                    loser_name = tourney_set['entrant1Name']
                    loser_score = tourney_set['entrant1Score']

                if winner_name is not None and winner_score is not None and loser_name is not None and loser_score is not None:
                    embed_desc = "{} {} - {} {}\nUpset Factor: {}".format(winner_name, winner_score, loser_score, loser_name, upset_factor)
                    await self._channel.send(embed=discord.Embed(title=embed_title, description=embed_desc, color=discord.Color.blue()))

            await asyncio.sleep(1)
