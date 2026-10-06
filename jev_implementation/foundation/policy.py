"""Pure routing prototypes. No model calls, file writes, or bot actions.

Call validate_response first. Thresholds are supplied by a versioned evaluation
artifact; there are intentionally no production numeric defaults in this module.
"""

from __future__ import annotations

from dataclasses import dataclass
import math


@dataclass(frozen=True)
class Decision:
    route: str
    reason: str


@dataclass(frozen=True)
class Gate:
    review: float
    act: float

    def __post_init__(self):
        if not (math.isfinite(self.review) and math.isfinite(self.act) and 0 <= self.review <= self.act <= 1):
            raise ValueError("Gate needs 0 <= review <= act <= 1")


@dataclass(frozen=True)
class Policy:
    calibration_id: str
    model: str
    question_revision: str
    intent_probability: Gate
    intent_confidence: Gate
    fit_min: float
    hazards: dict[str, Gate]
    severity_confidence_min: float
    severity_block: float  # normalized expectation, not a physical quantity

    def __post_init__(self):
        if not all(isinstance(s, str) and s.strip() for s in (self.calibration_id, self.model, self.question_revision)):
            raise ValueError("Policy needs calibration, model, and question revision IDs")
        if not all(math.isfinite(x) and 0 <= x <= 1 for x in (self.fit_min, self.severity_confidence_min, self.severity_block)):
            raise ValueError("Policy floors must be finite and in [0,1]")


def policy_matches(policy: Policy | None, model: str, revision: str) -> bool:
    return bool(policy and policy.model == model and policy.question_revision == revision)


def route_intent(answer: dict, policy: Policy | None, *, model: str, revision: str,
                 mutation: bool, required_arguments_ready: bool) -> Decision:
    if not policy_matches(policy, model, revision):
        return Decision("clarify", "missing or mismatched calibration")
    probability = answer["probabilities"][answer["choice"]]
    confidence = answer["confidence"]
    if probability < policy.intent_probability.review or confidence < policy.intent_confidence.review:
        return Decision("clarify", "intent not understood")
    if answer["choice"] in {"other", "none"}:
        return Decision("generate", "no supported closed-set route")
    if mutation and not required_arguments_ready:
        return Decision("clarify", "required action arguments unresolved")
    high = probability >= policy.intent_probability.act and confidence >= policy.intent_confidence.act
    if not high:
        return Decision("confirm" if mutation else "generate", "intent is in review band")
    return Decision("propose_effect" if mutation else "dispatch", "intent cleared calibrated gates")


def guard_line(hazards: dict[str, float], severity: dict, policy: Policy | None, *,
               model: str, revision: str, required_hazards: set[str], rewrites: int = 0) -> Decision:
    if not policy_matches(policy, model, revision):
        return Decision("fallback", "missing or mismatched calibration")
    if set(hazards) != required_hazards or set(policy.hazards) != required_hazards:
        return Decision("fallback", "missing hazard or policy")
    if not all(isinstance(value, (int, float)) and math.isfinite(value) and 0 <= value <= 1
               for value in hazards.values()):
        return Decision("fallback", "malformed hazard result")
    if severity["confidence"] < policy.severity_confidence_min:
        return Decision("fallback", "severity uncertain")
    if any(p >= policy.hazards[name].act for name, p in hazards.items()):
        return Decision("fallback", "hazard blocked")
    if any(p >= policy.hazards[name].review for name, p in hazards.items()):
        levels = len(severity["probabilities"]) - 1
        if levels <= 0 or not math.isfinite(severity["score"]):
            return Decision("fallback", "malformed severity result")
        if severity["score"] / levels >= policy.severity_block:
            return Decision("fallback", "review escalated by severity")
        return Decision("rewrite" if rewrites == 0 else "fallback", "review band; at most one rewrite")
    return Decision("speak", "all required hazards below review bands")


def selected_answer_fit(selected: str, fit: dict[str, float], *, none_id: str,
                        policy: Policy | None, model: str, revision: str) -> Decision:
    if not policy_matches(policy, model, revision):
        return Decision("generate", "missing or mismatched calibration")
    if selected == none_id or selected not in fit or fit[selected] < policy.fit_min:
        return Decision("generate", "selected answer itself did not fit")
    # Still needs output guards, evidence checks, and a current delivery identity.
    return Decision("check_output", "selected answer fit cleared")
