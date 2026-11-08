import json
import os
from pathlib import Path
from typing import Protocol, TypedDict, cast

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


class ExtractedTask(TypedDict):
    task: str
    owner: str
    deadline: str
    status: str


class ExtractedMeeting(TypedDict):
    summary: str
    tasks: list[ExtractedTask]



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

def extract_tasks(transcript: str) -> ExtractedMeeting:
    prompt = f"""
    Extract action items from this meeting transcript.

    Return ONLY valid JSON in exactly this format:
    {{
        "summary": "A short meeting summary",
        "tasks": [
            {{
                "task": "Task description",
                "owner": "Person responsible or Not specified",
                "deadline": "Deadline or Not specified",
                "status": "Pending"
            }}
        ]
    }}

    Rules:
    - Do not invent tasks, names, or deadlines.
    - If the owner is missing, use "Not specified".
    - If the deadline is missing, use "Not specified".
    - If there are no action items, return an empty tasks array.

    Meeting transcript:
    {transcript}
    """

    models = cast(_Models, client.models)
    response = models.generate_content(
        model="gemini-3.8-flash",
        contents=prompt
    )

    raw_text = (response.text or "").strip()

    # Remove JSON code fences if Gemini includes them
    if raw_text.startswith("```"):
        raw_text = raw_text.split("\n", 1)[-1]
        raw_text = raw_text.rsplit("```", 1)[0].strip()

    parsed: object = json.loads(raw_text)

    if not isinstance(parsed, dict):
        raise ValueError("Gemini returned an invalid task response")

    data = cast(dict[str, object], parsed)
    raw_tasks = data.get("tasks")
    if not isinstance(raw_tasks, list):
        raise ValueError("Gemini response does not contain a valid tasks list")

    tasks: list[ExtractedTask] = []
    for raw_task in cast(list[object], raw_tasks):
        if not isinstance(raw_task, dict):
            continue

        task_data = cast(dict[str, object], raw_task)
        tasks.append(
            ExtractedTask(
                task=str(task_data.get("task", "")) or "",
                owner=str(task_data.get("owner", "Not specified")) or "Not specified",
                deadline=str(task_data.get("deadline", "Not specified")) or "Not specified",
                status=str(task_data.get("status", "Pending")) or "Pending",
            )
        )

    summary = data.get("summary")
    if not isinstance(summary, str):
        summary = ""

    return ExtractedMeeting(summary=summary, tasks=tasks)
