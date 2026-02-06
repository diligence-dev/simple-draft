from random import sample
from statistics import mean
from warnings import warn
import networkx as nx  # type: ignore
from TournamentBase import (
    Player,
    PlayerStats,
    Pair,
    Match,
    pair_and_result,
    find_opponents,
    TournamentBase,
)


class TournamentOdd(TournamentBase):
    def __init__(self, players: list[Player]):
        self._dropped_players: list[Player] = []
        self._matches: list[Match] = []
        self._players: list[Player] = []

        # for player in players:
        #     self.mod_add_player(player)
        self._players = players
        self.mod_create_pairing()

    def get_finished_matches(self) -> list[Match]:
        return [m for m in self._matches if m.is_finished()]

    def get_current_matches(self) -> list[Match]:
        return [m for m in self._matches if not m.is_finished()]

    def get_active_players(self) -> list[Player]:
        return [p for p in self._players if p not in self._dropped_players]

    def is_player_free(self, player) -> bool:
        return (
            not any(m.includes(player) for m in self.get_current_matches())
            and self.n_matches_played(player) < 3
        )

    def get_free_players(self) -> list[Player]:
        return [p for p in self.get_active_players() if self.is_player_free(p)]

    def n_matches_played(self, player) -> int:
        return len([m for m in self.get_finished_matches() if m.includes(player)])

    def is_over(self) -> bool:
        return (
            sum(self.n_matches_played(p) for p in self.get_active_players())
            >= len(self.get_active_players()) * 3 - 1
        )

    def get_pairing(self) -> list[Pair]:
        return [(m.p1, m.p2) for m in self.get_current_matches()]

    def get_standings(self) -> list[PlayerStats]:
        standings: dict[Player, PlayerStats] = {
            player: PlayerStats(player) for player in self._players
        }

        for m in self.get_finished_matches():
            if m.p1_games_won not in [0, 1, 2] or m.p2_games_won not in [0, 1, 2]:
                continue

            if m.p1_games_won > m.p2_games_won:
                standings[m.p1].points += 3
            elif m.p1_games_won == m.p2_games_won:
                standings[m.p1].points += 1
                standings[m.p2].points += 1
            else:
                standings[m.p2].points += 3

            standings[m.p1].games_won += m.p1_games_won
            standings[m.p2].games_won += m.p2_games_won
            standings[m.p1].games_played += m.p1_games_won + m.p2_games_won
            standings[m.p2].games_played += m.p1_games_won + m.p2_games_won
            standings[m.p1].matches_played += 1
            standings[m.p2].matches_played += 1

        # Calculate player match winrate
        for player in self._players:
            p = standings[player]
            if p.matches_played == 0:
                standings[player].mw = -100
            else:
                standings[player].mw = max(0.333, p.points / (3 * p.matches_played))

        # Calculate opponent match winrate (OMW)
        for player in self._players:
            opponents = find_opponents(self.get_finished_matches(), player)
            if not opponents:
                standings[player].omw = 0
            else:
                standings[player].omw = mean(
                    standings[opponent].mw for opponent in opponents
                )

        # Calculate game winrate (GW)
        for player in self._players:
            p = standings[player]
            if p.games_played == 0:
                standings[player].gw = -100
            else:
                standings[player].gw = max(0.333, p.games_won / p.games_played)

        # Calculate opponent game winrate (OGW)
        for player in self._players:
            opponents = find_opponents(self.get_finished_matches(), player)
            if not opponents:
                standings[player].ogw = 0
            else:
                standings[player].ogw = mean(
                    standings[opponent].gw for opponent in opponents
                )

        # Sort standings by points and OMW
        standingsList: list[PlayerStats] = list(standings.values())
        standingsList.sort(key=lambda x: (-x.points, -x.omw, -x.gw, -x.ogw))
        return standingsList

    # def mod_shuffle_seatings(self) -> bool:
    #     self._players = sample(self._players, len(self._players))
    #     self.mod_replace_pairing()
    #     return True

    # def mod_add_player(self, player_to_add: str) -> str:
    #     player_to_add = player_to_add.replace("/", "|")
    #     player_to_add = player_to_add.replace("?", "")
    #     player_to_add = player_to_add.replace("%", "")
    #     player_to_add = player_to_add.strip()
    #     if player_to_add in self.get_active_players() or player_to_add == "bye":
    #         return ""

    #     if player_to_add in self._dropped_players:
    #         assert player_to_add in self._players
    #         self._dropped_players.remove(player_to_add)
    #     else:
    #         self._players.append(player_to_add)

    #     self.mod_replace_pairing(new_player=player_to_add)

    #     return player_to_add

    # def mod_drop_player(self, player_to_drop: Player) -> bool:
    #     if player_to_drop not in self._players:
    #         return False

    #     self._dropped_players.append(player_to_drop)
    #     self.mod_replace_pairing()
    #     return True

    def mod_swap_players(self, player1: Player, player2: Player) -> None:
        ms1 = [m for m in self.get_current_matches() if m.includes(player1)]
        assert len(ms1) == 1
        m1 = ms1[0]

        ms2 = [m for m in self.get_current_matches() if m.includes(player2)]
        assert len(ms2) == 1
        m2 = ms2[0]

        if m1.p1 == player1:
            m1.p1 = player2
        else:
            assert m1.p2 == player1
            m1.p2 = player2

        if m2.p1 == player2:
            m2.p1 = player1
        else:
            assert m2.p2 == player2
            m2.p2 = player1

    def mod_submit_result(
        self, p1: Player, p2: Player, p1_games_won: int, p2_games_won: int
    ) -> bool:
        if (p1, p2) not in self.get_pairing():
            warn(f"{p1} vs {p2} not in pairing")
            return False
        if p1_games_won not in (0, 1, 2) or p2_games_won not in (0, 1, 2):
            warn("games won not in (0, 1, 2)")
            return False
        elif p1_games_won + p2_games_won > 3:
            warn("total games > 3")
            return False

        for m in self.get_current_matches():
            if m.p1 == p1 and m.p2 == p2:
                m.mod_finish(p1_games_won, p2_games_won)
                break

        self.mod_create_pairing()
        return True

    def mod_create_pairing(self) -> None:
        if len(self._matches) == 0:
            players = self.get_active_players()

            n_halved = int(len(players) / 2)
            self._matches = [
                pair_and_result(players[i], players[i + n_halved])
                for i in range(n_halved)
            ]

            return None

        # Swiss pairing using maximum weight matching
        standings = self.get_standings()

        # get players in standings order
        players = [p.name for p in standings if p.name in self.get_free_players()]
        pairing_history = {
            frozenset({match.p1, match.p2}) for match in self.get_finished_matches()
        }

        G = nx.Graph()
        G.add_nodes_from(players)

        # Add edges with weights based on points
        for i, p1 in enumerate(players):
            for p2 in players[i + 1 :]:
                if frozenset({p1, p2}) not in pairing_history:
                    score_diff = abs(
                        standings[i].points - standings[players.index(p2)].points
                    )
                    score_sum = (
                        standings[i].points + standings[players.index(p2)].points
                    )
                    G.add_edge(p1, p2, weight=-(score_diff**2 * score_sum))

        pairings: list[Pair] = list(nx.max_weight_matching(G, maxcardinality=True))

        # Add current pairings to x
        self._matches.extend(pair_and_result(p1, p2) for p1, p2 in pairings)

    # def mod_replace_pairing(self, new_player: str = "") -> None:
    #     if new_player != "" and len(self.get_active_players(include_bye=True)) % 2 == 1:
    #         # new player replaces bye
    #         def replace_bye(m: Match) -> Match:
    #             if m.p1 == "bye":
    #                 return Match(new_player, m.p2, -1, -1)
    #             elif m.p2 == "bye":
    #                 return Match(m.p1, new_player, -1, -1)
    #             return m

    #         self._round_results[-1] = [
    #             replace_bye(match) for match in self._round_results[-1]
    #         ]

    #     if self.get_round() >= 1:
    #         self._round_results.pop()
    #     return self.mod_create_pairing()
