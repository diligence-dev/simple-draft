# simple-draft
*A lightweight, no-frills Magic: The Gathering draft / tournament organizer.*

## Overview
**simple-draft** is designed for casual Magic: The Gathering drafts. The philosophy is: no barriers, no unnecessary complexity, just a straightforward tool for generating seatings and pairings, submitting results, calculating tiebreakers and standings.

- 🚫 No passwords or accounts
- ✅ Works in any browser
- ♻️ Each table's state is reset daily (after being archived on the server)

⚠️ **Disclaimer:** This app is for casual drafts only and assumes that all players use the app in good faith. Opening the admin view for any table and making changes is trivial, so if someone wants to sabotage, they can easily do so. Thus, the app is definitely unsuitable for high-stakes drafts. It has been tested with 3 tables and 20+ players and works reliably, but no guarantees are provided.

---

## How It Works

The app is written in Python using the flask framework and hosted at https://www.pythonanywhere.com/

### Joining a Table
- Each table has a unique ID number (e.g. 99) which is part of the link.
- If you want to try the app, please use a random table number > 100.
- If you want to regularly use the same table, ask the developer if you know them, or create a github issue.
- To join, open the following link (replace 99 with your table id):
https://chillturtle.pythonanywhere.com/99/new_player
- Enter your name. A QR code will appear that others can scan to join quickly.
- Multiple players can join using the same device/browser, just open a separate tab for each player.
- Once everyone has joined, everyone should refresh the website to see the **seatings**.

---

### Rejoining if Disconnected
If someone closes the page or loses connection:
- Go back to the original link:
https://chillturtle.pythonanywhere.com/99/new_player
- Do not enter your name again, but instead select your name from the list to rejoin.

---

### Submitting Results
- Players can submit results themselves.
- Once all results are in, the next round starts automatically.
- Standings show who hasn't submitted results yet (see the **Matches Played** column).

---

### Admin View
Most of the time, you won't need the admin view at all, but it's available here:
https://chillturtle.pythonanywhere.com/99

**Admin features:**
- Undo the last change to a table's state (as many times as needed)
- Overwrite reported match results
- Add players after the draft started (experimental)
- Drop players
- Manually edit pairing

---

### Round Timing
The app does not include a round timer, so set one separately if needed. However, the app shows when the draft/round 2/round 3 started, so you can set a timer later in case you forgot to.

---

## Acknowledgement
Thanks to the folks developing the tools used (especially Python & flask) and to the pythonanywhere people for hosting the app!
