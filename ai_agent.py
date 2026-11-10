import json
import os
from datetime import date
from pathlib import Path
from typing import Optional, Protocol, TypedDict, cast
from google.genai import types
from dotenv import load_dotenv
from google import genai
import time
import ollama
from google.genai import errors

# Find .env in the same folder as this file
BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"

load_dotenv(ENV_PATH, override=True)

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise ValueError(
        f"GEMINI_API_KEY missing. Check: {ENV_PATH}"
    )

client = genai.Client(
    api_key=api_key,
    http_options=types.HttpOptions(timeout=20000)
)



class _Response(Protocol):
    text: Optional[str]


class _Models(Protocol):
    def generate_content(self, *, model: str, contents: str) -> _Response: ...


class _OllamaMessage(Protocol):
    content: Optional[str]


class _OllamaResponse(Protocol):
    message: Optional[_OllamaMessage]


class ExtractedTask(TypedDict):
    task: str
    owner: str
    deadline: str
    status: str


class ExtractedMeeting(TypedDict):
    meeting_name: str
    summary: str
    key_decisions: list[str]
    recommendations: list[str]
    tasks: list[ExtractedTask]





def generate_with_retry(prompt: str) -> _Response:
    import random

    models = cast(_Models, client.models)
    max_attempts = 3

    for attempt in range(max_attempts):
        start_time = time.perf_counter()

        try:
            print(
                f"Gemini request started "
                f"(attempt {attempt + 1}/{max_attempts})..."
            )

            response = models.generate_content(
                model="gemini-3.8-flash",
                contents=prompt
            )

            elapsed = time.perf_counter() - start_time
            print(
                f"Gemini response received in "
                f"{elapsed:.2f} seconds."
            )

            return response

        except errors.APIError as e:
            elapsed = time.perf_counter() - start_time

            if getattr(e, "code", None) == 503 and attempt < max_attempts - 1:
                wait_time = 2 ** attempt
                total_wait = wait_time + random.uniform(0, 0.5)

                print(
                    f"Gemini 503 after {elapsed:.2f}s. "==
                    f"Retrying in {total_wait:.1f}s..."
                )
                time.sleep(total_wait)
            else:
                raise

    raise RuntimeError("Gemini request failed after retries")


def generate_meeting_output(prompt: str) -> str:
    print("Trying local Gemma AI...")

    try:
        response = ollama.chat(
            model="gemma4:e2b",
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            format="json",
            options={
                "temperature": 0
            }
        )

        ollama_response = cast(_OllamaResponse, response)
        message = ollama_response.message

        if message is None or message.content is None:
            raise ValueError("Local Gemma returned no content")

        result = message.content.strip()

        if not result:
            raise ValueError("Local Gemma returned empty output")

        print("Local Gemma succeeded!")
        return result

    except Exception as local_error:
        print(f"Local Gemma failed: {local_error}")
        print("Switching to Gemini backup...")

    response = generate_with_retry(prompt)

    result = (response.text or "").strip()

    if not result:
        raise ValueError("Gemini returned empty output")

    print("Gemini backup succeeded!")
    return result


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

    response = generate_with_retry(prompt)
    return response.text or ""

def extract_tasks(transcript: str) -> ExtractedMeeting:

    prompt = f"""
    You are an expert AI meeting assistant.

    Analyze this meeting transcript and extract its information.

    Return ONLY valid JSON in exactly this format:

    {{
        "meeting_name": "A short and meaningful meeting title",
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
    - Generate a meaningful meeting name based on the discussion.
    - Keep the meeting name short, ideally 3 to 8 words.
    - Do not invent tasks, names, or deadlines.
    - If the owner is missing, use "Not specified".
    - If the deadline is missing, use "Not specified".
    - If there are no action items, return an empty tasks array.

    Meeting transcript: 
    {transcript}
    """



    response = generate_with_retry(prompt)

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
    meeting_name = data.get("meeting_name")

    if not isinstance(meeting_name, str) or not meeting_name.strip():
        meeting_name = "Untitled Meeting"

    return ExtractedMeeting(
        meeting_name=meeting_name,
        summary=summary,
        key_decisions=[],
        recommendations=[],
        tasks=tasks
    )


def analyze_meeting_once(
    transcript: str,
    meeting_date: str,
) -> ExtractedMeeting:

    prompt = f"""
    You are an expert AI meeting assistant.

    Analyze this meeting transcript.

    Return ONLY valid JSON in exactly this format:

    {{
        "meeting_name": "Short meaningful meeting title",
        "summary": "Short meeting summary",
        "key_decisions": [
            "Important decision 1"
        ],
        "recommendations": [
            "Suggested next step 1"
        ],
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
    - Meeting name should be 3 to 8 words.
    - Never invent names, tasks or deadlines.
    - Use "Not specified" for missing owners or deadlines.
    - Return empty lists if there are no decisions,
      recommendations or action items.
    - Keep the summary concise.

DEADLINE RULES:
    - The meeting date is: {meeting_date}
    - Interpret relative deadlines using this meeting date.
    - Convert "Friday", "next Monday", "tomorrow",
      and similar expressions into actual calendar dates.
    - Return every known deadline strictly as YYYY-MM-DD.
    - For a deadline without enough information,
      return "Not specified".
    - Never guess or invent a deadline date.


    Meeting transcript:
    {transcript}
    """

    raw_text = generate_meeting_output(prompt)

    if raw_text.startswith("```"):
        raw_text = raw_text.split("\n", 1)[-1]
        raw_text = raw_text.rsplit("```", 1)[0].strip()

    parsed: object = json.loads(raw_text)

    if not isinstance(parsed, dict):
        raise ValueError("Gemini returned invalid JSON")

    data = cast(dict[str, object], parsed)

    raw_tasks = data.get("tasks", [])
    if not isinstance(raw_tasks, list):
        raise ValueError("Invalid tasks list")
    raw_tasks = cast(list[object], raw_tasks)

    tasks: list[ExtractedTask] = []

    for item in raw_tasks:
        if not isinstance(item, dict):
            continue

        task_data = cast(dict[str, object], item)

        raw_deadline = str(
            task_data.get("deadline", "Not specified")
        ).strip()

        try:
            if raw_deadline.lower() == "not specified":
                deadline = "Not specified"
            else:
                deadline = date.fromisoformat(raw_deadline).isoformat()
        except ValueError:
            deadline = "Not specified"

        tasks.append({
            "task": str(task_data.get("task", "")),
            "owner": str(task_data.get("owner", "Not specified")),
            "deadline": deadline,
            "status": "Pending",
        })

    def get_string_list(key: str) -> list[str]:
        value = data.get(key, [])
        if not isinstance(value, list):
            return []
        return [str(item) for item in cast(list[object], value) if item]

    meeting_name = data.get("meeting_name")
    summary = data.get("summary")

    return ExtractedMeeting(
        meeting_name=(
            meeting_name.strip()
            if isinstance(meeting_name, str) and meeting_name.strip()
            else "Untitled Meeting"
        ),
        summary=summary if isinstance(summary, str) else "",
        key_decisions=get_string_list("key_decisions"),
        recommendations=get_string_list("recommendations"),
        tasks=tasks,
    )
