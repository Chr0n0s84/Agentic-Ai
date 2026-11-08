import os
from pathlib import Path
from collections.abc import Iterable, Mapping
from typing import cast

import gspread
from dotenv import load_dotenv
from gspread.utils import ValueInputOption

# Load environment variables from this project's .env file
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

SHEET_ID = os.getenv("GOOGLE_SHEET_ID")
CREDENTIALS_FILE = os.getenv("GOOGLE_CREDENTIALS_FILE", "service_account.json")


def get_worksheet() -> gspread.Worksheet:
    if not SHEET_ID:
        raise ValueError("GOOGLE_SHEET_ID is missing from .env")

    credentials_path = BASE_DIR / CREDENTIALS_FILE

    if not credentials_path.exists():
        raise FileNotFoundError(
            f"Google credentials file not found: {credentials_path}"
        )

    gc = gspread.service_account(filename=str(credentials_path))
    spreadsheet = gc.open_by_key(SHEET_ID)

    try:
        worksheet = spreadsheet.worksheet("Tasks")
    except gspread.WorksheetNotFound:
        worksheet = spreadsheet.add_worksheet(
            title="Tasks", rows=1000, cols=5
        )

    # Add headers if the worksheet is empty
    if not worksheet.get_all_values():
        worksheet.append_row(
            ["Task", "Owner", "Deadline", "Status", "Meeting Summary"]
        )

    return worksheet


def save_tasks(
    tasks: Iterable[object],
    summary: str,
) -> int:
    worksheet = get_worksheet()

    rows: list[list[str]] = []

    for task in tasks:
        if not isinstance(task, dict):
            continue

        task_data = cast(Mapping[str, object], task)
        rows.append([
            str(task_data.get("task", "")),
            str(task_data.get("owner", "")),
            str(task_data.get("deadline", "")),
            str(task_data.get("status", "Pending")),
            summary
        ])

    if rows:
        worksheet.append_rows(
            rows,
            value_input_option=ValueInputOption.user_entered,
        )

    return len(rows)
