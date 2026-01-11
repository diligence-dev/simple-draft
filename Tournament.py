from dataclasses import dataclass
from datetime import datetime
from random import sample
from statistics import mean
from warnings import warn
from zoneinfo import ZoneInfo
import networkx as nx  # type: ignore

Player = str
Pair = tuple[Player, Player]
Result = tuple[int, int]


@dataclass
class Match:
    p1: Player
    p2: Player
    p1_games_won: int = -1
    p2_games_won: int = -1

    def includes(self, player: Player) -> bool:
        return player in (self.p1, self.p2)

    def is_finished(self) -> bool:
        return (
            0 <= self.p1_games_won + self.p2_games_won <= 3
            and self.p1_games_won >= 0
            and self.p2_games_won >= 0
        )

    def __iter__(self):
        yield self.p1
        yield self.p2
        yield self.p1_games_won
        yield self.p2_games_won


def now_Berlin() -> datetime:
    return datetime.now(ZoneInfo("Europe/Berlin"))


def pair_and_result(p1: str, p2: str) -> Match:
    if p1 == "bye":
        return Match(p1, p2, 0, 2)
    elif p2 == "bye":
        return Match(p1, p2, 2, 0)
    else:
        return Match(p1, p2, -1, -1)


def find_opponents(round_results: list[list[Match]], player: Player) -> list[Player]:
    return [
        match.p1 if match.p2 == player else match.p1
        for rr in round_results
        for match in rr
        if match.includes(player) and not match.includes("bye") and match.is_finished()
    ]


@dataclass
class PlayerStats:
    name: str
    points: int = 0
    games_won: int = 0
    games_played: int = 0
    matches_played: int = 0
    mw: float = -99
    omw: float = -99
    gw: float = -99
    ogw: float = -99


class Tournament:
    def __init__(self, players: list[Player]):
        self._dropped_players: list[Player] = []
        self._round_results: list[list[Match]] = []
        self._players: list[Player] = ["bye"]
        self._round_start_times: list[datetime] = []
        for player in players:
            self.mod_add_player(player)

    def get_round_results(self) -> list[list[Match]]:
        return self._round_results

    def get_round_start_time(self, formatted=True) -> str | datetime:
        t = (
            now_Berlin()
            if len(self._round_start_times) == 0
            else self._round_start_times[-1]
        )
        return t.strftime("%H:%M") if formatted else t

    def get_active_players(self, include_bye=False) -> list[Player]:
        return [
            p
            for p in self._players
            if p not in self._dropped_players and (p != "bye" or include_bye)
        ]

    def get_pairing(self) -> list[Pair]:
        if len(self._round_results) == 0:
            return []
        return [(m.p1, m.p2) for m in self._round_results[-1]]

    def get_pairing_with_score(
        self,
    ) -> list[Match]:
        if len(self._round_results) == 0:
            return []
        return self._round_results[-1]

    def get_round(self) -> int:
        return len(self._round_results)

    def get_standings(self, include_bye: bool) -> list[PlayerStats]:
        standings: dict[Player, PlayerStats] = {
            player: PlayerStats(player) for player in self._players
        }

        for round_results in self._round_results:
            for m in round_results:
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
            opponents = find_opponents(self._round_results, player)
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
            opponents = find_opponents(self._round_results, player)
            if not opponents:
                standings[player].ogw = 0
            else:
                standings[player].ogw = mean(
                    standings[opponent].gw for opponent in opponents
                )

        # Sort standings by points and OMW
        standingsList: list[PlayerStats] = [
            stats
            for player, stats in standings.items()
            if player != "bye" or include_bye
        ]
        standingsList.sort(key=lambda x: (-x.points, -x.omw, -x.gw, -x.ogw))
        return standingsList

    def mod_submit_results(self, round_result: list[Match]) -> bool:
        if [(m.p1, m.p2) for m in round_result] != self.get_pairing():
            warn("wrong pairing")
            return False

        for m in round_result:
            ok = self.mod_submit_result(m.p1, m.p2, m.p1_games_won, m.p2_games_won)
            if not ok:
                return False

        return True

    def mod_shuffle_seatings(self) -> bool:
        if self.get_round() >= 2:
            warn("won't shuffle seatings after round 1")
            return False

        self._players = sample(self._players, len(self._players))
        self.mod_replace_pairing()
        return True

    def mod_add_player(self, player_to_add: str) -> str:
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

    def mod_drop_player(self, player_to_drop: Player) -> bool:
        if player_to_drop not in self._players or player_to_drop == "bye":
            return False

        self._dropped_players.append(player_to_drop)
        self.mod_replace_pairing()
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

        def replace_result(m, p1, p2, p1_games_won, p2_games_won):
            if m.p1 == p1 and m.p2 == p2:
                return Match(p1, p2, p1_games_won, p2_games_won)
            return m

        self._round_results[-1] = [
            replace_result(match, p1, p2, p1_games_won, p2_games_won)
            for match in self._round_results[-1]
        ]

        if all(match.is_finished() for match in self.get_pairing_with_score()):
            self.mod_create_pairing()
            return True

        return True

    def mod_create_pairing(self) -> None:
        self._round_start_times.append(now_Berlin())
        if self.get_round() == 0:
            players = self.get_active_players(include_bye=True)
            if len(players) % 2 == 1:
                players.remove("bye")

            n_halved = int(len(players) / 2)
            self._round_results.append(
                [
                    pair_and_result(players[i], players[i + n_halved])
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
        self._round_results.append([pair_and_result(p1, p2) for p1, p2 in pairings])

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
