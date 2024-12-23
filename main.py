from flask import Flask, request, render_template, redirect, url_for
import random
import socket
from collections import OrderedDict

app = Flask(__name__)

# Store event data in memory
players = []  # List of player names
x = []  # List of round results, where each round result is a dict of pairs (p1, p2) as keys and (p1_game_wins, p2_game_wins) as values

# Helper functions
def generate_seating():
    global players
    players = random.sample(players, len(players))

def calculate_pairings():
    if not x:
        return []
    return list(x[-1].keys())

def calculate_results():
    results = {}
    for round_result in x:
        results.update(round_result)
    return results

def calculate_standings():
    standings = [
        {"name": player, "points": 0, "omw": 0.0, "games_won": 0, "games_played": 0}
        for player in players
    ]
    results = calculate_results()
    for match, result in results.items():
        p1, p2 = match.split(" vs ")
        p1_games_won, p2_games_won = result
        for p in standings:
            if p["name"] == p1:
                if p1_games_won > p2_games_won:
                    p["points"] += 3  # Win
                elif p1_games_won == p2_games_won:
                    p["points"] += 1  # Draw
                p["games_won"] += p1_games_won
                p["games_played"] += p1_games_won + p2_games_won
            elif p["name"] == p2:
                if p2_games_won > p1_games_won:
                    p["points"] += 3  # Win
                elif p2_games_won == p1_games_won:
                    p["points"] += 1  # Draw
                p["games_won"] += p2_games_won
                p["games_played"] += p1_games_won + p2_games_won

    # Calculate opponent match win % (OMW)
    for p in standings:
        opponents = [
            op
            for match in results
            for op in match.split(" vs ")
            if p["name"] in match and op != p["name"]
        ]
        opponent_points = [o["points"] for o in standings if o["name"] in opponents]
        p["omw"] = (
            sum(opponent_points) / (len(opponent_points) * 3)
            if opponent_points
            else 0.0
        )

    # Sort standings by points and OMW
    standings.sort(key=lambda x: (-x["points"], -x["omw"]))
    return standings

def calculate_round_number():
    return len(x)

def calculate_pairing_history():
    pairing_history = set()
    for round_result in x:
        for match in round_result.keys():
            pairing_history.add(frozenset(match.split(" vs ")))
    return pairing_history

def generate_pairings():
    global x
    round_number = calculate_round_number() + 1
    pairings = []

    if round_number == 1:
        # Cross pairings for round 1 based on seating
        half = len(players) // 2
        for i in range(half):
            pairings.append((players[i], players[i + half]))

        # Assign a bye if there is an odd number of players
        if len(players) % 2 == 1:
            pairings.append((players[-1], "bye"))
    else:
        # Swiss pairings for subsequent rounds
        standings = calculate_standings()
        unpaired = standings.copy()
        pairing_history = calculate_pairing_history()

        while len(unpaired) > 1:
            player1 = unpaired.pop(0)
            # Find the first opponent that hasn't been played yet
            for i, opponent in enumerate(unpaired):
                if (
                    frozenset({player1["name"], opponent["name"]})
                    not in pairing_history
                ):
                    pairings.append((player1["name"], opponent["name"]))
                    unpaired.pop(i)
                    pairing_history.add(frozenset({player1["name"], opponent["name"]}))
                    break

        # Assign a bye if there is an odd number of players
        if unpaired:
            pairings.append((unpaired[0]["name"], "bye"))

    # Add current pairings to x
    x.append({f"{p1} vs {p2}": (0, 0) for p1, p2 in pairings})

# Routes
@app.route("/")
def index():
    pairings = calculate_pairings()
    results = calculate_results()
    standings = calculate_standings()
    round_number = calculate_round_number()
    pairing_history = calculate_pairing_history()

    # Filter out matches that already have results from the dropdown menu
    pairings_not_submitted = [
        (p1, p2)
        for p1, p2 in pairings
        if f"{p1} vs {p2}" not in results and f"{p2} vs {p1}" not in results
    ]
    return render_template(
        "index.html",
        players=players,
        pairings=pairings,
        pairings_not_submitted=pairings_not_submitted,
        standings=standings,
        round_number=round_number,
    )

@app.route("/add_player", methods=["POST"])
def add_player():
    name = request.form.get("name")
    if name and name not in players:
        players.append(name)
    return redirect(url_for("index"))

@app.route("/start_draft", methods=["POST"])
def start_draft():
    if len(players) >= 2:
        generate_seating()
    return redirect(url_for("index"))

@app.route("/start_round", methods=["POST"])
def start_round():
    if players:
        generate_pairings()
    return redirect(url_for("index"))

@app.route("/submit_result", methods=["POST"])
def submit_result():
    pairings = calculate_pairings()
    for i in range(len(pairings)):
        p1_score = request.form.get(f"p1_score_{i}")
        p2_score = request.form.get(f"p2_score_{i}")
        if p1_score is not None and p2_score is not None:
            p1_score = int(p1_score)
            p2_score = int(p2_score)
            match = f"{pairings[i][0]} vs {pairings[i][1]}"
            x[-1][match] = (p1_score, p2_score)
    generate_pairings()  # Automatically start a new round with new Swiss pairings
    return redirect(url_for("index"))

if __name__ == "__main__":
    # Prepopulate players
    players = ["a", "b", "c", "d", "e", "f", "g", "h", "i"]

    # Generate initial seating and pairings
    generate_seating()
    generate_pairings()

    # Find local IP address
    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)
    print(f"Hosting on http://{local_ip}:5000")
    app.run(host=local_ip, port=5000)
