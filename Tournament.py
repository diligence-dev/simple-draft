from collections import OrderedDict
from random import sample
from statistics import mean
from warnings import warn
from zoneinfo import ZoneInfo
import datetime
import networkx as nx


def now_Berlin():
    return datetime.datetime.now(ZoneInfo("Europe/Berlin"))


def pair_and_result(p1, p2):
    if p1 == "bye":
        return ((p1, p2), (0, 2))
    elif p2 == "bye":
        return ((p1, p2), (2, 0))
    else:
        return ((p1, p2), (-1, -1))


class Tournament:
    def __init__(self, players):
        self._dropped_players = []
        self._round_results = []
        self._players = ["bye"]
        self._round_start_times = []
        for player in players:
            self.mod_add_player(player)

    def get_round_results(self):
        return self._round_results

    def get_round_start_time(self, formatted=True):
        t = (
            now_Berlin()
            if len(self._round_start_times) == 0
            else self._round_start_times[-1]
        )
        return t.strftime("%H:%M") if formatted else t

    def get_active_players(self, include_bye=False):
        return [
            p
            for p in self._players
            if p not in self._dropped_players and (p != "bye" or include_bye)
        ]

    def get_pairing(self):
        if len(self._round_results) == 0:
            return []
        return list(self._round_results[-1].keys())

    def get_pairing_with_score(self):
        if len(self._round_results) == 0:
            return []
        return self._round_results[-1].items()

    def get_round(self):
        return len(self._round_results)

    def get_standings(self, include_bye):
        standings = {
            player: {
                "points": 0,
                "games_won": 0,
                "games_played": 0,
                "matches_played": 0,
            }
            for player in self._players
        }

        for round_results in self._round_results:
            for (p1, p2), (p1_games_won, p2_games_won) in round_results.items():
                if p1_games_won not in [0, 1, 2] or p2_games_won not in [0, 1, 2]:
                    continue
                if p1_games_won > p2_games_won:
                    standings[p1]["points"] += 3
                elif p1_games_won == p2_games_won:
                    standings[p1]["points"] += 1
                    standings[p2]["points"] += 1
                else:
                    standings[p2]["points"] += 3
                standings[p1]["games_won"] += p1_games_won
                standings[p2]["games_won"] += p2_games_won
                standings[p1]["games_played"] += p1_games_won + p2_games_won
                standings[p2]["games_played"] += p1_games_won + p2_games_won
                standings[p1]["matches_played"] += 1
                standings[p2]["matches_played"] += 1

        # Calculate player match winrate
        for player in self._players:
            p = standings[player]
            if p["matches_played"] == 0:
                standings[player]["mw"] = -100
            else:
                standings[player]["mw"] = max(
                    0.333, p["points"] / (3 * p["matches_played"])
                )

        # Calculate opponent match winrate (OMW)
        for player in self._players:
            opponents = [
                match[0] if match[1] == player else match[1]
                for round_results in self._round_results
                for match, result in round_results.items()
                if player in match and "bye" not in match and result != (-1, -1)
            ]
            if not opponents:
                standings[player]["omw"] = 0
            else:
                standings[player]["omw"] = mean(
                    standings[opponent]["mw"] for opponent in opponents
                )

        # Calculate game winrate (GW)
        for player in self._players:
            p = standings[player]
            if p["games_played"] == 0:
                standings[player]["gw"] = -100
            else:
                standings[player]["gw"] = max(0.333, p["games_won"] / p["games_played"])

        # Calculate opponent game winrate (OGW)
        for player in self._players:
            opponents = [
                match[0] if match[1] == player else match[1]
                for round_results in self._round_results
                for match, result in round_results.items()
                if player in match and "bye" not in match and result != (-1, -1)
            ]
            if not opponents:
                standings[player]["ogw"] = 0
            else:
                standings[player]["ogw"] = mean(
                    standings[opponent]["gw"] for opponent in opponents
                )

        # Sort standings by points and OMW
        standings = [
            {"name": player, **stats}
            for player, stats in standings.items()
            if player != "bye" or include_bye
        ]
        standings.sort(key=lambda x: (-x["points"], -x["omw"], -x["gw"], -x["ogw"]))
        return standings

    def mod_submit_results(self, round_result):
        if list(round_result.keys()) != self.get_pairing():
            warn("wrong pairing")
            return False

        for (p1, p2), (games_won_p1, games_won_p2) in round_result.items():
            ok = self.mod_submit_result(p1, p2, games_won_p1, games_won_p2)
            if not ok:
                return False

        return True

    def mod_shuffle_seatings(self):
        if self.get_round() >= 2:
            warn("won't shuffle seatings after round 1")
            return False

        self._players = sample(self._players, len(self._players))
        self.mod_replace_pairing()
        return True

    def mod_add_player(self, player_to_add):
        player_to_add = player_to_add.replace("/", "|")
        player_to_add = player_to_add.replace("?", "")
        player_to_add = player_to_add.replace("%", "")
        player_to_add = player_to_add.strip()
        if player_to_add in self.get_active_players() or player_to_add == "bye":
            return ""

        if player_to_add in self._dropped_players:
            assert player_to_add in self._players
            self._dropped_players.remove(player_to_add)
        else:
            self._players.append(player_to_add)

        if self.get_round() <= 1:
            self.mod_shuffle_seatings()

        self.mod_replace_pairing(new_player=player_to_add)

        return player_to_add

    def mod_drop_player(self, player_to_drop):
        if player_to_drop not in self._players or player_to_drop == "bye":
            return False

        self._dropped_players.append(player_to_drop)
        self.mod_replace_pairing()
        return True

    def mod_swap_players(self, player1, player2):
        def f(p1, p2, g1, g2):
            if p1 == player1:
                return ((player2, p2), (-1, -1))
            if p2 == player1:
                return ((p1, player2), (-1, -1))
            if p1 == player2:
                return ((player1, p2), (-1, -1))
            if p2 == player2:
                return ((p1, player1), (-1, -1))
            return ((p1, p2), (g1, g2))

        self._round_results[-1] = dict(
            f(p1, p2, g1, g2) for (p1, p2), (g1, g2) in self._round_results[-1].items()
        )

    def mod_submit_result(self, p1, p2, p1_games_won, p2_games_won):
        if (p1, p2) not in self.get_pairing():
            warn(f"{p1} vs {p2} not in pairing")
            return False
        if p1_games_won not in (0, 1, 2) or p2_games_won not in (0, 1, 2):
            warn("games won not in (0, 1, 2)")
            return False
        elif p1_games_won + p2_games_won > 3:
            warn("total games > 3")
            return False

        self._round_results[-1][(p1, p2)] = (p1_games_won, p2_games_won)

        if all(
            s1 in (0, 1, 2) and s2 in (0, 1, 2)
            for _, (s1, s2) in self.get_pairing_with_score()
        ):
            return self.mod_create_pairing()

        return True

    def mod_create_pairing(self):
        self._round_start_times.append(now_Berlin())
        if self.get_round() == 0:
            players = self.get_active_players(include_bye=True)
            if len(players) % 2 == 1:
                players.remove("bye")

            n_halved = int(len(players) / 2)
            self._round_results.append(
                OrderedDict(
                    pair_and_result(players[i], players[i + n_halved])
                    for i in range(n_halved)
                )
            )
            return True

        # Swiss pairing using maximum weight matching
        standings = self.get_standings(include_bye=True)
        active_players = self.get_active_players(include_bye=True)
        if len(active_players) % 2 == 1:
            active_players.remove("bye")
        # get players in standings order
        players = [p["name"] for p in standings if p["name"] in active_players]
        pairing_history = {
            frozenset(match)
            for round_results in self._round_results
            for match in round_results
        }

        G = nx.Graph()
        G.add_nodes_from(players)

        # Add edges with weights based on points
        for i, p1 in enumerate(players):
            for p2 in players[i + 1 :]:
                if frozenset({p1, p2}) not in pairing_history:
                    score_diff = abs(
                        standings[i]["points"] - standings[players.index(p2)]["points"]
                    )
                    score_sum = (
                        standings[i]["points"] + standings[players.index(p2)]["points"]
                    )
                    G.add_edge(p1, p2, weight=-(score_diff**2 * score_sum))

        pairings = list(nx.max_weight_matching(G, maxcardinality=True))

        # Add current pairings to x
        self._round_results.append(
            OrderedDict(pair_and_result(p1, p2) for p1, p2 in pairings)
        )
        return True

    def mod_replace_pairing(self, new_player=None):
        if (
            new_player is not None
            and len(self.get_active_players(include_bye=True)) % 2 == 1
        ):
            # new player replaces bye
            def replace_bye(pair, result):
                a, b = pair
                if a == "bye":
                    return (new_player, b), (-1, -1)
                elif b == "bye":
                    return (a, new_player), (-1, -1)
                return (a, b), result

            self._round_results[-1] = OrderedDict(
                replace_bye(pair, result)
                for pair, result in self._round_results[-1].items()
            )
            return True

        if self.get_round() >= 1:
            self._round_results.pop()
        return self.mod_create_pairing()
