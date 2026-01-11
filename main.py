from collections import defaultdict
from flask import Flask, request, render_template, redirect, url_for
from Tournament import Tournament, now_Berlin
import copy
import datetime
import pickle
import time

port = 5000

app = Flask(__name__)

global_state_file = f"{datetime.date.today().isoformat()}_events.pickle"

try:
    with open(global_state_file, "rb") as f:
        events = pickle.load(f)
except (FileNotFoundError, pickle.UnpicklingError) as e:

    def empty_event():
        return {"x": Tournament([]), "previous_states": []}

    events = defaultdict(empty_event)
    events[0] = {
        "x": Tournament(["a", "b", "c", "d", "e", "f", "g"]),
        "previous_states": [],
        "last_update": "0",
    }


# event id to Tournament
def id2t(event_id):
    return events[event_id]["x"]


# for QR code
url = "https://chillturtle.pythonanywhere.com"


def save_state(event_id):
    x = copy.deepcopy(events[event_id]["x"])
    events[event_id]["previous_states"].append(x)
    events[event_id]["last_update"] = str(time.time())


def save_global_state():
    with open(global_state_file, "wb") as f:
        pickle.dump(events, f)


def write_state_to_file(event_id):
    with open(f"pickles/{now_Berlin().isoformat()}_{event_id}.pickle", "wb") as f:
        pickle.dump(events[event_id]["x"], f)


def load_state_from_file(event_id, filename):
    x = copy.deepcopy(events[event_id]["x"])
    try:
        with open(filename, "rb") as f:
            events[event_id]["x"] = pickle.load(f)
        events[event_id]["previous_states"].append(x)
    except (FileNotFoundError, pickle.UnpicklingError) as e:
        print(f"Error loading state from file '{filename}': {e}")
    finally:
        save_global_state()


# Routes
@app.route("/")
def index():
    new_event_id = max(events.keys()) + 1
    return render_template(
        "index.html", event_ids=events.keys(), new_event_id=new_event_id
    )


@app.route("/<int:event_id>/")
def tournament_organizer(event_id):
    return render_template(
        "tournament_organizer.html",
        players=id2t(event_id).get_active_players(include_bye=True),
        pairing=id2t(event_id).get_pairing(),
        pairing_with_score=id2t(event_id).get_pairing_with_score(),
        standings=id2t(event_id).get_standings(include_bye=True),
        round_number=id2t(event_id).get_round(),
        event_id=event_id,
        round_results=[
            (p1, p2, s1, s2)
            for round_result in id2t(event_id).get_round_results()
            for (p1, p2), (s1, s2) in round_result.items()
        ],
        url=url,
        round_start_time=id2t(event_id).get_round_start_time(),
    )


@app.route("/<int:event_id>/qr", methods=["POST"])
def qr(event_id):
    global url
    url = request.form.get("url")
    return redirect(url_for("tournament_organizer", event_id=event_id))


@app.route("/<int:event_id>/shuffle_seatings", methods=["POST"])
def shuffle_seatings(event_id):
    save_state(event_id)
    id2t(event_id).mod_shuffle_seatings()
    save_global_state()
    return redirect(url_for("tournament_organizer", event_id=event_id))


@app.route("/<int:event_id>/submit_results", methods=["POST"])
def submit_results(event_id):
    save_state(event_id)
    round_result = {}
    for i, (p1, p2) in enumerate(id2t(event_id).get_pairing()):
        p1_games_won = int(request.form.get(f"p1_games_won_{i+1}"))
        p2_games_won = int(request.form.get(f"p2_games_won_{i+1}"))
        round_result[(p1, p2)] = (p1_games_won, p2_games_won)

    id2t(event_id).mod_submit_results(round_result)

    save_global_state()
    return redirect(url_for("tournament_organizer", event_id=event_id))


# player interface
@app.route("/<int:event_id>/new_player")
def new_player(event_id):
    name = request.args.get("name")
    error_message = None if not name else f"Player '{name}' already exists"
    seconds_in_round = (
        now_Berlin() - id2t(event_id).get_round_start_time(False)
    ).seconds
    return render_template(
        "new_player.html",
        error_message=error_message,
        players=id2t(event_id).get_active_players(),
        already_registered_route=(
            "player"
            if id2t(event_id).get_round() > 1 or seconds_in_round > 30 * 60
            else "draft_seating"
        ),
        event_id=event_id,
    )


@app.route("/<int:event_id>/add_player", methods=["POST"])
def add_player(event_id):
    save_state(event_id)
    name = request.form.get("name")
    name = id2t(event_id).mod_add_player(name)
    if name != "":
        target = "draft_seating_highlight"
    else:
        target = "new_player"

    save_global_state()
    return redirect(url_for(target, event_id=event_id, name=name))


@app.route("/<int:event_id>/drop_player", methods=["POST"])
def drop_player(event_id):
    save_state(event_id)

    name = request.form.get("name")
    name = id2t(event_id).mod_drop_player(name)

    save_global_state()
    return redirect(url_for("tournament_organizer", event_id=event_id))


@app.route("/<int:event_id>/swap_players", methods=["POST"])
def swap_players(event_id):
    save_state(event_id)
    id2t(event_id).mod_swap_players(
        request.form.get("player1"), request.form.get("player2")
    )
    save_global_state()
    return redirect(url_for("tournament_organizer", event_id=event_id))


@app.route("/<int:event_id>/player/<name>")
def player(event_id, name):
    if name not in id2t(event_id).get_active_players():
        return redirect(url_for("new_player", event_id=event_id))

    match = next(
        (
            (p1, p2, s1, s2)
            for (p1, p2), (s1, s2) in id2t(event_id).get_pairing_with_score()
            if name in (p1, p2)
        ),
        None,
    )
    if not match:
        return redirect(url_for("new_player", event_id=event_id))

    seconds_in_round = (
        now_Berlin() - id2t(event_id).get_round_start_time(False)
    ).seconds

    return render_template(
        "player.html",
        p1=match[0],
        p2=match[1],
        s1=match[2],
        s2=match[3],
        name=name,
        standings=id2t(event_id).get_standings(include_bye=False),
        event_id=event_id,
        round_start_time=id2t(event_id).get_round_start_time(),
        show_new_round=seconds_in_round < 180,
        last_update=events[event_id]["last_update"],
    )


@app.route("/<int:event_id>/submit_result", methods=["POST"])
def submit_result(event_id):
    save_state(event_id)

    id2t(event_id).mod_submit_result(
        request.form.get("p1"),
        request.form.get("p2"),
        int(request.form.get("p1_games_won")),
        int(request.form.get("p2_games_won")),
    )

    submitting_player = request.form.get("submitting_player")

    save_global_state()
    return redirect(url_for("player", event_id=event_id, name=submitting_player))


@app.route("/<int:event_id>/draft_seating/<name>")
def draft_seating_highlight(event_id, name):
    if name not in id2t(event_id).get_active_players():
        return redirect(url_for("new_player", event_id=event_id))
    return render_template(
        "draft_seating.html",
        players=id2t(event_id).get_active_players(),
        highlight=name,
        event_id=event_id,
        url=url,
        last_update=events[event_id]["last_update"],
    )


@app.route("/<int:event_id>/undo")
def undo(event_id):
    if events[event_id]["previous_states"]:
        events[event_id]["x"] = events[event_id]["previous_states"].pop()
    save_global_state()
    return redirect(url_for("tournament_organizer", event_id=event_id))


@app.route("/<int:event_id>/load_state", methods=["POST"])
def load_state(event_id):
    filename = request.form.get("filename")
    load_state_from_file(event_id, filename)
    return redirect(url_for("tournament_organizer", event_id=event_id))


@app.route("/<int:event_id>/write_state")
def write_state(event_id):
    write_state_to_file(event_id)
    return redirect(url_for("tournament_organizer", event_id=event_id))


@app.route("/<int:event_id>/lastupdate")
def lastupdate(event_id):
    return events[event_id]["last_update"]


@app.route("/<int:event_id>/standings")
def standings(event_id):
    return render_template(
        "standings.html",
        standings=id2t(event_id).get_standings(include_bye=False),
    )


if __name__ == "__main__":
    app.run(host="localhost", port=port)
