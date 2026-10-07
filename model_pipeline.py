"""Selected LLM wording, followed by validated Jev judgments and calibrated gates."""
from __future__ import annotations
import asyncio
import json
import hashlib
import time
from dataclasses import asdict
from pathlib import Path
from coach import Reply, JEV_URL
from credentials import load_jev_key
from llm_providers import generate, post_json
from jev_implementation.foundation.contracts import validate_response
from jev_implementation.foundation.questions import HAZARDS, QUESTION_REVISION, output_guard_request
from jev_implementation.foundation.policy import Gate, Policy, guard_line

ROOT = Path(__file__).parent
SYSTEM = (ROOT / "jev_implementation/prompts/coach_system.txt").read_text(encoding="utf-8")


def brief_for(answer, question):
    context = getattr(answer, "generation_context", {})
    topic = getattr(answer, "topic", None)
    return {"player_question": question[:500], "evidence": context,
            "prepared_options": [asdict(option) for option in topic.pair] if topic else [],
            "prepared_chat": str(answer), "prepared_spoken": getattr(answer, "spoken", ""),
            "requires_alternatives": not bool(getattr(answer, "layer", 0)),
            "followup_on_dated_read": bool(getattr(answer, "layer", 0))}


def load_policy(config, profile=None):
    identifier = config.get("policy_id")
    if not identifier:
        return None
    if not isinstance(identifier, str) or not identifier.replace("-", "").replace("_", "").isalnum():
        raise ValueError("Invalid calibration ID")
    data = json.loads((ROOT / "evals/policies" / f"{identifier}.json").read_text(encoding="utf-8"))
    eligibility = data.pop("eligible_generators", [])
    expected = {"provider": profile["provider"], "model": profile["model"],
                "prompt_sha256": hashlib.sha256(SYSTEM.encode("utf-8")).hexdigest()} if profile else None
    if expected is None or expected not in eligibility:
        return None
    for name in ("intent_probability", "intent_confidence"):
        data[name] = Gate(**data[name])
    data["hazards"] = {name: Gate(**band) for name, band in data["hazards"].items()}
    policy = Policy(**data)
    if policy.calibration_id != identifier:
        raise ValueError("Calibration ID mismatch")
    return policy


async def judge(text, brief, config, timeout):
    key = await asyncio.to_thread(load_jev_key)
    if not key:
        raise ValueError("Jev key missing")
    context = brief["evidence"]
    state = {"player_question": brief["player_question"], "candidate_line": text,
             "observed": context.get("game", {}),
             "computed": {"prepared_options": brief["prepared_options"]},
             "reported": context.get("scoreboard_capture", {}),
             "references": {k: v for k, v in context.items() if k not in {"game", "scoreboard_capture"}},
             "requires_alternatives": brief.get("requires_alternatives", True),
             "asks_for_options": brief.get("requires_alternatives", True),
             "prepared_hint": brief["prepared_spoken"]}
    request = output_guard_request(state, config["model"])
    response = await post_json(JEV_URL, {"Authorization": f"Bearer {key}"}, request, timeout)
    return validate_response(request, response)


async def draft(profile, brief, config, timeout):
    result = await generate(profile, SYSTEM, brief)
    if len(result.text.split()) > 60 or "```" in result.text:
        raise ValueError("Spoken answer must be plain text under 60 words")
    checked = await judge(result.text, brief, config, timeout)
    return result, checked


async def enhance(answer, question, profile, config, deadline):
    if profile["provider"] == "builtin" or not getattr(answer, "generation_context", None):
        return answer
    status = ""
    try:
        async with asyncio.timeout(deadline):
            policy = load_policy(config, profile)
            if policy is None:
                # No fabricated production thresholds. /compare can still evaluate draft outputs.
                status = "Live wording awaits Jev calibration; use /compare to test this profile."
            else:
                brief = brief_for(answer, question)
                for rewrite in range(2):
                    result, checked = await draft(profile, brief, config, min(5, deadline))
                    if result.model != profile["model"]:
                        status = "Resolved generator model differs from its evaluated profile."
                        break
                    hazards = {name: checked["answers"][name]["noul"] for name in HAZARDS}
                    decision = guard_line(hazards, checked["answers"]["severity"], policy,
                                          model=checked["model"], revision=QUESTION_REVISION,
                                          required_hazards=set(HAZARDS), rewrites=rewrite)
                    if decision.route == "speak":
                        suffix = f"\n\n**Coach ({profile['id']}):** {result.text}"
                        output = Reply(str(answer)[:1990-len(suffix)] + suffix)
                        output.__dict__.update(answer.__dict__)
                        output.spoken = result.text
                        output.model_metadata = {"profile": profile["id"], "model": result.model,
                                                 "usage": result.usage, "seconds": result.seconds,
                                                 "request_id": result.request_id, "retries": result.retries,
                                                 "jev_model": checked["model"], "guard": "speak"}
                        return output
                    if decision.route != "rewrite":
                        status = f"Jev rejected generated wording ({decision.reason})."
                        break
                    brief["rewrite_feedback"] = hazards
    except (OSError, ValueError, RuntimeError, KeyError, TypeError, TimeoutError) as exc:
        status = f"Model unavailable ({type(exc).__name__})."
    except Exception as exc:
        status = f"Model request failed ({type(exc).__name__})."
    suffix = f"\n\nModel {profile['id']}: {status} Using Jev's prepared answer."
    output = Reply(str(answer)[:1990-len(suffix)] + suffix)
    output.__dict__.update(answer.__dict__)
    output.model_metadata = {"profile": profile["id"], "guard": "fallback", "reason": status}
    return output


async def enhance_chain(answer, question, profiles, config, deadline):
    started = time.monotonic()
    attempted = []
    last = answer
    for profile in profiles:
        if profile["provider"] == "builtin":
            break
        remaining = deadline - (time.monotonic() - started)
        if remaining <= 0:
            break
        last = await enhance(answer, question, profile, config, remaining)
        attempted.append(profile["id"])
        if getattr(last, "model_metadata", {}).get("guard") == "speak":
            if len(attempted) > 1:
                suffix = f"\nFallback: {' → '.join(attempted)}."
                output = Reply(str(last)[:1990-len(suffix)] + suffix)
                output.__dict__.update(last.__dict__)
                return output
            return last
        # A missing global calibration cannot be solved by trying another provider.
        if not config.get("policy_id"):
            break
    return last
