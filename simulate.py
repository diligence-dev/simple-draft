from statistics import mean
from Tournament import Tournament
from TournamentBase import set_now_Berlin_forced
from datetime import timedelta
from random import normalvariate, randint


def roll(a, b):
    assert a <= b
    x = normalvariate(mu=a + 0.5 * (b - a), sigma=0.25 * (b - a))
    if x < a or x > b:
        return roll(a, b)
    return x


def simulate_tournament(n_players):
    players = ["a", "b", "c", "d", "e", "f", "g", "h", "i", "j", "k", "l"][0:n_players]

    mtpg = {
        p: timedelta(minutes=roll(5, 15)) for p in players
    }  # mean time per game of a player

    x = Tournament(players)
    for round_number in (1, 2, 3):
        results = []
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

            results.append(
                (
                    x.get_round_start_time(False) + match_time,
                    p1,
                    p2,
                    p1_games_won,
                    p2_games_won,
                )
            )

        for t, p1, p2, p1_games_won, p2_games_won in sorted(
            results, key=lambda r: r[0]
        ):
            set_now_Berlin_forced(t)
            x.mod_submit_result(p1, p2, p1_games_won, p2_games_won)
    return x


def total_hours_waited(x: Tournament):
    players = x.get_active_players()
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
    # return tournament_duration.total_seconds() / 60 / 60
    time_waited = {p: tournament_duration - time_played[p] for p in players}

    total_hours_waited = (
        sum(time_waited.values(), start=timedelta()).total_seconds() / 60 / 60
    )
    return total_hours_waited


# a = simulate_tournament(7)
# for m in [m for rr in a.get_round_results() for m in rr]:
#     print(f"{m.t_start} - {m.t_end} --- {m.p1} - {m.p2}")
# print(total_hours_waited(a))

print(mean(total_hours_waited(simulate_tournament(8)) for _ in range(100)))
# 7 player mean total_hours_waited 5.38h
# 7 player mean tournament_duration 2.81h

# 8 player mean total_hours_waited 3.97h
# 8 player mean tournament_duration 2.88h
