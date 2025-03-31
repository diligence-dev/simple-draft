from flask import Flask, request, render_template, redirect, url_for
import random
from collections import defaultdict, OrderedDict
from statistics import mean
import re
import networkx as nx
import copy
import pickle
from datetime import datetime

port = 5000

app = Flask(__name__)

def make_round_result(players):
    if len(players) % 2 == 1:
        players.append("bye")
    round_results = OrderedDict(
        ((players[i], players[i + 1]), (-1, -1)) for i in range(0, len(players), 2)
    )
    if len(players) > 0 and players[-1] == "bye":
        round_results[(players[-2], "bye")] = (2, 0)
    return round_results


# Dictionary to store state for each event
events = defaultdict(
    lambda: {"x": [make_round_result([])], "previous_states": []}
)
events["0"] = {"x": [make_round_result(["a", "b", "c", "d", "e", "f", "g", "h"])], "previous_states": []}


def save_state(event_id):
    x = copy.deepcopy(events[event_id]["x"])
    events[event_id]["previous_states"].append(x)
    with open(f"{datetime.now().isoformat()}_{event_id}.pickle", "wb") as f:
        pickle.dump(x, f)

def load_state_from_file(event_id, filename):
    events[event_id]["previous_states"].append(events[event_id]["x"])
    try:
        with open(filename, "rb") as f:
            events[event_id]["x"] = pickle.load(f)
    except (FileNotFoundError, pickle.UnpicklingError) as e:
        print(f"Error loading state from file '{filename}': {e}")

def get_players(event_id):
    x = events[event_id]["x"]
    return [p1 for p1, _ in x[0].keys()] + [p2 for _, p2 in x[0].keys()]

def get_players_no_bye(event_id):
    return [p for p in get_players(event_id) if p != "bye"]

def get_pairing(event_id):
    return list(events[event_id]["x"][-1].keys())


def get_pairing_with_score(event_id):
    return events[event_id]["x"][-1].items()


def calculate_standings(event_id):
    x = events[event_id]["x"]
    standings = {
        player: {"points": 0, "games_won": 0, "games_played": 0, "matches_played": 0}
        for player in get_players(event_id)
    }

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

    # Calculate player match winrate
    for player in get_players(event_id):
        p = standings[player]
        if p["matches_played"] == 0:
            standings[player]["mw"] = -100
        else:
            standings[player]["mw"] = max(
                0.333, p["points"] / (3 * p["matches_played"])
            )

    # Calculate opponent match winrate (OMW)
    for player in get_players(event_id):
        opponents = [
            match[0] if match[1] == player else match[1]
            for round_results in x
            for match, result in round_results.items()
            if player in match and "bye" not in match and result != (-1, -1)
        ]
        if not opponents:
            standings[player]["omw"] = 0
        else:
            standings[player]["omw"] = mean(
                standings[opponent]["mw"] for opponent in opponents
            )

    # Calculate game winrate (GW)
    for player in get_players(event_id):
        p = standings[player]
        if p["games_played"] == 0:
            standings[player]["gw"] = -100
        else:
            standings[player]["gw"] = max(
                0.333, p["games_won"] / p["games_played"]
            )

    # Calculate opponent game winrate (OGW)
    for player in get_players(event_id):
        opponents = [
            match[0] if match[1] == player else match[1]
            for round_results in x
            for match, result in round_results.items()
            if player in match and "bye" not in match and result != (-1, -1)
        ]
        if not opponents:
            standings[player]["ogw"] = 0
        else:
            standings[player]["ogw"] = mean(
                standings[opponent]["gw"] for opponent in opponents
            )

    # Sort standings by points and OMW
    standings = [{"name": player, **stats} for player, stats in standings.items()]
    standings.sort(key=lambda x: (-x["points"], -x["omw"], -x["gw"], -x["ogw"]))
    return standings


def new_round(event_id):
    save_state(event_id)
    x = events[event_id]["x"]

    # Swiss pairing using maximum weight matching
    standings = calculate_standings(event_id)
    players = [p["name"] for p in standings]  # in standings order
    pairing_history = {
        frozenset(match) for round_results in x for match in round_results
    }

    # Create a graph
    G = nx.Graph()
    G.add_nodes_from(players)

    # Add edges with weights based on points
    for i, p1 in enumerate(players):
        for p2 in players[i + 1 :]:
            if frozenset({p1, p2}) not in pairing_history:
                score_diff = abs(
                    standings[i]["points"] - standings[players.index(p2)]["points"]
                )
                G.add_edge(p1, p2, weight=-score_diff*score_diff)

    # Find the maximum weight matching
    matching = nx.max_weight_matching(G, maxcardinality=True)

    # Convert matching to pairings
    pairings = list(matching)

    def prefill(p1, p2):
        if p1 == "bye":
            return (0, 2)
        elif p2 == "bye":
            return (2, 0)
        else:
            return (-1, -1)

    # Add current pairings to x
    x.append(
        OrderedDict(
            ((p1, p2), prefill(p1, p2)) for p1, p2 in pairings
        )
    )


# Routes
@app.route("/<event_id>/")
def index(event_id):
    return render_template(
        "index.html",
        players=get_players(event_id),
        pairing=get_pairing(event_id),
        pairing_with_score=get_pairing_with_score(event_id),
        standings=calculate_standings(event_id),
        round_number=len(events[event_id]["x"]),
        event_id=event_id,
        round_results=[(p1, p2, s1, s2) for round_result in events[event_id]["x"] for (p1, p2), (s1, s2) in round_result.items()],
    )


@app.route("/<event_id>/qr", methods=["POST"])
def qr(event_id):
    url = request.form.get("url")
    return render_template(
        "qr.html", url=f"{url}/{event_id}/new_player",
        players=get_players(event_id)
    )


@app.route("/<event_id>/shuffle_seatings", methods=["POST"])
def shuffle_seatings(event_id):
    save_state(event_id)
    x = events[event_id]["x"]
    assert len(x) == 1
    x[0] = make_round_result(
        random.sample(get_players(event_id), len(get_players(event_id)))
    )
    return redirect(url_for("index", event_id=event_id))


@app.route("/<event_id>/submit_results", methods=["POST"])
def submit_results(event_id):
    save_state(event_id)
    for i, (p1, p2) in enumerate(get_pairing(event_id)):
        p1_games_won = int(request.form.get(f"p1_games_won_{i+1}"))
        p2_games_won = int(request.form.get(f"p2_games_won_{i+1}"))

        if p1_games_won in [0, 1, 2] and p2_games_won in [0, 1, 2]:
            events[event_id]["x"][-1][(p1, p2)] = (p1_games_won, p2_games_won)

    new_round(event_id)
    return redirect(url_for("index", event_id=event_id))


# player interface
@app.route("/<event_id>/new_player")
def new_player(event_id):
    name = request.args.get("name")
    error_message = None if not name else f"Player '{name}' already exists"
    return render_template(
        "new_player.html",
        error_message=error_message,
        players=get_players(event_id),
        event_id=event_id,
    )


@app.route("/<event_id>/add_player", methods=["POST"])
def add_player(event_id):
    save_state(event_id)
    name = request.form.get("name")
    name = re.sub(r"[^A-Za-z]", "_", name)
    if name not in get_players(event_id) and len(events[event_id]["x"]) == 1:
        events[event_id]["x"][0] = make_round_result(get_players_no_bye(event_id) + [name])
        return redirect(
            url_for("draft_seating_highlight", event_id=event_id, name=name)
        )
    else:
        return redirect(url_for("new_player", event_id=event_id, name=name))


@app.route("/<event_id>/player/<name>")
def player(event_id, name):
    if name not in get_players(event_id):
        return redirect(url_for("new_player", event_id=event_id))

    match = next(
        (
            (p1, p2, s1, s2)
            for (p1, p2), (s1, s2) in get_pairing_with_score(event_id)
            if name in (p1, p2)
        ),
        None,
    )
    if not match:
        return redirect(url_for("index", event_id=event_id))

    return render_template(
        "player.html",
        p1=match[0],
        p2=match[1],
        s1=match[2],
        s2=match[3],
        name=name,
        standings=calculate_standings(event_id),
        event_id=event_id,
    )


@app.route("/<event_id>/submit_result", methods=["POST"])
def submit_result(event_id):
    save_state(event_id)
    p1 = request.form.get("p1")
    p2 = request.form.get("p2")
    p1_games_won = request.form.get("p1_games_won")
    p2_games_won = request.form.get("p2_games_won")
    submitting_player = request.form.get("submitting_player")

    if (
        p1_games_won in ["0", "1", "2"]
        and p2_games_won in ["0", "1", "2"]
        and (p1_games_won != "2" or p2_games_won != "2")
        and (p1, p2) in events[event_id]["x"][-1].keys()
    ):
        events[event_id]["x"][-1][(p1, p2)] = (int(p1_games_won), int(p2_games_won))

    return redirect(url_for("player", event_id=event_id, name=submitting_player))


@app.route("/<event_id>/draft_seating")
def draft_seating(event_id):
    return render_template(
        "draft_seating.html",
        players=get_players_no_bye(event_id),
        highlight=None,
        event_id=event_id,
    )


@app.route("/<event_id>/draft_seating/<name>")
def draft_seating_highlight(event_id, name):
    if name not in get_players(event_id):
        return redirect(url_for("draft_seating", event_id=event_id))
    return render_template(
        "draft_seating.html",
        players=get_players_no_bye(event_id),
        highlight=name,
        event_id=event_id,
    )


@app.route("/<event_id>/undo")
def undo(event_id):
    if events[event_id]["previous_states"]:
        events[event_id]["x"] = events[event_id]["previous_states"].pop()
    return redirect(url_for("index", event_id=event_id))


@app.route("/<event_id>/load_state", methods=["POST"])
def load_state(event_id):
    filename = request.form.get("filename")
    load_state_from_file(event_id, filename)
    return redirect(url_for("index", event_id=event_id))


if __name__ == "__main__":
    app.run(host="localhost", port=port)
