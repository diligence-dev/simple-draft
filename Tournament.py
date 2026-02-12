from datetime import datetime
from random import sample
from statistics import mean
from warnings import warn
import networkx as nx  # type: ignore
from TournamentBase import (
    Player,
    Pair,
    now_Berlin,
    Match,
    TournamentBase,
)


class Tournament(TournamentBase):
    _round_start_times: list[datetime]

    def __init__(self, players: list[Player]):
        self._dropped_players = []
        self._round_results = []
        self._players = ["bye"]
        self._round_start_times = []
        for player in players:
            self.mod_add_player(player)

    def get_round_start_time(self, formatted=True) -> str | datetime:
        t = (
            now_Berlin()
            if len(self._round_start_times) == 0
            else self._round_start_times[-1]
        )
        return t.strftime("%H:%M") if formatted else t

    def get_current_matches(self) -> list[Match]:
        if len(self._round_results) == 0:
            return []
        return self._round_results[-1]

    def get_round(self) -> int:
        return len(self._round_results)

    def mod_submit_results(self, round_result: list[Match]) -> bool:
        if [(m.p1, m.p2) for m in round_result] != self.get_pairing():
            warn("wrong pairing")
            return False

        for m in round_result:
            ok = self.mod_submit_result(m.p1, m.p2, m.p1_games_won, m.p2_games_won)
            if not ok:
                return False

        return True

    def mod_swap_players(self, player1: Player, player2: Player) -> None:
        def f(m):
            if m.p1 == player1:
                return Match(player2, m.p2, -1, -1)
            if m.p2 == player1:
                return Match(m.p1, player2, -1, -1)
            if m.p1 == player2:
                return Match(player1, m.p2, -1, -1)
            if m.p2 == player2:
                return Match(m.p1, player1, -1, -1)
            return m

        self._round_results[-1] = [f(match) for match in self._round_results[-1]]

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

        for m in self._round_results[-1]:
            if m.p1 == p1 and m.p2 == p2:
                m.mod_finish(p1_games_won, p2_games_won)
                break

        if all(match.is_finished() for match in self.get_current_matches()):
            self.mod_create_pairing()
            return True

        return True

    def mod_create_pairing(self) -> None:
        if not all(m.is_finished() for m in self.get_current_matches()):
            return None

        self._round_start_times.append(now_Berlin())
        if self.get_round() == 0:
            players = self.get_active_players(include_bye=True)
            if len(players) % 2 == 1:
                players.remove("bye")

            n_halved = int(len(players) / 2)
            self._round_results.append(
                [
                    Match(players[i], players[i + n_halved])
                    for i in range(n_halved)
                ]
            )
            return None

        # Swiss pairing using maximum weight matching
        standings = self.get_standings(include_bye=True)
        active_players = self.get_active_players(include_bye=True)
        if len(active_players) % 2 == 1:
            active_players.remove("bye")
        # get players in standings order
        players = [p.name for p in standings if p.name in active_players]
        pairing_history = {
            frozenset({match.p1, match.p2})
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
                        standings[i].points - standings[players.index(p2)].points
                    )
                    score_sum = (
                        standings[i].points + standings[players.index(p2)].points
                    )
                    G.add_edge(p1, p2, weight=-(score_diff**2 * score_sum))

        pairings: list[Pair] = list(nx.max_weight_matching(G, maxcardinality=True))

        # Add current pairings to x
        self._round_results.append([Match(p1, p2) for p1, p2 in pairings])

    def mod_replace_pairing(self, new_player: str = "") -> None:
        if new_player != "" and len(self.get_active_players(include_bye=True)) % 2 == 1:
            # new player replaces bye
            def replace_bye(m: Match) -> Match:
                if m.p1 == "bye":
                    return Match(new_player, m.p2, -1, -1)
                elif m.p2 == "bye":
                    return Match(m.p1, new_player, -1, -1)
                return m

            self._round_results[-1] = [
                replace_bye(match) for match in self._round_results[-1]
            ]

        if self.get_round() >= 1:
            self._round_results.pop()
        return self.mod_create_pairing()
