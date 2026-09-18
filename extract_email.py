"""Step 5: read real application emails from Gmail, extract structured
fields via Claude. Prints results only — no Sheets writes yet, so this
layer stays testable in isolation before step 6 wires in update-vs-new-row.
"""

import base64
import json
import os

from anthropic import Anthropic
from dotenv import load_dotenv
from googleapiclient.discovery import build

from google_auth import get_credentials

load_dotenv()

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
TOKEN_PATH = "token.json"

# First-pass filter: known ATS domains, per Claude.md. Narrows what gets
# sent to the LLM instead of scanning every email in the inbox.
ATS_DOMAINS = [
    "greenhouse.io",
    "lever.co",
    "myworkday.com",
    "icims.com",
    "smartrecruiters.com",
    "ashbyhq.com",
    "jobvite.com",
]
ATS_QUERY = "(" + " OR ".join(f"from:{d}" for d in ATS_DOMAINS) + ")"

STATE_PATH = "state.json"


def build_gmail_query():
    start_date = os.environ.get("START_DATE")
    if not start_date:
        raise SystemExit("Set START_DATE=YYYY-MM-DD in .env (first date to scan from).")
    return f"{ATS_QUERY} after:{start_date.replace('-', '/')}"


def load_processed_ids():
    if not os.path.exists(STATE_PATH):
        return set()
    with open(STATE_PATH) as f:
        return set(json.load(f)["processed_ids"])


def save_processed_ids(ids):
    with open(STATE_PATH, "w") as f:
        json.dump({"processed_ids": sorted(ids)}, f, indent=2)

EXTRACTION_PROMPT = """You are extracting structured data from an internship \
application email. Reply with ONLY a JSON object, no other text, with these \
fields:
- company (string)
- position (string, or null if unclear)
- date_applied (string, YYYY-MM-DD, or null)
- link (string URL to the portal/job posting, or null if none in the email)
- status (one of: "Applied", "Interview", "Rejected", "Offer", "Replied")
- notes (string, one sentence summarizing the email)

Email:
Subject: {subject}
From: {sender}
Body:
{body}
"""


def get_body_text(payload):
    """Walk a Gmail message payload for the first text/plain part."""
    if payload.get("mimeType") == "text/plain" and payload.get("body", {}).get("data"):
        return base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8", errors="replace")

    for part in payload.get("parts", []):
        text = get_body_text(part)
        if text:
            return text

    return ""


def extract_fields(client, subject, sender, body):
    prompt = EXTRACTION_PROMPT.format(subject=subject, sender=sender, body=body[:4000])
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )
    text_block = next((b for b in response.content if b.type == "text"), None)
    if text_block is None:
        return {"error": "no text in LLM response", "stop_reason": response.stop_reason}

    raw = text_block.text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"error": "could not parse LLM response", "raw": raw}


def main():
    creds = get_credentials(SCOPES, TOKEN_PATH)
    gmail = build("gmail", "v1", credentials=creds)
    claude = Anthropic()

    processed_ids = load_processed_ids()

    results = gmail.users().messages().list(userId="me", q=build_gmail_query(), maxResults=100).execute()
    messages = [m for m in results.get("messages", []) if m["id"] not in processed_ids]

    if not messages:
        print("No new matching emails.")
        return

    for msg in messages:
        full_msg = gmail.users().messages().get(userId="me", id=msg["id"], format="full").execute()
        headers = full_msg["payload"].get("headers", [])
        subject = next((h["value"] for h in headers if h["name"] == "Subject"), "")
        sender = next((h["value"] for h in headers if h["name"] == "From"), "")
        body = get_body_text(full_msg["payload"]) or full_msg.get("snippet", "")

        fields = extract_fields(claude, subject, sender, body)
        fields["thread_id"] = full_msg["threadId"]

        print(json.dumps(fields, indent=2))
        print("-" * 40)

        # Mark as processed and persist immediately, so a crash mid-run
        # doesn't cause already-billed emails to be re-sent to Claude.
        processed_ids.add(msg["id"])
        save_processed_ids(processed_ids)


if __name__ == "__main__":
    main()
