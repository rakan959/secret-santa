"""Secret Santa link generator.

Configure participants and forbidden pairs, then run the script. It creates a
CSV mapping each giver to a private URL that embeds the assignment in base64
for the reveal page.
"""

from __future__ import annotations

import base64
import csv
import json
import pathlib
import random
from typing import Dict, List, Optional, Set, Tuple

# --- Configuration ---------------------------------------------------------

# List of participants. Add/remove names as needed.
PARTICIPANTS: List[str] = [
    "Caleb",
    "Chuck",
    "Kelina",
    "Libby",
    "MaryGrace",
    "Laura",
    "John",
    "Rakan",
    "Leah",
    "Sam",
    "Sav",
    "Alan",
    "Zoe",
]

# Forbidden bidirectional pairs; order in each tuple does not matter.
# Example: ("Alice", "Bob") blocks Alice->Bob and Bob->Alice.
FORBIDDEN_PAIRS: List[Tuple[str, str]] = [
    ("Chuck", "Laura"),
    ("Rakan", "Leah"),
    ("Sam", "MaryGrace"),
    ("Zoe", "Sav"),
    ("Libby", "Alan"),
]

# Allow reciprocal gifting (A->B and B->A). Set to False to disallow.
ALLOW_RECIPROCAL: bool = True

# CSV file where assignments will be written.
OUTPUT_CSV = pathlib.Path(__file__).parent / "assignments.csv"

# Base URL for reveal page; links encode assignments in base64.
BASE_URL = "https://rakan959.github.io/secret-santa/index.html"


# --- Pairing logic ---------------------------------------------------------


def _build_forbidden_set(pairs: List[Tuple[str, str]]) -> Set[frozenset[str]]:
    return {frozenset((a, b)) for a, b in pairs}


def _find_assignments(
    participants: List[str],
    forbidden: Set[frozenset[str]],
    allow_reciprocal: bool,
) -> Optional[Dict[str, str]]:
    shuffled = participants[:]
    random.shuffle(shuffled)
    available = participants[:]
    random.shuffle(available)

    def backtrack(
        index: int, remaining: List[str], assignment: Dict[str, str]
    ) -> Optional[Dict[str, str]]:
        if index == len(shuffled):
            return assignment

        giver = shuffled[index]
        candidates = [
            r
            for r in remaining
            if r != giver and frozenset((giver, r)) not in forbidden
        ]
        random.shuffle(candidates)

        for recipient in candidates:
            if not allow_reciprocal and assignment.get(recipient) == giver:
                continue

            assignment[giver] = recipient
            next_remaining = [r for r in remaining if r != recipient]
            result = backtrack(index + 1, next_remaining, assignment)
            if result:
                return result

            assignment.pop(giver, None)

        return None

    return backtrack(0, available, {})


def generate_pairings() -> Dict[str, str]:
    forbidden = _build_forbidden_set(FORBIDDEN_PAIRS)
    max_attempts = 5_000

    for _ in range(max_attempts):
        assignment = _find_assignments(PARTICIPANTS, forbidden, ALLOW_RECIPROCAL)
        if assignment:
            return assignment

    raise RuntimeError(
        "Unable to generate a valid assignment with current constraints."
    )


# --- Link generation -------------------------------------------------------


def build_assignment_url(giver: str, recipient: str) -> str:
    payload = json.dumps(
        {"giver": giver, "recipient": recipient}, separators=(",", ":")
    )
    token = (
        base64.urlsafe_b64encode(payload.encode("utf-8")).decode("ascii").rstrip("=")
    )
    return f"{BASE_URL}?data={token}"


def verify_assignments(assignments: Dict[str, str], participants: List[str]) -> None:
    participant_set = set(participants)
    giver_set = set(assignments.keys())
    recipient_values = list(assignments.values())
    recipient_set = set(recipient_values)

    issues = []

    missing_givers = participant_set - giver_set
    if missing_givers:
        issues.append(f"Missing givers: {sorted(missing_givers)}")

    missing_recipients = participant_set - recipient_set
    if missing_recipients:
        issues.append(f"Missing recipients: {sorted(missing_recipients)}")

    if len(recipient_values) != len(recipient_set):
        issues.append("Duplicate recipients detected")

    extra_givers = giver_set - participant_set
    if extra_givers:
        issues.append(f"Unexpected givers: {sorted(extra_givers)}")

    extra_recipients = recipient_set - participant_set
    if extra_recipients:
        issues.append(f"Unexpected recipients: {sorted(extra_recipients)}")

    if issues:
        raise ValueError("Assignment verification failed; " + "; ".join(issues))

    # Print a brief summary without revealing pairings.
    print(
        f"Verification passed: {len(giver_set)} givers matched to {len(recipient_set)} recipients."
    )


def write_csv(assignments: Dict[str, str], output_csv: pathlib.Path) -> None:
    rows = []
    for giver, recipient in assignments.items():
        rows.append((giver, build_assignment_url(giver, recipient)))

    with output_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["giver", "url"])
        for giver, url in sorted(rows, key=lambda r: r[0].lower()):
            writer.writerow([giver, url])


# --- Entry point -----------------------------------------------------------


def main() -> None:
    if len(set(PARTICIPANTS)) != len(PARTICIPANTS):
        raise ValueError("Participant names must be unique.")

    assignments = generate_pairings()
    verify_assignments(assignments, PARTICIPANTS)
    write_csv(assignments, OUTPUT_CSV)
    print(f"Wrote {len(assignments)} assignment links to {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
