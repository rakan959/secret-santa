"""Tests for santa.py."""

import base64
import csv
import json
import random
from typing import Dict
from urllib.parse import parse_qs, urlparse

import pytest

import santa


def _patch_participants(monkeypatch, names):
    monkeypatch.setattr(santa, "PARTICIPANTS", list(names))


def _patch_forbidden(monkeypatch, pairs):
    monkeypatch.setattr(santa, "FORBIDDEN_PAIRS", list(pairs))


def _patch_allow_recip(monkeypatch, value: bool):
    monkeypatch.setattr(santa, "ALLOW_RECIPROCAL", value)


def test_build_forbidden_set_bidirectional():
    result = santa._build_forbidden_set([("A", "B"), ("B", "C")])
    assert frozenset({"A", "B"}) in result
    assert frozenset({"B", "A"}) in result  # same frozenset works both ways
    assert frozenset({"B", "C"}) in result


def test_generate_pairings_respects_forbidden_and_no_self(monkeypatch):
    _patch_participants(monkeypatch, ["A", "B", "C", "D"])
    _patch_forbidden(monkeypatch, [("A", "B")])
    _patch_allow_recip(monkeypatch, True)
    random.seed(42)

    assignment = santa.generate_pairings()

    assert set(assignment.keys()) == {"A", "B", "C", "D"}
    assert all(giver != recipient for giver, recipient in assignment.items())
    assert frozenset({"A", assignment["A"]}) != frozenset({"A", "B"})


def test_generate_pairings_reciprocal_disabled(monkeypatch):
    _patch_participants(monkeypatch, ["A", "B", "C", "D"])
    _patch_forbidden(monkeypatch, [])
    _patch_allow_recip(monkeypatch, False)
    random.seed(1)

    assignment = santa.generate_pairings()

    pairs = {(giver, recipient) for giver, recipient in assignment.items()}
    for giver, recipient in pairs:
        assert (recipient, giver) not in pairs


def test_generate_pairings_fails_when_impossible(monkeypatch):
    _patch_participants(monkeypatch, ["A", "B"])
    _patch_forbidden(monkeypatch, [("A", "B"), ("B", "A")])
    _patch_allow_recip(monkeypatch, True)
    random.seed(0)

    with pytest.raises(RuntimeError):
        santa.generate_pairings()


def test_randomness_produces_variety(monkeypatch):
    _patch_participants(monkeypatch, ["A", "B", "C", "D"])
    _patch_forbidden(monkeypatch, [])
    _patch_allow_recip(monkeypatch, True)

    seen: Dict[str, Dict[str, str]] = {}
    for seed in range(50):
        random.seed(seed)
        assignment = santa.generate_pairings()
        key = tuple(sorted(assignment.items()))
        seen.setdefault(key, assignment)
        if len(seen) >= 2:
            break

    assert len(seen) >= 2, "Assignments should vary across runs"


def test_scalability_large_group(monkeypatch):
    participants = [f"P{i}" for i in range(30)]
    _patch_participants(monkeypatch, participants)
    _patch_forbidden(monkeypatch, [])
    _patch_allow_recip(monkeypatch, True)
    random.seed(7)

    assignment = santa.generate_pairings()

    assert set(assignment.keys()) == set(participants)
    assert len(set(assignment.values())) == len(participants)
    assert all(giver != recipient for giver, recipient in assignment.items())


def test_build_assignment_url_encodes_base64(monkeypatch):
    monkeypatch.setattr(santa, "BASE_URL", "https://example.com/reveal")
    url = santa.build_assignment_url("Bob", "Jim")

    parsed = urlparse(url)
    assert parsed.scheme == "https"
    assert parsed.netloc == "example.com"

    data_param = parse_qs(parsed.query)["data"][0]
    padded = data_param + "=" * (-len(data_param) % 4)
    decoded = json.loads(base64.urlsafe_b64decode(padded).decode("utf-8"))
    assert decoded == {"giver": "Bob", "recipient": "Jim"}


def test_write_csv_outputs_rows(monkeypatch, tmp_path):
    monkeypatch.setattr(santa, "BASE_URL", "https://example.com/reveal")
    assignments = {"Bob": "Jim", "Ann": "Zoe"}
    out_file = tmp_path / "out.csv"

    santa.write_csv(assignments, out_file)

    with out_file.open() as f:
        rows = list(csv.reader(f))

    assert rows[0] == ["giver", "url"]
    body = {r[0]: r[1] for r in rows[1:]}
    assert set(body.keys()) == {"Ann", "Bob"}
    for giver, recipient in assignments.items():
        assert giver in body
        assert "data=" in body[giver]


def test_verify_assignments_passes_and_prints(capsys):
    assignments = {"A": "B", "B": "C", "C": "A"}

    santa.verify_assignments(assignments, ["A", "B", "C"])

    out = capsys.readouterr().out
    assert "Verification passed" in out


def test_verify_assignments_detects_missing():
    assignments = {"A": "B"}

    with pytest.raises(ValueError):
        santa.verify_assignments(assignments, ["A", "B", "C"])
