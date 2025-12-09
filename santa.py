"""Secret Santa QR generator.

Configure participants and forbidden pairs, then run the script. It creates
QR codes (one per giver) that reveal their assigned recipient when scanned,
so pairings stay private. Pairings are never printed to the terminal.
"""

from __future__ import annotations

import pathlib
import random
import sys
import urllib.parse
from typing import Dict, List, Optional, Set, Tuple

try:
    import qrcode
except ModuleNotFoundError:  # pragma: no cover - import guard
    sys.stderr.write(
        "The 'qrcode' package is required. Install with: pip install qrcode[pil]\n"
    )
    raise


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
    "Allen",
    "Zoe",
]

# Forbidden bidirectional pairs; order in each tuple does not matter.
# Example: ("Alice", "Bob") blocks Alice->Bob and Bob->Alice.
FORBIDDEN_PAIRS: List[Tuple[str, str]] = [
    ("Chuck", "Laura"),
    ("Rakan", "Leah"),
    ("Sam", "MaryGrace"),
    ("Zoe", "Sav"),
    ("Libby", "Allen"),
]

# Allow reciprocal gifting (A->B and B->A). Set to False to disallow.
ALLOW_RECIPROCAL: bool = True

# Directory where QR codes will be written.
OUTPUT_DIR = pathlib.Path(__file__).parent / "qr_codes"

# Base URL for reveal page; QR codes encode this with query params.
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


# --- QR generation ---------------------------------------------------------


def _qr_payload(giver: str, recipient: str) -> str:
    query = urllib.parse.urlencode({"giver": giver, "recipient": recipient})
    return f"{BASE_URL}?{query}"


def _safe_filename(name: str) -> str:
    return "".join(ch for ch in name if ch.isalnum() or ch in {"-", "_"}) or "unknown"


def write_qr_codes(assignments: Dict[str, str], output_dir: pathlib.Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    for giver, recipient in assignments.items():
        payload = _qr_payload(giver, recipient)
        img = qrcode.make(payload)
        filename = _safe_filename(giver)
        img.save(output_dir / f"{filename}.png")


# --- Entry point -----------------------------------------------------------


def main() -> None:
    if len(set(PARTICIPANTS)) != len(PARTICIPANTS):
        raise ValueError("Participant names must be unique.")

    assignments = generate_pairings()
    write_qr_codes(assignments, OUTPUT_DIR)
    print(f"Created {len(assignments)} QR codes in {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
