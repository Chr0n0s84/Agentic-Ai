
import os
import time
from pathlib import Path
from typing import Protocol, cast

from dotenv import load_dotenv
from google import genai
from google.genai import types


class _GeminiModels(Protocol):
    def generate_content(
        self,
        *,
        model: str,
        contents: str,
        config: types.GenerateContentConfig | None = None,
    ) -> types.GenerateContentResponse: ...

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env", override=True)

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise ValueError("GEMINI_API_KEY not found in .env")

client = genai.Client(
    api_key=api_key,
    http_options=types.HttpOptions(timeout=60000)
)

prompt = """
Extract the action items from this meeting:

John will complete the project report by November 15.
Sarah will prepare the presentation by November 17.
Mike will review the final report by November 18.

Return a short JSON response with task, owner and deadline.
"""

print("Testing Gemini API...")
start = time.perf_counter()

try:
    models = cast(_GeminiModels, client.models)
    response = models.generate_content(
        model="gemini-3.5-flash-lite",
        contents=prompt,
        config=types.GenerateContentConfig(
            thinking_config=types.ThinkingConfig(
                thinking_level=types.ThinkingLevel.LOW
            )
        )
    )

    print("\nSUCCESS!")
    print(f"Response time: {time.perf_counter() - start:.2f} seconds")
    print(response.text)

except Exception as e:
    print("\nFAILED!")
    print(f"Response time: {time.perf_counter() - start:.2f} seconds")
    print(type(e).__name__, str(e))

finally:
    client.close()
