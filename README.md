# TernSheet

Automatically tracks internship applications in a Google Sheet by watching
Gmail for application-confirmation emails (Greenhouse, Lever, Workday, etc.),
extracting the key details with Claude, and adding/updating a row — no
manual data entry.

## How it works

1. Poll Gmail (cron, hourly) for emails from known ATS domains, received on
   or after a configurable start date.
2. Send each new email to Claude (Haiku) to extract structured fields.
3. Upsert a row in a Google Sheet, keyed on the Gmail **thread ID** — a new
   thread creates a row, a follow-up on a tracked thread updates it in place
   instead of duplicating it.
4. Emails already processed are never re-sent to the LLM or re-scanned.

## Sheet columns

`Company`, `Position`, `Date Applied`, `Link`, `Sender Email`, `Status`
(`Applied` / `Interview` / `Rejected` / `Offer` / `Replied`), `Last Updated`,
`Notes`, `Thread ID`.

## Setup

1. **Google Cloud Console**: create a project, enable the Gmail API and
   Sheets API, and set up an OAuth consent screen (Testing mode is fine —
   add your own Google account as a test user). Create OAuth credentials of
   type **Desktop app**, download the JSON, and save it in this folder as
   `credentials.json`.

2. **Python environment**:
   ```
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Config**: copy `.env.example` to `.env` and fill in:
   - `SHEET_ID` — the long ID in your Google Sheet's URL
   - `SHEET_NAME` — the tab name (defaults to `Sheet1` if unset)
   - `ANTHROPIC_API_KEY` — from console.anthropic.com
   - `START_DATE` — only scan emails on/after this date (`YYYY-MM-DD`)

4. **First run**:
   ```
   python sync_to_sheet.py
   ```
   Opens a browser window for Gmail OAuth, then Sheets OAuth (separate
   scopes, separate cached tokens: `token.json` and `token_sheets.json`).
   If multiple Google accounts are logged into your browser, make sure to
   pick the one that owns the target sheet.

5. **Automate** (cron, runs hourly):
   ```
   0 * * * * cd "/path/to/TernSheet" && venv/bin/python sync_to_sheet.py >> sync.log 2>&1
   ```
   Add via `crontab -e`. Output/errors land in `sync.log`.

## Files

- `sync_to_sheet.py` — the pipeline: Gmail fetch → Claude extraction → Sheets upsert. Run this one.
- `extract_email.py` — extraction layer only (prints results, no Sheets writes); useful for testing extraction in isolation.
- `google_auth.py` — shared OAuth helper.
- `test_extract_email.py`, `test_sync_to_sheet.py` — offline self-checks for the parsing/merge logic (`python test_*.py`).
- `test_gmail_auth.py`, `test_sheets_auth.py` — minimal standalone scripts proving each API connection works on its own.
- `state.json` (gitignored) — IDs of already-processed emails, so nothing is ever re-sent to the LLM twice.

## Notes

- Credentials never committed: `credentials.json`, `.env`, and `token*.json` are all gitignored.
- MVP scope: polling only, no push notifications, no dashboard — see `Claude.md` for full project context and design decisions.
