from flask import Flask, request, jsonify, render_template
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
            pairings.append((seating[-1], 'bye'))
    else:
        # Swiss pairings for subsequent rounds
        sorted_players = sorted(standings, key=lambda x: (-x['points'], -x['omw']))
        unpaired = sorted_players.copy()

        while len(unpaired) > 1:
            player1 = unpaired.pop(0)
            # Find the first opponent that hasn't been played yet
            for i, opponent in enumerate(unpaired):
                if frozenset({player1['name'], opponent['name']}) not in pairing_history:
                    pairings.append((player1['name'], opponent['name']))
                    unpaired.pop(i)
                    pairing_history.add(frozenset({player1['name'], opponent['name']}))
                    break

        # Assign a bye if there is an odd number of players
        if unpaired:
            pairings.append((unpaired[0]['name'], 'bye'))

    # Add current pairings to pairing history
    for match in pairings:
        if 'bye' not in match:
            pairing_history.add(frozenset(match))

def update_standings():
    global standings
    # Initialize/reset standings
    standings = [{'name': player, 'points': 0, 'omw': 0.0, 'games_won': 0, 'games_played': 0} for player in players]

    # Update points and tiebreakers
    for match, result in results.items():
        p1, p2 = match.split(' vs ')
        p1_points, p2_points = result
        for p in standings:
            if p['name'] == p1:
                p['points'] += p1_points
                p['games_won'] += p1_points
                p['games_played'] += sum(result)
            elif p['name'] == p2:
                p['points'] += p2_points
                p['games_won'] += p2_points
                p['games_played'] += sum(result)

    # Calculate opponent match win % (OMW)
    for p in standings:
        opponents = [op for match in results for op in match.split(' vs ') if p['name'] in match and op != p['name']]
        opponent_points = [o['points'] for o in standings if o['name'] in opponents]
        p['omw'] = sum(opponent_points) / (len(opponent_points) * 3) if opponent_points else 0.0

# Routes
@app.route('/')
def index():
    return render_template('index.html', players=players, seating=seating, pairings=pairings, standings=standings, round_number=round_number)

@app.route('/add_player', methods=['POST'])
def add_player():
    name = request.form.get('name')
    if name and name not in players:
        players.append(name)
        return jsonify({'success': True, 'message': f'Player {name} added.'})
    return jsonify({'success': False, 'message': 'Player name missing or already added.'})

@app.route('/start_draft', methods=['POST'])
def start_draft():
    if len(players) < 2:
        return jsonify({'success': False, 'message': 'At least 2 players are required to start the draft.'})
    generate_seating()
    return jsonify({'success': True, 'seating': seating})

@app.route('/start_round', methods=['POST'])
def start_round():
    if not seating:
        return jsonify({'success': False, 'message': 'Draft not started yet.'})
    generate_pairings()
    return jsonify({'success': True, 'pairings': pairings})

@app.route('/submit_result', methods=['POST'])
def submit_result():
    match = request.form.get('match')
    p1_score = int(request.form.get('p1_score'))
    p2_score = int(request.form.get('p2_score'))
    if match and p1_score >= 0 and p2_score >= 0:
        results[match] = (p1_score, p2_score)
        update_standings()
        return jsonify({'success': True, 'message': 'Result submitted successfully.'})
    return jsonify({'success': False, 'message': 'Invalid input.'})

@app.route('/standings', methods=['GET'])
def get_standings():
    return jsonify({'success': True, 'standings': standings})

if __name__ == '__main__':
    # Find local IP address
    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)
    print(f"Hosting on http://{local_ip}:5000")
    app.run(host=local_ip, port=5000)
