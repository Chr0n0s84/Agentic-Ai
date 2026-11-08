
import os
from pathlib import Path
from typing import Protocol, cast

from dotenv import load_dotenv
from google import genai

# Find .env in the same folder as this file
BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"

load_dotenv(ENV_PATH, override=True)

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise ValueError(
        f"GEMINI_API_KEY missing. Check: {ENV_PATH}"
    )

client = genai.Client(api_key=api_key)


class _Response(Protocol):
    text: str | None


class _Models(Protocol):
    def generate_content(self, *, model: str, contents: str) -> _Response: ...



def analyze_meeting(transcript: str) -> str:

    prompt = f"""
    You are an expert AI Meeting Assistant.

    Analyze this meeting transcript:

    {transcript}

    Return your response in these sections:

    1. MEETING SUMMARY
    Give a short summary.

    2. KEY DECISIONS
    List all important decisions.

    3. ACTION ITEMS
    For every task identify:
    - Task description
    - Responsible person
    - Deadline

    4. MISSING INFORMATION
    Highlight tasks with missing owners
    or missing deadlines.

    5. RECOMMENDATIONS
    Suggest next steps for the team.

    Never invent names or deadlines.
    If information is missing, write
    "Not specified".
    """

    models = cast(_Models, client.models)
    response = models.generate_content(
        model="gemini-3.8-flash",
        contents=prompt
    )

    return response.text or ""