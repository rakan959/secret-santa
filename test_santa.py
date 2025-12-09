"""Tests for santa.py."""

import random
from typing import Dict

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


def test_write_qr_codes_generates_expected_files(monkeypatch, tmp_path):
    captured = {}

    class FakeImage:
        def __init__(self, payload):
            self.payload = payload

        def save(self, path):
            captured[path.name] = self.payload

    def fake_make(payload):
        return FakeImage(payload)

    monkeypatch.setattr(
        santa, "qrcode", type("Q", (), {"make": staticmethod(fake_make)})
    )

    assignments = {"Bob": "Jim", "Ann-Marie": "Zoe"}

    santa.write_qr_codes(assignments, tmp_path)

    assert captured["Bob.png"] == santa._qr_payload("Bob", "Jim")
    assert captured["Ann-Marie.png"] == santa._qr_payload("Ann-Marie", "Zoe")
