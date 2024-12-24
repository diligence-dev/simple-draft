from flask import Flask, request, render_template, redirect, url_for
import random
import socket
from collections import OrderedDict
from statistics import mean
import re

app = Flask(__name__)

def make_round_result(players):
    if len(players) % 2 == 1:
        players.append("bye")
    round_results = OrderedDict(((players[i], players[i + 1]), (-1, -1)) for i in range(0, len(players), 2))
    if list(round_results.keys())[-1][1] == "bye":
        round_results[list(round_results.keys())[-1]] = (2, 0)
    return round_results

# List of round results, where each round result is an OrderedDict of pairs (p1, p2) as keys and (p1_game_wins, p2_game_wins) as values
x = [make_round_result(["a", "b", "c", "d", "e", "f", "g", "h", "i"])]


def get_players():
    return([p for p, o in x[0].keys() if o != "bye"] + [p if p != "bye" else o for o, p in x[0].keys()])


def shuffle_seating():
    global x
    assert len(x) == 1
    x[0] = make_round_result(random.sample(get_players(), len(get_players())))


def get_pairing():
    return list(x[-1].keys())

def calculate_standings():
    standings = {player: {"points": 0, "games_won": 0, "games_played": 0, "matches_played": 0}
                 for player in get_players() + ["bye"]}

    for round_results in x:
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

    del standings["bye"]

    # Calculate player match winrate
    for player in get_players():
        p = standings[player]
        if p["matches_played"] == 0:
            standings[player]["match_winrate"] = 1.0
        else:
            standings[player]["match_winrate"] = max(0.33, p["points"] / (3 * p["matches_played"]))

    # Calculate opponent match winrate (OMW)
    for player in get_players():
        opponents = [
            match[0] if match[1] == player else match[1]
            for round_results in x
            for match in round_results.keys()
            if player in match and "bye" not in match
        ]
        if not opponents:
            standings[player]["omw"] = 1.0
        else:
            standings[player]["omw"] = mean(standings[opponent]["match_winrate"] for opponent in opponents)

    # Sort standings by points and OMW
    standings = [{"name": player, **stats} for player, stats in standings.items()]
    standings.sort(key=lambda x: (-x["points"], -x["omw"]))
    return standings

def new_round():
    global x
    pairings = []

    # Swiss pairing
    standings = calculate_standings()
    unpaired = get_players()
    pairing_history = {frozenset(match) for round_results in x for match in round_results}

    while len(unpaired) > 1:
        p1 = unpaired.pop(0)
        # Find the first opponent that hasn't been played yet
        for i, opponent in enumerate(unpaired):
            if frozenset({p1, opponent}) not in pairing_history:
                pairings.append((p1, opponent))
                unpaired.pop(i)
                break

    # Assign a bye if there is an odd number of players
    if unpaired:
        pairings.append((unpaired[0], "bye"))

    # Add current pairings to x
    x.append(OrderedDict(((p1, p2), (-1, -1) if p2 != "bye" else (2, 0)) for p1, p2 in pairings))

def pairings_not_submitted():
    return [pair for pair in get_pairing() if x[-1][pair][0] not in (0, 1, 2) or x[-1][pair][1] not in (0, 1, 2)]

# Routes
@app.route("/")
def index():
    return render_template(
        "index.html",
        players=get_players(),
        pairings=get_pairing(),
        pairings_not_submitted=pairings_not_submitted(),
        standings=calculate_standings(),
        round_number=len(x),
    )

@app.route("/start_draft", methods=["POST"])
def start_draft():
    shuffle_seating()
    return redirect(url_for("index"))

@app.route("/submit_results", methods=["POST"])
def submit_results():
    for i, (p1, p2) in enumerate(get_pairing()):
        p1_games_won = int(request.form.get(f"p1_games_won_{i+1}"))
        p2_games_won = int(request.form.get(f"p2_games_won_{i+1}"))

        if p1_games_won in [0, 1, 2] and p2_games_won in [0, 1, 2]:
            x[-1][(p1, p2)] = (p1_games_won, p2_games_won)

    new_round()
    return redirect(url_for("index"))


# player interface

@app.route("/new_player")
def new_player():
    return render_template("new_player.html")

@app.route("/add_player", methods=["POST"])
def add_player():
    name = request.form.get("name")
    name = re.sub(r'[^A-Za-z]', '_', name)
    if name not in get_players():
        global x
        x[0] = make_round_result(get_players() + [name])
    return redirect(url_for("index"))

@app.route("/player/<name>")
def player(name):
    if name not in get_players():
        return redirect(url_for("index"))

    match = next(((p1, p2) for p1, p2 in get_pairing() if name in (p1, p2)), None)
    if not match:
        return redirect(url_for("index"))

    return render_template("player.html", p1=match[0], p2=match[1],
                           standings=calculate_standings(),
                           players=get_players())

@app.route("/submit_result", methods=["POST"])
def submit_result():
    p1 = request.form.get(f"p1")
    p2 = request.form.get(f"p2")
    p1_games_won = request.form.get(f"p1_games_won")
    p2_games_won = request.form.get(f"p2_games_won")
    if p1_games_won in ["0", "1", "2"] and p2_games_won in ["0", "1", "2"]:
        x[-1][(p1, p2)] = (int(p1_games_won), int(p2_games_won))

    return redirect(url_for("index"))



if __name__ == "__main__":
    # Generate initial seating and pairings
    shuffle_seating()

    # Find local IP address
    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)
    print(f"Hosting on http://{local_ip}:5000/player/a")
    app.run(host=local_ip, port=5000)
