"""Synthetic regression cases. These tests do not calibrate Jev's accuracy."""

import copy
import unittest
from dataclasses import replace

from foundation.contracts import ContractError, PINNED_MODEL, request_fingerprint, validate_request, validate_response
from foundation.evidence import Fact, Turn, fresh_report, may_deliver
from foundation.policy import Gate, Policy, guard_line, route_intent, selected_answer_fit
from foundation.questions import HAZARDS, QUESTION_REVISION, output_guard_request


def request():
    return {"state": {"player_question": "Should I lock the plan?"}, "model": PINNED_MODEL,
            "questions": {"intent": {"type": "choice", "instructions": "What did the player request?",
                                     "criteria": {"ask": "Ask for advice", "other": "Something else"}}}}


def response():
    return {"model": PINNED_MODEL, "usage": {"input_tokens": 100, "output_tokens": 10},
            "answers": {"intent": {"type": "choice", "choice": "ask", "confidence": .8,
                                    "probabilities": {"ask": .9, "other": .1}}}}


def synthetic_policy():
    # Test fixtures ONLY. No evidence backs these example thresholds for Coach.
    return Policy("SYNTHETIC-UNIT-TEST-ONLY", PINNED_MODEL, QUESTION_REVISION,
                  Gate(.5, .85), Gate(.5, .8), .8,
                  {name: Gate(.3, .7) for name in HAZARDS}, .6, .7)


class ContractTests(unittest.TestCase):
    def test_preserves_model_usage_and_probabilities(self):
        result = validate_response(request(), response())
        self.assertEqual(result, response())

    def test_response_is_detached(self):
        original = response()
        result = validate_response(request(), original)
        original["answers"].clear()
        self.assertIn("intent", result["answers"])

    def test_rejects_missing_and_extra_question_ids(self):
        for answers in ({}, {"invented": response()["answers"]["intent"]}):
            with self.subTest(answers=answers), self.assertRaises(ContractError):
                validate_response(request(), {**response(), "answers": answers})

    def test_rejects_missing_probability_keys_and_zero_mass(self):
        for probs in ({}, {"ask": 1}, {"ask": 0, "other": 0}, {"ask": 1, "other": 0, "extra": 0}):
            res = response()
            res["answers"]["intent"]["probabilities"] = probs
            with self.subTest(probs=probs), self.assertRaises(ContractError):
                validate_response(request(), res)

    def test_rejects_nonfinite_negative_boolean_and_string_probabilities(self):
        for value in (float("nan"), float("inf"), -1, True, "0.9"):
            res = response()
            res["answers"]["intent"]["probabilities"]["ask"] = value
            with self.subTest(value=value), self.assertRaises(ContractError):
                validate_response(request(), res)

    def test_rejects_wrong_winner_or_type(self):
        for key, value in (("choice", "other"), ("choice", "unknown"), ("type", "score"), ("confidence", 1.1)):
            res = response()
            res["answers"]["intent"][key] = value
            with self.subTest(key=key, value=value), self.assertRaises(ContractError):
                validate_response(request(), res)

    def test_tied_winner_is_allowed(self):
        res = response()
        res["answers"]["intent"]["probabilities"] = {"ask": .5, "other": .5}
        validate_response(request(), res)

    def test_score_mean_keys_and_legend(self):
        req = request()
        req["questions"] = {"risk": {"type": "score", "instructions": "How risky?", "criteria": ["Low", "High"]}}
        res = {"model": PINNED_MODEL, "usage": {}, "answers": {"risk": {"type": "score", "score": .25,
            "confidence": .7, "probabilities": {"0": .75, "1": .25}, "legend": {"0": "Low", "1": "High"}}}}
        validate_response(req, res)
        for key, value in (("score", .8), ("legend", {}), ("probabilities", {0: .75, 1: .25})):
            bad = copy.deepcopy(res)
            bad["answers"]["risk"][key] = value
            with self.subTest(key=key), self.assertRaises(ContractError):
                validate_response(req, bad)

    def test_noul_needs_no_confidence(self):
        req = request()
        req["questions"] = {"stated": {"type": "noul", "instructions": "Was it stated?"}}
        res = {"model": PINNED_MODEL, "usage": {}, "answers": {"stated": {"type": "noul", "noul": .5}}}
        validate_response(req, res)

    def test_request_bounds(self):
        for count in (0, 1, 256):
            req = request()
            req["questions"]["intent"]["criteria"] = {str(i): None for i in range(count)}
            with self.subTest(count=count), self.assertRaises(ContractError):
                validate_request(req)
        for count in (1, 11):
            req["questions"] = {"risk": {"type": "score", "instructions": "How risky?", "criteria": ["level"] * count}}
            with self.subTest(score_count=count), self.assertRaises(ContractError):
                validate_request(req)

    def test_undocumented_role_rule_sibling_is_rejected(self):
        req = request()
        req["questions"]["intent"]["role_rule"] = "Important hidden instruction"
        with self.assertRaises(ContractError):
            validate_request(req)

    def test_cache_identity_tracks_wording_state_model_and_option_order(self):
        original = request_fingerprint(request())
        variants = [request() for _ in range(4)]
        variants[0]["state"]["player_question"] = "Lock it"
        variants[1]["model"] = "different-model"
        variants[2]["questions"]["intent"]["instructions"] = "Different wording"
        variants[3]["questions"]["intent"]["criteria"] = {"other": "Something else", "ask": "Ask for advice"}
        for variant in variants:
            self.assertNotEqual(original, request_fingerprint(variant))
        self.assertEqual(original, request_fingerprint(copy.deepcopy(request())))

    def test_usage_does_not_invent_missing_counts(self):
        res = response()
        res["usage"] = {}
        self.assertEqual(validate_response(request(), res)["usage"], {})
        for invalid in (-1, True, "100"):
            res["usage"] = {"input_tokens": invalid}
            with self.assertRaises(ContractError):
                validate_response(request(), res)


class PolicyTests(unittest.TestCase):
    def setUp(self):
        self.policy = synthetic_policy()
        self.context = {"model": PINNED_MODEL, "revision": QUESTION_REVISION}
        self.hazards = {name: .05 for name in HAZARDS}
        self.severity = {"score": .5, "confidence": .9, "probabilities": {"0": .5, "1": .5, "2": 0, "3": 0}}

    def guard(self, **kwargs):
        return guard_line(self.hazards, self.severity, self.policy, required_hazards=set(HAZARDS), **self.context, **kwargs)

    def test_uncalibrated_never_speaks(self):
        self.policy = None
        self.assertEqual(self.guard().route, "fallback")

    def test_model_and_wording_mismatch_never_speak(self):
        for context in ({"model": "new-version", "revision": QUESTION_REVISION}, {"model": PINNED_MODEL, "revision": "new-wording"}):
            self.context = context
            self.assertEqual(self.guard().route, "fallback")

    def test_missing_check_is_not_a_pass(self):
        del self.hazards["unseen_location"]
        self.assertEqual(self.guard().route, "fallback")

    def test_review_rewrites_once(self):
        self.hazards["unseen_location"] = .3
        self.assertEqual(self.guard().route, "rewrite")
        self.assertEqual(self.guard(rewrites=1).route, "fallback")

    def test_severity_escalates_review(self):
        self.hazards["unseen_location"] = .4
        self.severity.update(score=3, probabilities={"0": 0, "1": 0, "2": 0, "3": 1})
        self.assertEqual(self.guard().route, "fallback")

    def test_hazard_action_boundary_blocks(self):
        self.hazards["unseen_location"] = .7
        self.assertEqual(self.guard().route, "fallback")

    def test_uncertain_severity_falls_back(self):
        self.severity["confidence"] = .3
        self.assertEqual(self.guard().route, "fallback")

    def test_nonfinite_or_out_of_range_hazard_falls_back(self):
        for value in (float("nan"), float("inf"), -0.1, 1.1):
            self.hazards["unseen_location"] = value
            self.assertEqual(self.guard().route, "fallback")

    def test_malformed_severity_cannot_bypass_a_review(self):
        self.hazards["unseen_location"] = .4
        self.severity.update(score=float("nan"), probabilities={"0": 1})
        self.assertEqual(self.guard().route, "fallback")

    def test_clear_battery_allows_candidate(self):
        self.assertEqual(self.guard().route, "speak")

    def test_other_candidate_fit_cannot_admit_bad_selected_answer(self):
        result = selected_answer_fit("wrong", {"wrong": .2, "right": .99}, none_id="none", policy=self.policy, **self.context)
        self.assertEqual(result.route, "generate")

    def test_none_is_never_a_prepared_answer(self):
        result = selected_answer_fit("none", {"none": 1}, none_id="none", policy=self.policy, **self.context)
        self.assertEqual(result.route, "generate")

    def test_high_fit_still_needs_output_check(self):
        result = selected_answer_fit("right", {"right": .9}, none_id="none", policy=self.policy, **self.context)
        self.assertEqual(result.route, "check_output")

    def test_action_needs_arguments_and_middle_band_confirms(self):
        answer = response()["answers"]["intent"]
        def decide(ready):
            return route_intent(answer, self.policy, mutation=True, required_arguments_ready=ready, **self.context).route
        self.assertEqual(decide(False), "clarify")
        self.assertEqual(decide(True), "propose_effect")
        answer["confidence"] = .6
        self.assertEqual(decide(True), "confirm")
        answer["confidence"] = .2
        self.assertEqual(decide(True), "clarify")

    def test_confident_other_goes_to_generation(self):
        answer = {"choice": "other", "confidence": 1, "probabilities": {"other": 1, "ask": 0}}
        result = route_intent(answer, self.policy, mutation=False, required_arguments_ready=True, **self.context)
        self.assertEqual(result.route, "generate")


class EvidenceTests(unittest.TestCase):
    def test_delivery_requires_same_session_match_serial_and_version(self):
        current = Turn("guild-and-player", "match", 2, 4)
        self.assertTrue(may_deliver(current, current, delivered=True, already_committed=False))
        variants = [replace(current, session_id="other"), replace(current, match_id="new"),
                    replace(current, match_serial=3), replace(current, request_version=5)]
        for variant in variants:
            self.assertFalse(may_deliver(current, variant, delivered=True, already_committed=False))
        self.assertFalse(may_deliver(current, current, delivered=False, already_committed=False))
        self.assertFalse(may_deliver(current, current, delivered=True, already_committed=True))

    def test_reports_expire_and_never_become_observed_facts(self):
        fact = Fact("jungler bot", "player_report", "match", 100, 115, "utterance-1")
        self.assertTrue(fresh_report(fact, match_id="match", game_second=110))
        for when in (99, 115, 116):
            self.assertFalse(fresh_report(fact, match_id="match", game_second=when))
        self.assertFalse(fresh_report(fact, match_id="other", game_second=110))
        self.assertFalse(fresh_report(replace(fact, source="reference"), match_id="match", game_second=110))

    def test_guard_state_requires_evidence_and_explicit_alternatives_scope(self):
        with self.assertRaises(ValueError):
            output_guard_request({"candidate_line": "go now"})
        state = {"player_question": "where now?", "candidate_line": "Check the wave or reset.",
                 "observed": {}, "computed": {}, "reported": [], "references": [],
                 "requires_alternatives": True, "asks_for_options": True, "prepared_hint": None}
        req = output_guard_request(state)
        self.assertEqual(set(req["questions"]), set(HAZARDS) | {"severity"})
        self.assertTrue(all("instructions" in q for q in req["questions"].values()))


if __name__ == "__main__":
    unittest.main()
