from dataclasses import dataclass
from datetime import datetime
from random import sample
from statistics import mean
from warnings import warn
from zoneinfo import ZoneInfo

Player = str
Pair = tuple[Player, Player]

now_Berlin_forced = None


def set_now_Berlin_forced(x):
    global now_Berlin_forced
    now_Berlin_forced = x


def now_Berlin() -> datetime:
    return (
        datetime.now(ZoneInfo("Europe/Berlin"))
        if now_Berlin_forced is None
        else now_Berlin_forced
    )


@dataclass
class Match:
    p1: Player
    p2: Player
    p1_games_won: int
    p2_games_won: int
    t_start: datetime
    t_end: datetime | None

    def __init__(
        self, p1, p2, p1_games_won=-1, p2_games_won=-1, t_start=None, t_end=None
    ):
        self.p1 = p1
        self.p2 = p2
        self.p1_games_won = p1_games_won
        self.p2_games_won = p2_games_won
        self.t_start = now_Berlin() if t_start is None else t_start
        self.t_end = t_end

    def mod_finish(self, p1_games_won: int, p2_games_won: int) -> bool:
        if (
            0 <= p1_games_won + p2_games_won <= 3
            and p1_games_won >= 0
            and p2_games_won >= 0
        ):
            self.t_end = now_Berlin()
            if self.t_end < self.t_start:
                warn(f"match ended before it began: ${self}")

            self.p1_games_won = p1_games_won
            self.p2_games_won = p2_games_won
            return True
        else:
            return False

    def duration_seconds(self) -> int | None:
        if self.t_end is None:
            return None
        return (self.t_end - self.t_start).seconds

    def includes(self, player: Player) -> bool:
        return player in (self.p1, self.p2)

    def is_finished(self) -> bool:
        return (
            0 <= self.p1_games_won + self.p2_games_won <= 3
            and self.p1_games_won >= 0
            and self.p2_games_won >= 0
            and self.t_end is not None
        )

    def __iter__(self):
        yield self.p1
        yield self.p2
        yield self.p1_games_won
        yield self.p2_games_won


def pair_and_result(p1: str, p2: str) -> Match:
    now = now_Berlin()
    if p1 == "bye":
        return Match(p1, p2, 0, 2, t_start=now, t_end=now)
    elif p2 == "bye":
        return Match(p1, p2, 2, 0, t_start=now, t_end=now)
    else:
        return Match(p1, p2, -1, -1)


def find_opponents(matches: list[list[Match]], player: Player) -> list[Player]:
    return [
        match.p1 if match.p2 == player else match.p1
        for ms in matches
        for match in ms
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


class TournamentBase:
    _dropped_players: list[Player]
    _round_results: list[list[Match]]
    _players: list[Player]

    def get_finished_matches(self) -> list[Match]:
        return [m for ms in self._round_results for m in ms if m.is_finished()]

    def get_active_players(self, include_bye=False) -> list[Player]:
        return [
            p
            for p in self._players
            if p not in self._dropped_players and (p != "bye" or include_bye)
        ]

    def get_current_matches(self) -> list[Match]:
        raise "get_current_matches must be overwritten"

    def get_pairing(self) -> list[Pair]:
        return [(m.p1, m.p2) for m in self.get_current_matches()]

    def get_standings(self, include_bye: bool = False) -> list[PlayerStats]:
        standings: dict[Player, PlayerStats] = {
            player: PlayerStats(player) for player in self._players
        }

        for m in self.get_finished_matches():
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

        if len(self.get_finished_matches()) == 0:
            self._players = sample(self._players, len(self._players))

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

        for m in self.get_current_matches():
            if m.p1 == p1 and m.p2 == p2:
                m.mod_finish(p1_games_won, p2_games_won)
                break

        self.mod_create_pairing()
        return True
