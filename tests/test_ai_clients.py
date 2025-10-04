import sys
import types
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch


def _ensure_stub(module_name, setup):
    if module_name in sys.modules:
        return
    module = types.ModuleType(module_name)
    setup(module)
    sys.modules[module_name] = module


def _setup_openai(module):
    class ResponsesStub:
        def __init__(self):
            self.create = lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("create not stubbed"))

    class OpenAIStub:
        def __init__(self, api_key=None):
            self.api_key = api_key
            self.responses = ResponsesStub()

    module.OpenAI = OpenAIStub


def _setup_anthropic(module):
    class MessagesStub:
        def __init__(self):
            self.create = lambda *args, **kwargs: None

    class AnthropicStub:
        def __init__(self, api_key=None):
            self.api_key = api_key
            self.messages = MessagesStub()

    module.Anthropic = AnthropicStub


_ensure_stub("openai", _setup_openai)
_ensure_stub("anthropic", _setup_anthropic)

import ai_clients


class AIClientsTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)

        self.original_cache_file = ai_clients.Config.CACHE_FILE
        ai_clients.Config.CACHE_FILE = str(Path(self.temp_dir.name) / "cache.json")
        self.addCleanup(setattr, ai_clients.Config, "CACHE_FILE", self.original_cache_file)

        self.orig_openai_key = ai_clients.Config.OPENAI_API_KEY
        self.orig_claude_key = ai_clients.Config.CLAUDE_API_KEY
        self.orig_deepseek_key = ai_clients.Config.DEEPSEEK_API_KEY
        ai_clients.Config.OPENAI_API_KEY = "test-openai"
        ai_clients.Config.CLAUDE_API_KEY = "test-claude"
        ai_clients.Config.DEEPSEEK_API_KEY = "test-deepseek"
        self.addCleanup(setattr, ai_clients.Config, "OPENAI_API_KEY", self.orig_openai_key)
        self.addCleanup(setattr, ai_clients.Config, "CLAUDE_API_KEY", self.orig_claude_key)
        self.addCleanup(setattr, ai_clients.Config, "DEEPSEEK_API_KEY", self.orig_deepseek_key)

        self.can_use_patch = patch.object(ai_clients.token_monitor, "can_use_tokens", return_value=(True, "OK"))
        self.mock_can_use = self.can_use_patch.start()
        self.addCleanup(self.can_use_patch.stop)

        self.add_tokens_patch = patch.object(ai_clients.token_monitor, "add_tokens")
        self.mock_add_tokens = self.add_tokens_patch.start()
        self.addCleanup(self.add_tokens_patch.stop)

    def test_choose_model_routes_pro(self):
        manager = ai_clients.AIClientManager()
        provider, model = manager.choose_model("Matematica", is_free_tier=False)
        self.assertEqual((provider, model), ("claude", "claude-4.5-sonnet"))

        provider, model = manager.choose_model("Istorie", is_free_tier=False)
        self.assertEqual((provider, model), ("openai", "gpt-5"))

    def test_choose_model_free_non_stem_weighted(self):
        manager = ai_clients.AIClientManager()
        with patch.object(ai_clients.random, "choices", return_value=["gpt-4.1-nano"]) as mock_choices:
            provider, model = manager.choose_model("Istorie", is_free_tier=True)
        self.assertEqual((provider, model), ("openai", "gpt-4.1-nano"))
        mock_choices.assert_called_once_with(["gpt-5-nano", "gpt-4.1-nano"], weights=[0.75, 0.25], k=1)

    def test_get_ai_response_caches_pro_results(self):
        manager = ai_clients.AIClientManager()
        with patch.object(manager, "call_openai", return_value={"content": "primul", "tokens_used": 42}) as mock_call:
            result1 = manager.get_ai_response("Salut", subject="Istorie", is_free_tier=False)
            result2 = manager.get_ai_response("Salut", subject="Istorie", is_free_tier=False)

        self.assertEqual(result1["content"], "primul")
        self.assertFalse(result1["from_cache"])
        self.assertTrue(result2["from_cache"])
        mock_call.assert_called_once()
        self.mock_add_tokens.assert_not_called()

    def test_get_ai_response_free_stem_uses_handler_map(self):
        manager = ai_clients.AIClientManager()
        with patch.object(manager, "call_deepseek", return_value={"content": "deep", "tokens_used": 100}) as mock_deep:
            result = manager.get_ai_response("Salut", subject="Matematica", is_free_tier=True)

        self.assertEqual(result["provider"], "deepseek")
        self.assertEqual(result["content"], "deep")
        self.assertFalse(result["from_cache"])
        mock_deep.assert_called_once()
        self.mock_add_tokens.assert_called_once_with("default", 100)

    def test_call_openai_extracts_output_text_and_usage(self):
        manager = ai_clients.AIClientManager()

        class FakeResponse:
            def __init__(self, text, tokens):
                self.output_text = text
                self.usage = SimpleNamespace(total_tokens=tokens)

        messages = [{"role": "user", "content": "Salut"}]
        fake_response = FakeResponse("raspuns", 21)
        create_mock = MagicMock(return_value=fake_response)
        manager.openai_client.responses.create = create_mock

        result = manager.call_openai(messages, model="gpt-5", max_tokens=50, temperature=0.15)

        self.assertEqual(result["content"], "raspuns")
        self.assertEqual(result["tokens_used"], 21)

        create_mock.assert_called_once()
        kwargs = create_mock.call_args.kwargs
        self.assertEqual(kwargs["model"], "gpt-5")
        self.assertEqual(kwargs["max_output_tokens"], 50)
        self.assertEqual(kwargs["temperature"], 0.15)
        self.assertEqual(kwargs["input"], [
            {"role": "user", "content": [{"type": "text", "text": "Salut"}]}
        ])

    def test_get_free_tier_response_delegates_to_get_ai_response(self):
        manager = ai_clients.AIClientManager()
        with patch.object(manager, "get_ai_response", return_value={"content": "ok"}) as mock_get:
            result = manager.get_free_tier_response(
                prompt="Salut",
                subject="Istorie",
                user_id="u1",
                max_tokens=222,
                temperature=0.33
            )

        self.assertEqual(result, {"content": "ok"})
        mock_get.assert_called_once_with(
            prompt="Salut",
            subject="Istorie",
            user_id="u1",
            is_free_tier=True,
            max_tokens=222,
            temperature=0.33
        )

    def test_unknown_provider_raises(self):
        manager = ai_clients.AIClientManager()
        with patch.object(manager, "choose_model", return_value=("unknown", "model")):
            with self.assertRaises(ValueError):
                manager.get_ai_response("Salut", subject="Istorie", is_free_tier=False)


if __name__ == "__main__":
    unittest.main()
