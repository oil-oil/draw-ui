#!/usr/bin/env python3
from __future__ import annotations

import base64
import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "generate_image.py"
SPEC = importlib.util.spec_from_file_location("generate_image", SCRIPT_PATH)
assert SPEC and SPEC.loader
generate_image = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(generate_image)


class FakeResponse:
    def __init__(self, payload: dict):
        self._body = json.dumps(payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def read(self) -> bytes:
        return self._body


class GenerateImageTests(unittest.TestCase):
    def test_provider_specific_model_resolution(self):
        self.assertEqual(generate_image.resolve_codex_model("gpt-5.6-sol"), "gpt-5.6-sol")
        self.assertEqual(generate_image.resolve_codex_model(), generate_image.DEFAULT_CODEX_MODEL)

    def test_openai_base_url_is_explicit_and_normalized(self):
        with mock.patch.dict(os.environ, {"OPENAI_IMAGE_BASE_URL": "https://example.com"}, clear=False):
            self.assertEqual(generate_image.resolve_codex_base_url(), "https://example.com/v1")
        with mock.patch.dict(
            os.environ, {"OPENAI_IMAGE_BASE_URL": "https://example.com/custom/v1/"}, clear=False
        ):
            self.assertEqual(generate_image.resolve_codex_base_url(), "https://example.com/custom/v1")

    def test_codex_request_uses_selected_model_and_forces_image_tool(self):
        captured = {}
        png = b"\x89PNG\r\n\x1a\nfixture"
        response_payload = {
            "output": [
                {
                    "type": "image_generation_call",
                    "result": base64.b64encode(png).decode("ascii"),
                }
            ]
        }

        def fake_urlopen(request, timeout):
            captured["request"] = request
            captured["timeout"] = timeout
            return FakeResponse(response_payload)

        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "result.png"
            with (
                mock.patch.dict(os.environ, {"OPENAI_IMAGE_API_KEY": "test-key"}, clear=False),
                mock.patch.object(generate_image.urllib.request, "urlopen", side_effect=fake_urlopen),
            ):
                final_path = generate_image.request_codex_image(
                    prompt="draw a test",
                    refs=[],
                    image_type="wide",
                    model="gpt-5.6-sol",
                    output_path=output,
                )

            request_payload = json.loads(captured["request"].data)
            self.assertEqual(request_payload["model"], "gpt-5.6-sol")
            self.assertEqual(request_payload["tool_choice"], "required")
            self.assertIs(request_payload["store"], False)
            self.assertEqual(request_payload["tools"][0]["size"], "1536x864")
            self.assertEqual(final_path.read_bytes(), png)
            self.assertEqual(captured["request"].headers["Authorization"], "Bearer test-key")


if __name__ == "__main__":
    unittest.main()
