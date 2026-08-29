import json
import re
from typing import Any

from openai import AsyncOpenAI

from app.config import settings


class GonkaClient:
    """
    Client for communicating with Gonka Router's
    OpenAI-compatible API.
    """

    def __init__(self) -> None:
        self.client = AsyncOpenAI(
            api_key=settings.gonka_api_key,
            base_url=settings.gonka_api_url,
        )

    async def analyze_claim(
        self,
        model: str,
        system_prompt: str,
        user_prompt: str,
    ) -> dict[str, Any]:

        response = await self.client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": system_prompt,
                },
                {
                    "role": "user",
                    "content": user_prompt,
                },
            ],
            temperature=0.0,
        )

        content = response.choices[0].message.content

        if not content:
            raise ValueError(
                f"Gonka returned an empty response for model: {model}"
            )

        return self._parse_json(content)

    @staticmethod
    def _parse_json(content: str) -> dict[str, Any]:
        """
        Extract a JSON object from an LLM response.

        Handles:
        - Plain JSON
        - Markdown JSON code blocks
        - <think>...</think> reasoning blocks
        - Additional prose before/after JSON
        """

        content = content.strip()

        # ---------------------------------------------------------
        # 1. Remove <think>...</think> blocks.
        # ---------------------------------------------------------

        content = re.sub(
            r"<think>.*?</think>",
            "",
            content,
            flags=re.DOTALL | re.IGNORECASE,
        ).strip()

        # ---------------------------------------------------------
        # 2. Remove markdown code fences.
        # ---------------------------------------------------------

        if content.startswith("```"):

            lines = content.splitlines()

            # Remove opening fence.
            lines = lines[1:]

            # Remove closing fence.
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]

            content = "\n".join(lines).strip()

        # ---------------------------------------------------------
        # 3. Try parsing the entire response first.
        # ---------------------------------------------------------

        try:
            parsed = json.loads(content)

            if not isinstance(parsed, dict):
                raise ValueError(
                    "Gonka response must be a JSON object."
                )

            return parsed

        except json.JSONDecodeError:
            pass

        # ---------------------------------------------------------
        # 4. If there is additional text, locate the JSON object.
        # ---------------------------------------------------------

        start = content.find("{")
        end = content.rfind("}")

        if start == -1 or end == -1 or end <= start:
            raise ValueError(
                f"Gonka returned invalid JSON: {content}"
            )

        json_content = content[start:end + 1]

        try:
            parsed = json.loads(json_content)

        except json.JSONDecodeError as exc:
            raise ValueError(
                f"Gonka returned invalid JSON: {content}"
            ) from exc

        if not isinstance(parsed, dict):
            raise ValueError(
                "Gonka response must be a JSON object."
            )

        return parsed