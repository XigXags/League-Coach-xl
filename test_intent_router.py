import io
import json
import os
import unittest
import urllib.error
from unittest.mock import patch

from intent_router import IntentRouterError, route_question


class Response(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


class RouterTests(unittest.TestCase):
    def test_missing_configuration_is_not_silently_bypassed(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(IntentRouterError):
                route_question("What champion am I playing?")

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
            "COACH_ROUTER_API_KEY": "test-key",
        }, clear=True), patch("urllib.request.urlopen", side_effect=respond):
            route = route_question("Who am I and how long has this game gone?")
        self.assertEqual(route.kind, "observe")
        self.assertEqual(route.tools, ("active_champion", "game_clock"))
        self.assertEqual(route.source, "llm")
        self.assertEqual(captured[0]["reasoning_effort"], "none")
        self.assertEqual(captured[0]["max_completion_tokens"], 128)
        self.assertTrue(captured[0]["response_format"]["json_schema"]["strict"])
        tools_schema = captured[0]["response_format"]["json_schema"]["schema"]["properties"]["tools"]
        self.assertNotIn("uniqueItems", tools_schema)

    def test_http_error_exposes_safe_api_diagnostics(self):
        error_body = io.BytesIO(json.dumps({"error": {
            "message": "Unsupported schema keyword: example",
            "type": "invalid_request_error",
            "param": "response_format",
            "code": "invalid_json_schema",
        }}).encode())
        error = urllib.error.HTTPError(
            "https://router.invalid/v1/chat/completions", 400, "Bad Request", {}, error_body)
        with patch.dict(os.environ, {
            "COACH_ROUTER_URL": "https://router.invalid/v1/chat/completions",
            "COACH_ROUTER_MODEL": "router-model",
            "COACH_ROUTER_API_KEY": "test-key",
        }, clear=True), patch("urllib.request.urlopen", side_effect=error), \
             patch("builtins.print") as logged:
            with self.assertRaises(IntentRouterError):
                route_question("Can you see the minimap?")
        message = " ".join(str(call.args[0]) for call in logged.call_args_list)
        self.assertIn("api_code=invalid_json_schema", message)
        self.assertIn("api_param=response_format", message)
        self.assertNotIn("test-key", message)

    def test_unknown_tool_is_rejected_without_rules_fallback(self):
        body = {"choices": [{"message": {"content": json.dumps({
            "kind": "observe", "tools": ["read_everything"], "clarification": ""
        })}}]}
        with patch.dict(os.environ, {
            "COACH_ROUTER_URL": "https://router.invalid/v1/chat/completions",
            "COACH_ROUTER_MODEL": "router-model",
            "COACH_ROUTER_API_KEY": "test-key",
        }, clear=True), patch("urllib.request.urlopen", return_value=Response(json.dumps(body).encode())):
            with self.assertRaises(IntentRouterError):
                route_question("What champion am I playing?")

    def test_missing_key_file_blocks_routing(self):
        with patch.dict(os.environ, {
            "COACH_ROUTER_URL": "https://router.invalid/v1/chat/completions",
            "COACH_ROUTER_MODEL": "router-model",
            "COACH_ROUTER_API_KEY_FILE": "Z:\\missing\\router-key.txt",
        }, clear=True):
            with self.assertRaises(IntentRouterError):
                route_question("What champion am I playing?")

    def test_api_failure_does_not_guess_minimap_intent_or_reach_jev(self):
        with patch.dict(os.environ, {
            "COACH_ROUTER_URL": "https://router.invalid/v1/chat/completions",
            "COACH_ROUTER_MODEL": "router-model",
            "COACH_ROUTER_API_KEY": "test-key",
        }, clear=True), patch("urllib.request.urlopen", side_effect=OSError("offline")):
            with self.assertRaises(IntentRouterError):
                route_question("Can you see the minimap?")

    def test_forward_play_call_routes_to_jev(self):
        body = {"choices": [{"message": {"content": json.dumps({
            "kind": "decision", "tools": [], "clarification": ""
        })}}]}
        with patch.dict(os.environ, {
            "COACH_ROUTER_URL": "https://router.invalid/v1/chat/completions",
            "COACH_ROUTER_MODEL": "router-model",
            "COACH_ROUTER_API_KEY": "test-key",
        }, clear=True), patch("urllib.request.urlopen", return_value=Response(json.dumps(body).encode())):
            route = route_question("Should we contest dragon?")
        self.assertEqual((route.kind, route.source), ("decision", "llm"))


if __name__ == "__main__":
    unittest.main()
