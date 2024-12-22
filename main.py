from flask import Flask, request, render_template, redirect, url_for
import random
import socket

app = Flask(__name__)

# Store event data in memory
players = []  # List of player names
seating = []  # Draft seating order
pairings = []  # Current round pairings
results = {}  # Match results
standings = []  # Standings by points and tiebreakers
round_number = 0  # Current round
pairing_history = set()  # Track all previous pairings


# Helper functions
def generate_seating():
    global seating
    seating = random.sample(players, len(players))


def generate_pairings():
    global pairings, round_number, pairing_history
    round_number += 1
    pairings = []

    if round_number == 1:
        # Cross pairings for round 1 based on seating
        half = len(seating) // 2
        for i in range(half):
            pairings.append((seating[i], seating[i + half]))

        # Assign a bye if there is an odd number of players
        if len(seating) % 2 == 1:
            pairings.append((seating[-1], "bye"))
    else:
        # Swiss pairings for subsequent rounds
        unpaired = standings.copy()

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

    # Add current pairings to pairing history
    for match in pairings:
        pairing_history.add(frozenset(match))


def update_standings():
    global standings
    # Initialize/reset standings
    if not standings:
        standings = [
            {"name": player, "points": 0, "omw": 0.0, "games_won": 0, "games_played": 0}
            for player in players
        ]

    # Update points and tiebreakers
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


# Routes
@app.route("/")
def index():
    # Filter out matches that already have results from the dropdown menu
    pairings_not_submitted = [
        (p1, p2)
        for p1, p2 in pairings
        if f"{p1} vs {p2}" not in results and f"{p2} vs {p1}" not in results
    ]
    return render_template(
        "index.html",
        players=players,
        seating=seating,
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
    if seating:
        generate_pairings()
    return redirect(url_for("index"))


@app.route("/submit_result", methods=["POST"])
def submit_result():
    for i in range(len(pairings)):
        p1_score = request.form.get(f"p1_score_{i}")
        p2_score = request.form.get(f"p2_score_{i}")
        if p1_score is not None and p2_score is not None:
            p1_score = int(p1_score)
            p2_score = int(p2_score)
            match = f"{pairings[i][0]} vs {pairings[i][1]}"
            results[match] = (p1_score, p2_score)
    update_standings()
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
