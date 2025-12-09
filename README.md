# Secret Santa Link Generator

Generate Secret Santa pairings with constraints and output a CSV of private reveal links that encode each assignment in URL-safe base64. A static web page (`index.html`) decodes the link and shows the giver/recipient without exposing other pairs.

## How it works
- Pairings are built with backtracking to avoid self-draws, honor bidirectional forbidden pairs, and optionally block reciprocals.
- Each assignment is serialized as `{giver, recipient}`, URL-safe base64 encoded, and appended to the reveal page as `?data=...`.
- A CSV (`assignments.csv`) is written with columns `giver,url` for easy distribution.

## Configuration
Edit `santa.py`:
- `PARTICIPANTS`: list of unique names.
- `FORBIDDEN_PAIRS`: list of tuples; each blocks both directions.
- `ALLOW_RECIPROCAL`: set `False` to prevent A→B when B→A already exists.
- `BASE_URL`: your deployed `index.html` (GitHub Pages URL).

## Setup
```pwsh
# From repo root
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt  # if present; otherwise see deps below
```
Dependencies: `pytest` (tests), standard library only for the script.

## Run
```pwsh
py .\santa.py
```
Outputs:
- `assignments.csv` (giver,url) in the repo root.
- Console shows verification (all givers/recipients covered) and CSV path.

## Reveal page
- Hosted at `index.html` (e.g., GitHub Pages).
- Accepts `?data=<urlsafe_base64>` where payload is JSON `{"giver":"Alice","recipient":"Bob"}` (padding optional). Legacy `?giver=&recipient=` still works.

## Testing
```pwsh
py -m pytest
```
Suite covers pairing rules, reciprocity flag, impossible constraints, randomness variety, scalability, verification, base64 link encoding, and CSV output.

## Notes
- If constraints make pairing impossible, the script raises `RuntimeError`.
- Verification runs every time and fails fast on missing/duplicate/extra givers or recipients.
- Keep names unique; duplicates are rejected.
