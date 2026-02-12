from dataclasses import dataclass
from datetime import datetime
from warnings import warn
from now_Berlin import now_Berlin

Player = str


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

        if self.includes("bye") and (p1_games_won != -1 or p2_games_won != -1):
            warn("Tried to create Match with bye and result; result replaced with 2-0")

        if p1 == "bye":
            self.mod_finish(0, 2)
        elif p2 == "bye":
            self.mod_finish(2, 0)

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
