from statistics import mean
from Tournament import set_now_Berlin_forced, Tournament, now_Berlin
from datetime import timedelta
from random import normalvariate, randint


def roll(a, b):
    assert a <= b
    x = normalvariate(mu=a + 0.5 * (b - a), sigma=0.25 * (b - a))
    if x < a:
        x = a
    elif x > b:
        x = b
    return x


def simulate_tournament(n_players):
    players = ["a", "b", "c", "d", "e", "f", "g", "h", "i", "j", "k", "l"][0:n_players]

    mtpg = {
        p: timedelta(minutes=roll(5, 15)) for p in players
    }  # mean time per game of a player

    x = Tournament(players)
    while not x.is_finished():
        for m in x.get_current_matches():
            p1 = m.p1
            p2 = m.p2
            p1_games_won = 0
            p2_games_won = 0
            match_time = timedelta()
            for _ in range(3):  # three games
                p1_time = roll(mtpg[p1] - 0.5 * mtpg[p1], mtpg[p1] + 0.5 * mtpg[p1])
                p2_time = roll(mtpg[p2] - 0.5 * mtpg[p2], mtpg[p2] + 0.5 * mtpg[p2])
                match_time += p1_time + p2_time
                if match_time > timedelta(minutes=60):
                    match_time = timedelta(minutes=60)
                    break

                if randint(1, 2) == 1:
                    p1_games_won += 1
                else:
                    p2_games_won += 1

                if p1_games_won == 2 or p2_games_won == 2:
                    break

            set_now_Berlin_forced(m.t_start + match_time)
            x.mod_submit_result(p1, p2, p1_games_won, p2_games_won)

    time_played = {p: timedelta() for p in players}

    for m in x.get_finished_matches():
        time_played[m.p1] += m.t_end - m.t_start
        time_played[m.p2] += m.t_end - m.t_start

    tournament_start = min(m.t_start for m in x.get_finished_matches())
    tournament_end = max(m.t_end for m in x.get_finished_matches())
    tournament_duration = tournament_end - tournament_start
    time_waited = {p: tournament_duration - time_played[p] for p in players}

    total_hours_waited = (
        sum(time_waited.values(), start=timedelta()).total_seconds() / 60 / 60
    )
    return total_hours_waited


print(mean(simulate_tournament(7) for _ in range(100)))
