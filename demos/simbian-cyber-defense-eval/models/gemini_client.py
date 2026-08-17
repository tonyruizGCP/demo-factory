"""Gemini 3.7 Flash Model Client with extended reasoning and thinking support.

Supports calling Gemini 3.7 Flash via the Google Gen AI SDK (google-genai) or Vertex AI,
handling thinking token budgets, tool calling, delta streaming, and fallback execution.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def load_env_file(env_path: Optional[Path] = None) -> None:
    """Lightweight .env file parser to populate os.environ without requiring external packages."""
    target = env_path or (Path(__file__).resolve().parent.parent / ".env")
    if not target.exists():
        return

    try:
        with open(target, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                k = k.strip()
                v = v.strip().strip("'\"")
                if k and k not in os.environ and v:
                    os.environ[k] = v
    except Exception:
        pass


# Automatically load .env on module import
load_env_file()


class GeminiClient:
    """Client for invoking Gemini 3.7 Flash with thinking/reasoning parameters."""

    def __init__(
        self,
        model_name: str = "gemini-3.7-flash",
        api_key: Optional[str] = None,
        project_id: Optional[str] = None,
        location: Optional[str] = None,
    ):
        load_env_file()
        self.model_name = model_name
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        self.project_id = project_id or os.environ.get("GOOGLE_CLOUD_PROJECT") or os.environ.get("GCP_PROJECT")
        self.location = location or os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
        self._genai_client = None
        self._init_sdk()

    def _init_sdk(self) -> None:
        """Initialize Google Gen AI client if libraries and credentials are available."""
        if not self.api_key and not self.project_id:
            self._genai_client = None
            return

        try:
            from google import genai
            from google.genai import types

            if self.api_key:
                self._genai_client = genai.Client(api_key=self.api_key)
            elif self.project_id:
                self._genai_client = genai.Client(
                    vertexai=True,
                    project=self.project_id,
                    location=self.location,
                )
        except Exception:
            self._genai_client = None

    def is_live_available(self) -> bool:
        """Return True if live Gemini API connection is available."""
        if not self._genai_client:
            self._init_sdk()
        return self._genai_client is not None

    def generate_response(
        self,
        system_prompt: str,
        conversation_history: List[Dict[str, str]],
        model_name: Optional[str] = None,
        thinking_budget: int = 2048,
        temperature: float = 0.2,
    ) -> Tuple[str, int, int]:
        """Generate response from Gemini model with extended reasoning capabilities.

        Args:
            system_prompt (str): System instruction and agent constitution.
            conversation_history (List[Dict[str, str]]): List of message turns with 'role' and 'content'.
            model_name (Optional[str], optional): Target Gemini model. Defaults to self.model_name.
            thinking_budget (int, optional): Thinking token budget for reasoning. Defaults to 2048.
            temperature (float, optional): Generation temperature. Defaults to 0.2.

        Returns:
            Tuple[str, int, int]: (response_text, input_tokens, output_tokens)
        """
        if not self._genai_client:
            self._init_sdk()

        if not self._genai_client:
            raise RuntimeError(
                "Live Gemini client is not initialized. Please configure GOOGLE_CLOUD_PROJECT or GEMINI_API_KEY in your .env file."
            )

        from google.genai import types

        contents = []
        for msg in conversation_history:
            role = "user" if msg["role"] in ("user", "system") else "model"
            contents.append(types.Content(
                role=role,
                parts=[types.Part.from_text(text=msg["content"])]
            ))

        target_model = model_name or self.model_name

        config = types.GenerateContentConfig(
            system_instruction=system_prompt,
            temperature=temperature,
            thinking_config=types.ThinkingConfig(
                thinking_budget=thinking_budget,
            ) if thinking_budget > 0 else None,
            response_mime_type="application/json",
        )

        candidate_models = [target_model]
        if target_model != "gemini-2.5-flash":
            candidate_models.append("gemini-2.5-flash")

        response = None
        last_err = None
        for m in candidate_models:
            try:
                model_config = config
                if "2.5" in m or "1.5" in m:
                    model_config = types.GenerateContentConfig(
                        system_instruction=system_prompt,
                        temperature=temperature,
                        response_mime_type="application/json",
                    )

                response = self._genai_client.models.generate_content(
                    model=m,
                    contents=contents,
                    config=model_config,
                )
                break
            except Exception as e:
                last_err = e
                continue

        if response is None:
            raise last_err or RuntimeError("Failed to generate content with Gemini models.")

        raw_text = response.text or ""
        in_tokens = getattr(response.usage_metadata, "prompt_token_count", len(str(contents)) // 4) or 0
        out_tokens = getattr(response.usage_metadata, "candidates_token_count", len(raw_text) // 4) or 0

        return raw_text, in_tokens, out_tokens

    def generate_hunting_step(
        self,
        system_instruction: str,
        conversation_history: List[Dict[str, str]],
        thinking_budget: int = 2048,
        temperature: float = 0.2,
    ) -> Dict[str, Any]:
        """Generate the next hunting reasoning step and action."""
        raw_text, _, _ = self.generate_response(
            system_prompt=system_instruction,
            conversation_history=conversation_history,
            thinking_budget=thinking_budget,
            temperature=temperature,
        )

        try:
            parsed_json = json.loads(raw_text)
        except Exception:
            parsed_json = {"raw_output": raw_text}

        return {
            "thought": parsed_json.get("thought", ""),
            "action_type": parsed_json.get("action_type", "sql_query"),
            "sql_query": parsed_json.get("sql_query"),
            "findings": parsed_json.get("findings", []),
            "summary": parsed_json.get("summary", ""),
            "raw_response": raw_text,
        }
