import os
import hashlib
from datetime import datetime, date
from pathlib import Path
from collections.abc import Iterable, Mapping
from typing import Optional, TypedDict, cast

import gspread
from dotenv import load_dotenv
from gspread.utils import ValueInputOption

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

SHEET_ID = os.getenv("GOOGLE_SHEET_ID")
CREDENTIALS_FILE = os.getenv(
    "GOOGLE_CREDENTIALS_FILE", "service_account.json"
)

TASK_HEADERS = [
    "Task",
    "Owner",
    "Deadline",
    "Status",
    "Meeting Summary",
    "Meeting ID",
    "Meeting Transcript",
]

MEETING_HEADERS = [
    "Meeting ID",
    "Meeting Name",
    "Date & Time",
    "Summary",
    "Transcript",
]


class TaskRecord(TypedDict):
    row: int
    task: str
    owner: str
    deadline: str
    status: str


def get_spreadsheet() -> gspread.Spreadsheet:
    if not SHEET_ID:
        raise ValueError("GOOGLE_SHEET_ID is missing from .env")

    credentials_path = BASE_DIR / CREDENTIALS_FILE

    if not credentials_path.exists():
        raise FileNotFoundError(
            f"Google credentials file not found: {credentials_path}"
        )

    gc = gspread.service_account(filename=str(credentials_path))
    return gc.open_by_key(SHEET_ID)


def get_or_create_worksheet(
    spreadsheet: gspread.Spreadsheet,
    title: str,
    headers: list[str],
) -> gspread.Worksheet:
    try:
        worksheet = spreadsheet.worksheet(title)
    except gspread.WorksheetNotFound:
        worksheet = spreadsheet.add_worksheet(
            title=title,
            rows=1000,
            cols=len(headers),
        )

    if worksheet.col_count < len(headers):
        worksheet.resize(cols=len(headers))

    existing_headers = worksheet.row_values(1)

    if not existing_headers:
        worksheet.update(
            range_name=f"A1:{gspread.utils.rowcol_to_a1(1, len(headers))}",
            values=[headers],
        )
    elif title == "Tasks":
        # Preserve existing five columns and add the new headers
        worksheet.update(
            range_name="F1:G1",
            values=[TASK_HEADERS[5:7]],
        )

    return worksheet


def get_worksheet() -> gspread.Worksheet:
    spreadsheet = get_spreadsheet()
    return get_or_create_worksheet(
        spreadsheet, "Tasks", TASK_HEADERS
    )


def save_meeting(
    meeting_name: str,
    tasks: Iterable[object],
    summary: str,
    transcript: str,
) -> Optional[int]:

    spreadsheet = get_spreadsheet()

    tasks_sheet = get_or_create_worksheet(
        spreadsheet, "Tasks", TASK_HEADERS
    )
    meetings_sheet = get_or_create_worksheet(
        spreadsheet, "Meetings", MEETING_HEADERS
    )

    # Generate a stable ID for this transcript
    normalized_transcript = " ".join(transcript.split())
    meeting_id = hashlib.sha256(
        normalized_transcript.encode("utf-8")
    ).hexdigest()

    # Check the Meetings worksheet first
    existing_meeting_ids = meetings_sheet.col_values(1)[1:]

    if meeting_id in existing_meeting_ids:
        return None

    # Prepare task rows
    rows: list[list[str]] = []

    for task in tasks:
        if not isinstance(task, dict):
            continue

        task_data = cast(Mapping[str, object], task)

        rows.append([
            str(task_data.get("task", "")),
            str(task_data.get("owner", "Not specified")),
            str(task_data.get("deadline", "Not specified")),
            str(task_data.get("status", "Pending")),
            summary,
            meeting_id,
            transcript,
        ])

    # Check Tasks too, in case a previous save was interrupted
    existing_task_ids = tasks_sheet.col_values(6)[1:]

    if rows and meeting_id not in existing_task_ids:
        tasks_sheet.append_rows(
            rows,
            value_input_option=ValueInputOption.user_entered,
        )

    # Save the meeting record even when there are no tasks
    meeting_datetime = datetime.now().astimezone().isoformat(
        timespec="seconds"
    )

    meetings_sheet.append_row(
        [
            meeting_id,
            meeting_name,
            meeting_datetime,
            summary,
            transcript,
        ],
        value_input_option=ValueInputOption.user_entered,
    )

    return len(rows)


def meeting_exists(transcript: str) -> bool:
    """Check whether this transcript is already saved."""
    spreadsheet = get_spreadsheet()

    try:
        meetings_sheet = spreadsheet.worksheet("Meetings")
    except gspread.WorksheetNotFound:
        return False

    normalized_transcript = " ".join(transcript.split())
    meeting_id = hashlib.sha256(
        normalized_transcript.encode("utf-8")
    ).hexdigest()

    existing_ids = meetings_sheet.col_values(1)[1:]

    return meeting_id in existing_ids


def get_all_tasks() -> list[TaskRecord]:
    """Return tasks with their actual Google Sheets row numbers."""
    worksheet = get_worksheet()
    records = worksheet.get_all_records()

    # Remove extra spaces from column headers
    records = [
        {
            str(key).strip(): value
            for key, value in record.items()
        }
        for record in records
    ]
    print("SHEET RECORDS:", records)
    print("SHEET HEADERS:", list(records[0].keys()) if records else "No records")

    tasks: list[TaskRecord] = []

    for row_number, record in enumerate(records, start=2):
        tasks.append({
            "row": row_number,
            "task": str(record.get("Task", "")),
            "owner": str(record.get("Owner", "")),
            "deadline": str(record.get("Deadline", "")),
            "status": str(record.get("Status", "Pending")),
        })

    return tasks


def update_task_status(row_number: int, status: str):
    """Update the status of a task in Google Sheets."""

    allowed_statuses = ["Pending", "In Progress", "Completed"]

    if status not in allowed_statuses:
        raise ValueError("Invalid task status")

    if row_number < 2:
        raise ValueError("Invalid task row number")

    worksheet = get_worksheet()

    if row_number > worksheet.row_count:
        raise ValueError("Task not found")

    task_name = worksheet.cell(row_number, 1).value

    if not task_name:
        raise ValueError("Task not found")

    worksheet.update_cell(row_number, 4, status)

    return task_name


def parse_deadline(deadline: str) -> Optional[date]:
    """Convert a deadline string into a date."""
    deadline = deadline.strip()

    if not deadline or deadline.lower() in {
        "not specified", "none", "n/a"
    }:
        return None

    try:
        return date.fromisoformat(deadline)
    except ValueError:
        return None


def get_deadline_tasks() -> dict[str, list[TaskRecord]]:
    """Return upcoming, overdue and undated pending tasks."""
    tasks = get_all_tasks()
    today = date.today()

    upcoming: list[TaskRecord] = []
    overdue: list[TaskRecord] = []
    undated: list[TaskRecord] = []

    for task in tasks:
        if task["status"].strip().lower() == "completed":
            continue

        deadline_date = parse_deadline(task["deadline"])

        if deadline_date is None:
            undated.append(task)
        elif deadline_date < today:
            overdue.append(task)
        else:
            upcoming.append(task)

    upcoming.sort(
        key=lambda task: parse_deadline(task["deadline"]) or date.max
    )

    overdue.sort(
        key=lambda task: parse_deadline(task["deadline"]) or date.max
    )

    return {
        "upcoming": upcoming,
        "overdue": overdue,
        "undated": undated,
    }
