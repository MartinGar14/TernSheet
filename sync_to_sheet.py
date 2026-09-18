"""Step 6: full pipeline — fetch new application emails, extract fields via
Claude, and upsert rows in the Google Sheet, keyed on Gmail thread ID.

A new thread -> new row. A follow-up on a tracked thread -> updates that
row in place instead of duplicating it. Non-application emails (no company
and no status extracted) are skipped and not written to the sheet.
"""

import json
import os
from datetime import date

from anthropic import Anthropic
from dotenv import load_dotenv
from googleapiclient.discovery import build

from extract_email import (
    SCOPES as GMAIL_SCOPES,
    TOKEN_PATH as GMAIL_TOKEN_PATH,
    build_gmail_query,
    extract_fields,
    get_body_text,
    load_processed_ids,
    save_processed_ids,
)
from google_auth import get_credentials

load_dotenv()

SHEETS_SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
SHEETS_TOKEN_PATH = "token_sheets.json"
SHEET_ID = os.environ["SHEET_ID"]
SHEET_NAME = os.environ.get("SHEET_NAME") or "Sheet1"

HEADERS = [
    "Company", "Position", "Date Applied", "Link", "Sender Email",
    "Status", "Last Updated", "Notes", "Thread ID",
]


def ensure_header(sheets):
    result = sheets.values().get(spreadsheetId=SHEET_ID, range=f"{SHEET_NAME}!A1:I1").execute()
    if not result.get("values"):
        sheets.values().update(
            spreadsheetId=SHEET_ID, range=f"{SHEET_NAME}!A1",
            valueInputOption="USER_ENTERED", body={"values": [HEADERS]},
        ).execute()


def load_thread_map(sheets):
    """thread_id -> {row: sheet row number, data: existing row values}."""
    result = sheets.values().get(spreadsheetId=SHEET_ID, range=f"{SHEET_NAME}!A2:I").execute()
    thread_map = {}
    for i, row in enumerate(result.get("values", [])):
        row = row + [""] * (len(HEADERS) - len(row))
        thread_id = row[8]
        if thread_id:
            thread_map[thread_id] = {"row": i + 2, "data": row}
    return thread_map


def merge_row(old, fields, sender, thread_id, today):
    """Combine a freshly-extracted email's fields with the sheet's existing
    row for that thread — a null field never overwrites a known value."""
    return [
        fields.get("company") or old[0],
        fields.get("position") or old[1],
        fields.get("date_applied") or old[2],
        fields.get("link") or old[3],
        sender or old[4],
        fields.get("status") or old[5],
        today,
        fields.get("notes") or old[7],
        thread_id,
    ]


def upsert_row(sheets, thread_map, fields, sender):
    thread_id = fields["thread_id"]
    company, status = fields.get("company"), fields.get("status")
    today = date.today().isoformat()

    if thread_id in thread_map:
        entry = thread_map[thread_id]
        old = entry["data"]
        merged = merge_row(old, fields, sender, thread_id, today)
        sheets.values().update(
            spreadsheetId=SHEET_ID, range=f"{SHEET_NAME}!A{entry['row']}:I{entry['row']}",
            valueInputOption="USER_ENTERED", body={"values": [merged]},
        ).execute()
        if status and status != old[5]:
            print(f"STATUS CHANGE [{company or old[0]}]: {old[5] or '(none)'} -> {status}")
        else:
            print(f"Updated (no status change) [{company or old[0]}]")
    else:
        new_row = [
            company or "", fields.get("position") or "", fields.get("date_applied") or "",
            fields.get("link") or "", sender or "", status or "", today,
            fields.get("notes") or "", thread_id,
        ]
        sheets.values().append(
            spreadsheetId=SHEET_ID, range=f"{SHEET_NAME}!A1",
            valueInputOption="USER_ENTERED", body={"values": [new_row]},
        ).execute()
        print(f"NEW [{company or '(unknown)'}] status={status}")


def main():
    gmail_creds = get_credentials(GMAIL_SCOPES, GMAIL_TOKEN_PATH)
    gmail = build("gmail", "v1", credentials=gmail_creds)
    sheets_creds = get_credentials(SHEETS_SCOPES, SHEETS_TOKEN_PATH)
    sheets = build("sheets", "v4", credentials=sheets_creds).spreadsheets()
    claude = Anthropic()

    ensure_header(sheets)
    processed_ids = load_processed_ids()

    results = gmail.users().messages().list(userId="me", q=build_gmail_query(), maxResults=100).execute()
    messages = [m for m in results.get("messages", []) if m["id"] not in processed_ids]

    if not messages:
        print("No new matching emails.")
        return

    thread_map = load_thread_map(sheets)

    for msg in messages:
        full_msg = gmail.users().messages().get(userId="me", id=msg["id"], format="full").execute()
        headers = full_msg["payload"].get("headers", [])
        subject = next((h["value"] for h in headers if h["name"] == "Subject"), "")
        sender = next((h["value"] for h in headers if h["name"] == "From"), "")
        body = get_body_text(full_msg["payload"]) or full_msg.get("snippet", "")

        fields = extract_fields(claude, subject, sender, body)
        fields["thread_id"] = full_msg["threadId"]

        if fields.get("company") or fields.get("status"):
            upsert_row(sheets, thread_map, fields, sender)
        else:
            print(f"Skipped (not an application): {subject!r}")

        processed_ids.add(msg["id"])
        save_processed_ids(processed_ids)


if __name__ == "__main__":
    main()
