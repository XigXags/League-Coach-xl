"""Validate the HTTP JSON contract before any value influences Coach.

Uses wire-format string Score keys. This is not an SDK adapter or HTTP client.
Additional response fields are retained; unknown request fields are rejected.
"""

from __future__ import annotations

import hashlib
import json
import math
from typing import Any

PINNED_MODEL = "jev-1.13.0"  # Documentation baseline, not a calibrated Coach model.
PROBABILITY_TOLERANCE = 1e-5


class ContractError(ValueError):
    """Missing, malformed, or inconsistent model output; use a safe fallback."""


def _require(ok: bool, message: str) -> None:
    if not ok:
        raise ContractError(message)


def _number(value: Any, label: str, low: float, high: float) -> float:
    _require(type(value) in (int, float), f"{label}: expected a number")
    _require(math.isfinite(value) and low <= value <= high, f"{label}: out of range")
    return float(value)


def _text(value: Any, label: str) -> None:
    _require(isinstance(value, str) and bool(value.strip()), f"{label}: empty text")


def _structured(value: Any, label: str) -> None:
    _require(isinstance(value, (str, dict, list)), f"{label}: expected text/object/array")


def canonical(value: Any) -> str:
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise ContractError("Expected finite JSON data") from exc


def validate_request(request: dict) -> None:
    _require(isinstance(request, dict), "request: expected object")
    _require(set(request) == {"state", "model", "questions"}, "request: unexpected/missing fields")
    _structured(request["state"], "state")
    _text(request["model"], "model")
    questions = request["questions"]
    _require(isinstance(questions, dict) and bool(questions), "questions: expected nonempty map")
    for qid, question in questions.items():
        _text(qid, "question id")
        _require(isinstance(question, dict), f"{qid}: expected object")
        _require({"type", "instructions"} <= set(question) <= {"type", "instructions", "criteria"},
                 f"{qid}: unexpected/missing fields; put guidance inside instructions")
        _structured(question["instructions"], f"{qid}.instructions")
        kind, criteria = question["type"], question.get("criteria")
        _require(kind in ("choice", "score", "noul"), f"{qid}: unknown question type")
        if kind == "choice":
            # Coach deliberately resolves singleton candidate sets in code.
            _require(isinstance(criteria, dict) and 2 <= len(criteria) <= 255,
                     f"{qid}: Coach Choice requires 2..255 options, including none if appropriate")
            for key, value in criteria.items():
                _text(key, f"{qid} option")
                if value is not None:
                    _structured(value, f"{qid}.{key}")
        elif kind == "score":
            _require(isinstance(criteria, list) and 2 <= len(criteria) <= 10,
                     f"{qid}: Score requires 2..10 levels")
            for level in criteria:
                _structured(level, f"{qid} level")
        elif "criteria" in question:
            _require(isinstance(criteria, dict) and set(criteria) <= {"true", "false"},
                     f"{qid}: Noul criteria keys must be true/false strings")
            for boundary in criteria.values():
                _structured(boundary, f"{qid} boundary")
    canonical(request)


def request_fingerprint(request: dict) -> str:
    """Includes model, state, wording, candidate IDs and option ORDER.

    Order is material for Jev; canonical JSON alone would erase a Choice permutation.
    """
    validate_request(request)
    order = {qid: list(q["criteria"]) for qid, q in request["questions"].items() if q["type"] == "choice"}
    payload = {"request": request, "choice_order": order}
    return hashlib.sha256(canonical(payload).encode("utf-8")).hexdigest()


def validate_response(request: dict, response: dict) -> dict:
    """Return a detached, validated envelope. Never replace missing probabilities with zero.

    Token counts are optional in the API reference; missing counts remain missing.
    Validation deliberately does not infer factual correctness or recompute confidence.
    """
    validate_request(request)
    _require(isinstance(response, dict), "response: expected object")
    _text(response.get("model"), "response.model")
    usage = response.get("usage")
    _require(isinstance(usage, dict), "response.usage: expected object")
    for key in ("input_tokens", "output_tokens"):
        if key in usage:
            _require(type(usage[key]) is int and usage[key] >= 0, f"usage.{key}: expected nonnegative integer")
    answers = response.get("answers")
    _require(isinstance(answers, dict) and set(answers) == set(request["questions"]),
             "answers: expected exactly the requested question IDs")
    for qid, question in request["questions"].items():
        answer = answers[qid]
        _require(isinstance(answer, dict) and answer.get("type") == question["type"], f"{qid}: wrong answer type")
        if question["type"] == "noul":
            _number(answer.get("noul"), f"{qid}.noul", 0, 1)
            continue
        _number(answer.get("confidence"), f"{qid}.confidence", 0, 1)
        expected = set(question["criteria"]) if question["type"] == "choice" else {str(i) for i in range(len(question["criteria"]))}
        probabilities = answer.get("probabilities")
        _require(isinstance(probabilities, dict) and set(probabilities) == expected, f"{qid}: wrong probability keys")
        for key, value in probabilities.items():
            _number(value, f"{qid}.{key}", 0, 1)
        _require(abs(math.fsum(probabilities.values()) - 1) <= PROBABILITY_TOLERANCE, f"{qid}: probabilities must sum to one")
        if question["type"] == "choice":
            choice = answer.get("choice")
            _require(isinstance(choice, str) and choice in expected, f"{qid}: unknown choice")
            _require(probabilities[choice] + PROBABILITY_TOLERANCE >= max(probabilities.values()), f"{qid}: choice is not a maximum")
        else:
            score = _number(answer.get("score"), f"{qid}.score", 0, len(expected) - 1)
            mean = math.fsum(int(key) * value for key, value in probabilities.items())
            _require(abs(score - mean) <= PROBABILITY_TOLERANCE, f"{qid}: score disagrees with distribution")
            legend = answer.get("legend")
            _require(isinstance(legend, dict) and set(legend) == expected, f"{qid}: wrong legend keys")
    return json.loads(canonical(response))
