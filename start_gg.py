from pysmashgg import SmashGG, tournaments, api, filters
from custom_start_gg_queries import *

import time


class StartGG(SmashGG):
    def __init__(self, key):
        SmashGG.__init__(self, key)

    def tournament_show_sets(self, tournament_name: str, event_name: str, page_num: int) -> dict:
        data = {}
        event_id = tournaments.get_event_id(tournament_name, event_name, self.header, self.auto_retry)
        variables = {"eventId": event_id, "page": page_num, "filters": {"updatedAfter": int(time.time()) - 70, "state": 3}}
        response = api.run_query(SHOW_SETS_WITH_SEED_QUERY, variables, self.header, self.auto_retry)
        sets = filters.show_sets_filter(response)

        # adding seed to data
        if sets is not None:
            nodes = response['data']['event']['sets']['nodes']
            for i in range(len(sets)):
                if len(nodes[i]['slots']) < 2:
                    continue  # This fixes a bug where player doesn't have an opponent
                if nodes[i]['slots'][0]['entrant'] is None or nodes[i]['slots'][1]['entrant'] is None:
                    continue  # This fixes a bug when tournament ends early

                sets[i]['entrant1Seed'] = nodes[i]['slots'][0]['entrant']['initialSeedNum']
                sets[i]['entrant2Seed'] = nodes[i]['slots'][1]['entrant']['initialSeedNum']

        data['sets'] = sets
        data['complete'] = response['data']['event']['state'] == 'COMPLETED'
        return data

    def show_event_metadata(self, tournament_name: str, event_name: str) -> dict or None:
        data = None
        variables = {"tourneySlug": tournament_name}
        response = api.run_query(SHOW_EVENT_METADATA, variables, self.header, self.auto_retry)

        if response['data']['tournament'] is None:
            return None

        if event_name is not None:
            for event in response['data']['tournament']['events']:
                if event['slug'].split("/")[-1] == event_name:
                    data = {'tourney_name': response['data']['tournament']['name'], 'event_name': event['name'],
                            'event_id': event['id'], 'complete': event['state'] == 'COMPLETED'}
                    break
        else:
            data = {'tourney_name': response['data']['tournament']['name'], 'event_name': response['data']['tournament']['events'][0]['name'],
                    'event_id': response['data']['tournament']['events'][0]['id'], 'complete': response['data']['tournament']['events'][0]['state'] == 'COMPLETED'}

        return data

    def find_player_in_bracket(self, event_id: str, player_name: str) -> str or None:
        try:
            return tournaments.get_player_id(event_id, player_name, self.header, self.auto_retry)
        except IndexError:
            return None

    def show_player_sets(self, player_id: str, event_id: str, page_num: int) -> dict or None:
        data = {}
        variables = {"playerId": player_id, "page": page_num, "filters": {"eventIds": [event_id], "state": 3}}
        response = api.run_query(SHOW_PLAYER_SETS_QUERY, variables, self.header, self.auto_retry)
        sets = self._player_sets_filter(response)

        data['sets'] = sets
        data['complete'] = response['data']['player']['sets']['nodes'][0]['event']['state'] == 'COMPLETED' if len(sets) > 0 else False
        return data

    def _player_sets_filter(self, response: dict) -> list or None:
        """Helper method based off the show_sets_filter function in PySmashGG"""
        if 'data' not in response:
            return
        if response['data']['player'] is None:
            return

        if response['data']['player']['sets']['nodes'] is None:
            return

        sets = []  # Need for return at the end

        for node in response['data']['player']['sets']['nodes']:
            if len(node['slots']) < 2:
                continue  # This fixes a bug where player doesn't have an opponent
            if (node['slots'][0]['entrant'] is None or node['slots'][1]['entrant'] is None):
                continue  # This fixes a bug when tournament ends early

            cur_set = {}
            cur_set['id'] = node['id']
            cur_set['entrant1Id'] = node['slots'][0]['entrant']['id']
            cur_set['entrant2Id'] = node['slots'][1]['entrant']['id']
            cur_set['entrant1Name'] = node['slots'][0]['entrant']['name']
            cur_set['entrant2Name'] = node['slots'][1]['entrant']['name']

            if (node['games'] is not None):
                entrant1_chars = []
                entrant2_chars = []
                game_winners_ids = []
                for game in node['games']:
                    if (game['selections'] is None):  # This fixes an issue with selections being none while games are reported
                        continue
                    elif (node['slots'][0]['entrant']['id'] == game['selections'][0]['entrant']['id']):
                        entrant1_chars.append(game['selections'][0]['selectionValue'])
                        if len(game['selections']) > 1:
                            entrant2_chars.append(game['selections'][1]['selectionValue'])
                    else:
                        entrant2_chars.append(game['selections'][0]['selectionValue'])
                        if len(game['selections']) > 1:
                            entrant1_chars.append(game['selections'][1]['selectionValue'])

                    game_winners_ids.append(game['winnerId'])

                cur_set['entrant1Chars'] = entrant1_chars
                cur_set['entrant2Chars'] = entrant2_chars
                cur_set['gameWinners'] = game_winners_ids

            # Next 2 if/else blocks make sure there's a result in, sometimes DQs are weird
            # there also could be ongoing matches
            match_done = True
            if node['slots'][0]['standing'] is None:
                cur_set['entrant1Score'] = -1
                match_done = False
            elif node['slots'][0]['standing']['stats']['score']['value'] is not None:
                cur_set['entrant1Score'] = node['slots'][0]['standing']['stats']['score']['value']
            else:
                cur_set['entrant1Score'] = -1

            if node['slots'][1]['standing'] is None:
                cur_set['entrant2Score'] = -1
                match_done = False
            elif node['slots'][1]['standing']['stats']['score']['value'] is not None:
                cur_set['entrant2Score'] = node['slots'][1]['standing']['stats']['score']['value']
            else:
                cur_set['entrant2Score'] = -1

            # Determining winner/loser (elif because sometimes smashgg won't give us one)
            if match_done:
                cur_set['completed'] = True
                if node['slots'][0]['standing']['placement'] == 1:
                    cur_set['winnerId'] = cur_set['entrant1Id']
                    cur_set['loserId'] = cur_set['entrant2Id']
                    cur_set['winnerName'] = cur_set['entrant1Name']
                    cur_set['loserName'] = cur_set['entrant2Name']
                elif node['slots'][0]['standing']['placement'] == 2:
                    cur_set['winnerId'] = cur_set['entrant2Id']
                    cur_set['loserId'] = cur_set['entrant1Id']
                    cur_set['winnerName'] = cur_set['entrant2Name']
                    cur_set['loserName'] = cur_set['entrant1Name']
            else:
                cur_set['completed'] = False

            cur_set['fullRoundText'] = node['fullRoundText']

            if node['phaseGroup'] is not None:
                cur_set['bracketName'] = node['phaseGroup']['phase']['name']
                cur_set['bracketId'] = node['phaseGroup']['id']
            else:
                cur_set['bracketName'] = None
                cur_set['bracketId'] = None

            # This gives player_ids, but it also is made to work with team events
            for j in range(0, 2):
                players = []
                for user in node['slots'][j]['entrant']['participants']:
                    cur_player = {}
                    if user['player'] is not None:
                        cur_player['playerId'] = user['player']['id']
                        cur_player['playerTag'] = user['player']['gamerTag']
                        if user['entrants'] is not None:
                            cur_player['entrantId'] = user['entrants'][0]['id']
                        else:
                            cur_player['entrantId'] = node['slots'][j]['entrant']['id']
                        players.append(cur_player)
                    else:
                        cur_player['playerId'] = None
                        cur_player['playerTag'] = None
                        cur_player['entrantId'] = node['slots'][j]['entrant']['id']

                cur_set['entrant' + str(j + 1) + 'Players'] = players

            cur_set['entrant1Seed'] = node['slots'][0]['entrant']['initialSeedNum']
            cur_set['entrant2Seed'] = node['slots'][1]['entrant']['initialSeedNum']

            sets.append(cur_set)  # Adding that specific set onto the large list of sets

        return sets
