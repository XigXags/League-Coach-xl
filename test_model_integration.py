"""Offline regression tests for model switching, provider boundaries and scoreboard freshness."""
import asyncio
import copy
import json
from pathlib import Path
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, Mock, patch

import bot as runtime
from coach import Option, Reply, jev_rank
from llm_providers import generate
from model_pipeline import enhance
from model_profiles import Profiles, ROOT
from scoreboard_reader import ScoreboardWatcher, match_identity
from coordinators import CoordinatorBoard


class ProfileTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.config = json.loads((ROOT / "jev_implementation/profiles.example.json").read_text())
        self.save()

    def tearDown(self):
        self.temp.cleanup()

    def save(self):
        (self.root / "coach_models.json").write_text(json.dumps(self.config))

    def test_persistence_and_independent_servers(self):
        self.config["profiles"]["alternate"] = copy.deepcopy(self.config["profiles"]["legacy"])
        self.save()
        registry = Profiles(self.root)
        registry.select(1, "alternate")
        self.assertEqual(Profiles(self.root).selected(1), "alternate")
        self.assertEqual(registry.selected(2), "legacy")
        self.assertEqual(registry.revision[1], 1)

    def test_bad_selection_does_not_change_or_write(self):
        registry = Profiles(self.root)
        for name in ("missing", "claude-test"):
            with self.assertRaises(ValueError):
                registry.select(1, name)
        self.assertEqual(registry.selected(1), "legacy")
        self.assertFalse((self.root / "model_selections.json").exists())

    def test_invalid_reload_keeps_old_configuration(self):
        registry = Profiles(self.root)
        self.config["profiles"]["legacy"]["fallback_profile"] = "legacy"
        self.save()
        with self.assertRaises(ValueError):
            registry.reload()
        self.assertIsNone(registry.data["profiles"]["legacy"]["fallback_profile"])

    def test_nonlocal_http_and_embedded_credentials_rejected(self):
        for endpoint in ("http://example.com/v1", "https://user:password@example.com/v1"):
            self.config["profiles"]["local-test"]["base_url"] = endpoint
            self.save()
            with self.assertRaises(ValueError):
                Profiles(self.root)

    def test_missing_credentials_and_model_are_reported_without_values(self):
        self.config["profiles"]["openai-test"]["enabled"] = True
        self.save()
        with patch.dict("os.environ", {}, clear=True):
            registry = Profiles(self.root)
            self.assertEqual(registry.readiness("openai-test"), "model ID missing")
            with patch.dict("os.environ", {"COACH_OPENAI_MODEL": "test-model"}):
                self.assertEqual(registry.readiness("openai-test"), "API key missing")


class ProviderTests(unittest.IsolatedAsyncioTestCase):
    def profile(self, provider):
        return {"provider": provider, "model": "requested", "api_key_env": None,
                "base_url": "http://127.0.0.1:11434/v1", "max_output_tokens": 160, "timeout_seconds": 2}

    async def test_responses_collects_text_after_reasoning_and_sets_no_storage(self):
        response = {"model": "resolved", "status": "completed", "usage": {"input_tokens": 3},
                    "output": [{"type": "reasoning"}, {"type": "message", "content": [
                        {"type": "output_text", "text": "Reset."}, {"type": "output_text", "text": "Or push."}]}]}
        with patch("llm_providers.post_json", new_callable=AsyncMock, return_value=response) as post:
            result = await generate(self.profile("openai_responses"), "rules", {"observed": 1})
        self.assertEqual(result.text, "Reset. Or push.")
        self.assertEqual(result.model, "resolved")
        self.assertFalse(post.call_args.args[2]["store"])

    async def test_native_anthropic_protocol_and_blocks(self):
        response = {"model": "resolved", "stop_reason": "end_turn", "content": [
            {"type": "thinking", "thinking": "private"}, {"type": "text", "text": "Push. Or reset."}]}
        with patch("llm_providers.post_json", new_callable=AsyncMock, return_value=response) as post:
            result = await generate(self.profile("anthropic_messages"), "rules", {})
        self.assertEqual(result.text, "Push. Or reset.")
        self.assertEqual(post.call_args.args[1]["anthropic-version"], "2023-06-01")
        self.assertEqual(post.call_args.args[2]["system"], "rules")

    async def test_truncated_refused_empty_and_missing_model_fail(self):
        responses = [
            {"model": "x", "status": "incomplete", "output": []},
            {"model": "x", "status": "completed", "output": [{"type": "message", "content": [{"type": "refusal"}]}]},
            {"model": "x", "status": "completed", "output": []},
            {"status": "completed", "output": [{"type": "message", "content": [{"type": "output_text", "text": "hello"}]}]},
        ]
        for response in responses:
            with patch("llm_providers.post_json", new_callable=AsyncMock, return_value=response):
                with self.assertRaises(ValueError):
                    await generate(self.profile("openai_responses"), "rules", {})

    async def test_compatible_chat_shape(self):
        response = {"model": "local", "choices": [{"finish_reason": "stop", "message": {"content": "Reset."}}]}
        with patch("llm_providers.post_json", new_callable=AsyncMock, return_value=response):
            self.assertEqual((await generate(self.profile("chat_completions"), "rules", {})).text, "Reset.")

    async def test_unconfigured_calibration_never_spends_generator_tokens(self):
        answer = Reply("Game read: reset or push.")
        answer.spoken = "Reset. Or push."
        answer.generation_context = {"game": {}}
        answer.commit = Mock()
        profile = self.profile("openai_responses") | {"id": "test"}
        with patch("model_pipeline.generate", new_callable=AsyncMock) as generate_mock:
            result = await enhance(answer, "What now?", profile, {"policy_id": None}, 2)
        generate_mock.assert_not_awaited()
        self.assertEqual(result.spoken, answer.spoken)
        self.assertIs(result.commit, answer.commit)
        answer.commit.assert_not_called()
        self.assertIn("calibration", str(result))

    async def test_switch_cancels_pending_generation_and_keeps_memory(self):
        guild = SimpleNamespace(id=888811, voice_client=None)
        task = asyncio.create_task(asyncio.sleep(30))
        await asyncio.sleep(0)
        runtime.bot.generations[guild.id] = task
        topic = object()
        runtime.bot.topics[guild.id] = topic
        runtime.begin_request(guild)
        await asyncio.sleep(0)
        self.assertTrue(task.cancelled())
        self.assertIs(runtime.bot.topics.pop(guild.id), topic)

    async def test_failed_discord_send_does_not_commit(self):
        guild = SimpleNamespace(id=888812, voice_client=None)
        interaction = SimpleNamespace(guild=guild, guild_id=guild.id,
            response=SimpleNamespace(defer=AsyncMock()), followup=SimpleNamespace(send=AsyncMock(side_effect=RuntimeError("send failed"))))
        answer = Reply("Game read: reset.")
        answer.commit = Mock()
        with patch.object(runtime, "make_answer", new_callable=AsyncMock, return_value=answer):
            with self.assertRaises(RuntimeError):
                await runtime.respond_to_question(interaction, "what now?")
        answer.commit.assert_not_called()

    async def test_new_request_during_discord_send_does_not_commit_or_speak(self):
        guild = SimpleNamespace(id=888813, voice_client=None)
        async def send(message):
            runtime.begin_request(guild)
        interaction = SimpleNamespace(guild=guild, guild_id=guild.id,
            response=SimpleNamespace(defer=AsyncMock()), followup=SimpleNamespace(send=AsyncMock(side_effect=send)))
        answer = Reply("Game read: reset.")
        answer.commit = Mock()
        with patch.object(runtime, "make_answer", new_callable=AsyncMock, return_value=answer), \
             patch.object(runtime, "speak_with_refresh", new_callable=AsyncMock) as speak:
            await runtime.respond_to_question(interaction, "what now?")
        answer.commit.assert_not_called()
        speak.assert_not_awaited()

    def test_accept_is_exactly_once(self):
        answer = Reply("plain")
        answer.commit = Mock(return_value="")
        runtime.accept(888814, answer)
        runtime.accept(888814, answer)
        answer.commit.assert_called_once()


class ScoreboardTests(unittest.TestCase):
    def setUp(self):
        self.state = {"players": [{"name": "a", "champion": "Ashe", "team": "ORDER"}], "game_time_seconds": 100}
        self.watcher = ScoreboardWatcher(lambda: self.state)
        self.watcher.latest = {"match": match_identity(self.state), "monotonic": time.monotonic(),
            "game_second": 95, "captured_at": time.time(), "source": "visible scoreboard", "ocr_text": "Ashe 30 CS",
            "lines": ["Ashe 30 CS"], "status": "OCR read", "path": "private.png"}

    def test_fresh_ocr_is_labelled_unverified_and_local_path_removed(self):
        result = self.watcher.snapshot(self.state)
        self.assertEqual(result["ocr_text"], "Ashe 30 CS")
        self.assertIn("Unverified", result["reliability"])
        self.assertNotIn("path", result)

    def test_expired_changed_match_restarted_or_unreadable_never_enters_brief(self):
        original = copy.deepcopy(self.watcher.latest)
        for changes in ({"monotonic": time.monotonic() - 50}, {"match": ()}, {"game_second": 101}, {"ocr_text": ""}):
            self.watcher.latest = original | changes
            self.assertIsNone(self.watcher.snapshot(self.state))


class ComparisonIsolationTests(unittest.TestCase):
    def test_fork_keeps_context_but_never_mutates_live_plan(self):
        board = CoordinatorBoard()
        board.plan = {"id": "six_crab", "marks": [4, 5]}
        board.offer = (("a", "six_crab"),)
        detached = board.fork()
        self.assertEqual(detached.plan, board.plan)
        self.assertIsNot(detached.lock, board.lock)
        detached.plan["marks"].append(6)
        detached.offer = ()
        self.assertEqual(board.plan["marks"], [4, 5])
        self.assertEqual(board.offer, (("a", "six_crab"),))


if __name__ == "__main__":
    unittest.main()
