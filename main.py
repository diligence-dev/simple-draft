from flask import Flask, request, render_template, redirect, url_for
import random
from collections import defaultdict, OrderedDict
from statistics import mean
import networkx as nx
import copy
import pickle
import datetime
import time
from warnings import warn
from zoneinfo import ZoneInfo

port = 5000

app = Flask(__name__)


def pair_and_result(p1, p2):
    if p1 == "bye":
        return ((p1, p2), (0, 2))
    elif p2 == "bye":
        return ((p1, p2), (2, 0))
    else:
        return ((p1, p2), (-1, -1))


def now_Berlin():
    return datetime.datetime.now(ZoneInfo("Europe/Berlin"))


class Tournament:
    def __init__(self, players):
        self._dropped_players = []
        self._round_results = []
        self._players = ["bye"]
        self._round_start_times = []
        for player in players:
            self.mod_add_player(player)

    def get_round_results(self):
        return self._round_results

    def get_round_start_time(self):
        return self._round_start_times[-1]

    def get_active_players(self, include_bye=False):
        return [
            p
            for p in self._players
            if p not in self._dropped_players and (p != "bye" or include_bye)
        ]

    def get_pairing(self):
        if len(self._round_results) == 0:
            return []
        return list(self._round_results[-1].keys())

    def get_pairing_with_score(self):
        if len(self._round_results) == 0:
            return []
        return self._round_results[-1].items()

    def get_round(self):
        return len(self._round_results)

    def get_standings(self, include_bye):
        standings = {
            player: {
                "points": 0,
                "games_won": 0,
                "games_played": 0,
                "matches_played": 0,
            }
            for player in self._players
        }

        for round_results in self._round_results:
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
        for player in self._players:
            p = standings[player]
            if p["matches_played"] == 0:
                standings[player]["mw"] = -100
            else:
                standings[player]["mw"] = max(
                    0.333, p["points"] / (3 * p["matches_played"])
                )

        # Calculate opponent match winrate (OMW)
        for player in self._players:
            opponents = [
                match[0] if match[1] == player else match[1]
                for round_results in self._round_results
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
        for player in self._players:
            p = standings[player]
            if p["games_played"] == 0:
                standings[player]["gw"] = -100
            else:
                standings[player]["gw"] = max(0.333, p["games_won"] / p["games_played"])

        # Calculate opponent game winrate (OGW)
        for player in self._players:
            opponents = [
                match[0] if match[1] == player else match[1]
                for round_results in self._round_results
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
        standings = [
            {"name": player, **stats}
            for player, stats in standings.items()
            if player != "bye" or include_bye
        ]
        standings.sort(key=lambda x: (-x["points"], -x["omw"], -x["gw"], -x["ogw"]))
        return standings

    def mod_submit_results(self, round_result):
        if list(round_result.keys()) != self.get_pairing():
            warn("wrong pairing")
            return False

        for (p1, p2), (games_won_p1, games_won_p2) in round_result.items():
            ok = self.mod_submit_result(p1, p2, games_won_p1, games_won_p2)
            if not ok:
                return False

        return True

    def mod_shuffle_seatings(self):
        if self.get_round() >= 2:
            warn("won't shuffle seatings after round 1")
            return False

        self._players = random.sample(self._players, len(self._players))
        self.mod_replace_pairing()
        return True

    def mod_add_player(self, player_to_add):
        player_to_add = player_to_add.replace("/", "|")
        player_to_add = player_to_add.replace("?", "")
        player_to_add = player_to_add.replace("%", "")
        if player_to_add in self.get_active_players() or player_to_add == "bye":
            return ""

        if player_to_add in self._dropped_players:
            assert player_to_add in self._players
            self._dropped_players.remove(player_to_add)
        else:
            self._players.append(player_to_add)

        if self.get_round() <= 1:
            self.mod_shuffle_seatings()

        self.mod_replace_pairing(new_player=player_to_add)

        return player_to_add

    def mod_drop_player(self, player_to_drop):
        if player_to_drop not in self._players or player_to_drop == "bye":
            return False

        self._dropped_players.append(player_to_drop)
        self.mod_replace_pairing()
        return True

    def mod_swap_players(self, player1, player2):
        def f(p1, p2, g1, g2):
            if p1 == player1:
                return ((player2, p2), (-1, -1))
            if p2 == player1:
                return ((p1, player2), (-1, -1))
            if p1 == player2:
                return ((player1, p2), (-1, -1))
            if p2 == player2:
                return ((p1, player1), (-1, -1))
            return ((p1, p2), (g1, g2))

        self._round_results[-1] = dict(
            f(p1, p2, g1, g2) for (p1, p2), (g1, g2) in self._round_results[-1].items()
        )

    def mod_submit_result(self, p1, p2, p1_games_won, p2_games_won):
        if (p1, p2) not in self.get_pairing():
            warn(f"{p1} vs {p2} not in pairing")
            return False
        if p1_games_won not in (0, 1, 2) or p2_games_won not in (0, 1, 2):
            warn("games won not in (0, 1, 2)")
            return False
        elif p1_games_won + p2_games_won > 3:
            warn("total games > 3")
            return False

        self._round_results[-1][(p1, p2)] = (p1_games_won, p2_games_won)

        if all(
            s1 in (0, 1, 2) and s2 in (0, 1, 2)
            for _, (s1, s2) in self.get_pairing_with_score()
        ):
            return self.mod_create_pairing()

        return True

    def mod_create_pairing(self):
        self._round_start_times.append(now_Berlin().strftime("%H:%M"))
        if self.get_round() == 0:
            players = self.get_active_players(include_bye=True)
            if len(players) % 2 == 1:
                players.remove("bye")

            n_halved = int(len(players) / 2)
            self._round_results.append(
                OrderedDict(
                    pair_and_result(players[i], players[i + n_halved])
                    for i in range(n_halved)
                )
            )
            return True

        # Swiss pairing using maximum weight matching
        standings = self.get_standings(include_bye=True)
        active_players = self.get_active_players(include_bye=True)
        if len(active_players) % 2 == 1:
            active_players.remove("bye")
        # get players in standings order
        players = [p["name"] for p in standings if p["name"] in active_players]
        pairing_history = {
            frozenset(match)
            for round_results in self._round_results
            for match in round_results
        }

        G = nx.Graph()
        G.add_nodes_from(players)

        # Add edges with weights based on points
        for i, p1 in enumerate(players):
            for p2 in players[i + 1 :]:
                if frozenset({p1, p2}) not in pairing_history:
                    score_diff = abs(
                        standings[i]["points"] - standings[players.index(p2)]["points"]
                    )
                    G.add_edge(p1, p2, weight=-score_diff * score_diff)

        pairings = list(nx.max_weight_matching(G, maxcardinality=True))

        # Add current pairings to x
        self._round_results.append(
            OrderedDict(pair_and_result(p1, p2) for p1, p2 in pairings)
        )
        return True

    def mod_replace_pairing(self, new_player=None):
        if (
            new_player is not None
            and len(self.get_active_players(include_bye=True)) % 2 == 1
        ):
            # new player replaces bye
            def replace_bye(pair, result):
                a, b = pair
                if a == "bye":
                    return (new_player, b), (-1, -1)
                elif b == "bye":
                    return (a, new_player), (-1, -1)
                return (a, b), result

            self._round_results[-1] = OrderedDict(
                replace_bye(pair, result)
                for pair, result in self._round_results[-1].items()
            )
            return True

        if self.get_round() >= 1:
            self._round_results.pop()
        return self.mod_create_pairing()


def empty_event():
    return {"x": Tournament([]), "previous_states": []}


try:
    with open("events.pickle", "rb") as f:
        events = pickle.load(f)
except (FileNotFoundError, pickle.UnpicklingError) as e:
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
    with open(f"events.pickle", "wb") as f:
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
    return render_template(
        "new_player.html",
        error_message=error_message,
        players=id2t(event_id).get_active_players(),
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


if __name__ == "__main__":
    app.run(host="localhost", port=port)
