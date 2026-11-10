import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import time
from typing import Any
import ollama

def _extract_message_content(response: Any) -> str:
    message = getattr(response, "message", None)
    if message is None:
        return ""

    content = getattr(message, "content", None)
    return "" if content is None else str(content)

print("Testing local Gemma AI...")

start = time.perf_counter()

try:
    response = ollama.chat(  # pyright: ignore[reportUnknownMemberType]
        model="gemma4:e2b",
        messages=[
            {
                "role": "user",
                "content": """
                Extract meeting tasks:

                John will write a report by Friday.
                Sarah will design a poster by Monday.
                Mike will review the report by Tuesday.

                Return exactly three tasks with owner and deadline.
                """
            }
        ],
    )

    print("\nSUCCESS!")
    print("Response time:", round(time.perf_counter() - start, 2), "seconds")
    print(_extract_message_content(response))

except Exception as e:
    print("\nFAILED!")
    print(type(e).__name__, str(e))


from ai_agent import generate_meeting_output

prompt = """
Return ONLY valid JSON in this format:
{
  "meeting_name": "Project Planning",
  "summary": "The team discussed project tasks.",
  "key_decisions": [],
  "recommendations": [],
  "tasks": [
    {
      "task": "Complete project report",
      "owner": "John",
      "deadline": "2026-11-15",
      "status": "Pending"
    }
  ]
}

Meeting transcript:
John will complete the project report by November 15.
"""

print("Testing hybrid AI...")
result = generate_meeting_output(prompt)

print("\nFINAL RESULT:")
print(result)
