import io
import json
import os
import unittest
from unittest.mock import patch

from intent_router import route_question


class Response(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


class RouterTests(unittest.TestCase):
    def test_rules_route_known_fact_without_configuration(self):
        with patch.dict(os.environ, {}, clear=True):
            route = route_question("What champion am I playing?")
        self.assertEqual((route.kind, route.tools, route.source),
                         ("observe", ("active_champion",), "rules"))

    def test_llm_selects_multiple_allowed_tools(self):
        body = {"choices": [{"message": {"content": json.dumps({
            "kind": "observe",
            "tools": ["active_champion", "game_clock"],
            "clarification": "",
        })}}]}
        captured = []

        def respond(request, timeout):
            captured.append(json.loads(request.data))
            return Response(json.dumps(body).encode())

        with patch.dict(os.environ, {
            "COACH_ROUTER_URL": "https://router.invalid/v1/chat/completions",
            "COACH_ROUTER_MODEL": "router-model",
        }, clear=True), patch("urllib.request.urlopen", side_effect=respond):
            route = route_question("Who am I and how long has this game gone?")
        self.assertEqual(route.kind, "observe")
        self.assertEqual(route.tools, ("active_champion", "game_clock"))
        self.assertEqual(route.source, "llm")
        self.assertEqual(captured[0]["reasoning_effort"], "none")
        self.assertEqual(captured[0]["max_completion_tokens"], 128)
        self.assertTrue(captured[0]["response_format"]["json_schema"]["strict"])

    def test_unknown_tool_is_rejected_and_falls_back(self):
        body = {"choices": [{"message": {"content": json.dumps({
            "kind": "observe", "tools": ["read_everything"], "clarification": ""
        })}}]}
        with patch.dict(os.environ, {
            "COACH_ROUTER_URL": "https://router.invalid/v1/chat/completions",
            "COACH_ROUTER_MODEL": "router-model",
        }, clear=True), patch("urllib.request.urlopen", return_value=Response(json.dumps(body).encode())):
            route = route_question("What champion am I playing?")
        self.assertEqual((route.source, route.tools), ("rules", ("active_champion",)))

    def test_missing_key_file_falls_back_without_breaking_the_bot(self):
        with patch.dict(os.environ, {
            "COACH_ROUTER_URL": "https://router.invalid/v1/chat/completions",
            "COACH_ROUTER_MODEL": "router-model",
            "COACH_ROUTER_API_KEY_FILE": "Z:\\missing\\router-key.txt",
        }, clear=True):
            route = route_question("What champion am I playing?")
        self.assertEqual((route.source, route.tools), ("rules", ("active_champion",)))

    def test_forward_play_call_routes_to_jev(self):
        body = {"choices": [{"message": {"content": json.dumps({
            "kind": "decision", "tools": [], "clarification": ""
        })}}]}
        with patch.dict(os.environ, {
            "COACH_ROUTER_URL": "https://router.invalid/v1/chat/completions",
            "COACH_ROUTER_MODEL": "router-model",
        }, clear=True), patch("urllib.request.urlopen", return_value=Response(json.dumps(body).encode())):
            route = route_question("Should we contest dragon?")
        self.assertEqual((route.kind, route.source), ("decision", "llm"))


if __name__ == "__main__":
    unittest.main()
