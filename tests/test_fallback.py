import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import ai_agent

# Simulate local AI failure
def simulate_local_failure(*_args: object, **_kwargs: object) -> None:
    raise RuntimeError("Simulated local AI failure")

ai_agent.ollama.chat = simulate_local_failure

prompt = """
Return ONLY valid JSON:
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
"""

print("Testing Gemini fallback...")

try:
    result = ai_agent.generate_meeting_output(prompt)
    print("\nFALLBACK SUCCESS!")
    print(result)

except Exception as e:
    print("\nFALLBACK FAILED!")
    print(type(e).__name__, str(e))
