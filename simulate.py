from statistics import mean
from Tournament import set_now_Berlin_forced, Tournament, now_Berlin
from datetime import timedelta
from random import normalvariate, randint

def roll(a, b):
    assert a <= b
    x = normalvariate(mu = a + 0.5 * (b - a),
                      sigma = 0.25 * (b - a))
    if x < a:
        x = a
    elif x > b:
        x = b
    return x

players = ["a", "b", "c", "d", "e", "f", "g"]

def simulate_tournament():
    mtpg = {p: timedelta(minutes=roll(5, 15)) for p in players} # mean time per game of a player

    x = Tournament(players)
    for i in range(3):
        for p1, p2 in x.get_pairing():
            if "bye" in (p1, p2):
                continue
            p1_games_won = 0
            p2_games_won = 0
            match_time = timedelta()
            for game_number in (1, 2, 3):
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

            set_now_Berlin_forced(x.get_round_start_time(False) + match_time)
            x.mod_submit_result(p1, p2, p1_games_won, p2_games_won)
    x.get_standings(False)

    time_played = {p: timedelta() for p in players}
    tournament_start = x.get_round_start_time(False)
    tournament_end = x.get_round_start_time(False)

    for round_result in x.get_round_results()[0:3]:
        for m in round_result:
            if m.includes("bye"):
                continue
            time_played[m.p1] += m.t_end - m.t_start
            time_played[m.p2] += m.t_end - m.t_start
            tournament_start = min(tournament_start, m.t_start)
            tournament_end = max(tournament_end, m.t_end)

    tournament_duration = tournament_end - tournament_start
    time_waited = {p: tournament_duration - time_played[p] for p in players}

    total_hours_waited = sum(time_waited.values(), start = timedelta()).total_seconds() / 60 / 60
    return total_hours_waited

print(mean(simulate_tournament() for _ in range(100)))
