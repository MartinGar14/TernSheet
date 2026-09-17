# TernSheet — Project Context

## What it is
A personal internship-application tracker. Companies almost always send a
confirmation email when you apply (often via an ATS like Greenhouse, Lever,
or Workday). This tool watches Gmail, detects those emails, extracts the key
info, and logs/updates a row in a Google Sheet automatically — so applications
are tracked without any manual data entry.

## Core concept
- Poll Gmail for new emails related to internship applications.
- Extract structured fields from each relevant email.
- Add a new row for a first-time application.
- When a follow-up email arrives on the same thread, UPDATE that row instead
  of creating a new one.
- Only notify the user on real status changes (interview / reject / offer) —
  not on every touch. A generic "still reviewing applications" nudge should
  just quietly bump Last Updated, not fire a notification.

## Google Sheet columns
- Company
- Position
- Date Applied
- Link (if the email provided one — portal/careers page)
- Sender Email
- Status: `Applied` / `Interview` / `Rejected` / `Offer` / `Replied` (fallback
  for follow-ups that don't clearly fit the above)
- Last Updated
- Raw snippet/notes — first line or two of the email, so misclassifications
  are easy to spot and fix manually

## Matching logic
- Use the Gmail **thread ID** as the key for "is this a follow-up to
  something already tracked" — far more reliable than matching on company
  name strings, since branding/wording varies a lot.

## Tech stack / architecture
- **Language:** Python
- **Gmail access:** Gmail API via OAuth. MVP uses simple polling (cron /
  Task Scheduler, every 15–30 min) — NOT Pub/Sub push notifications. Push is
  a stretch goal for a later, more polished version, not part of the MVP.
- **Sheet writes:** Google Sheets API
- **Classification/extraction:** LLM-based extraction (subject + body →
  structured fields) is the primary approach, since email phrasing varies too
  much for regex alone to hold up. Keyword/domain rules (e.g. greenhouse.io,
  lever.co, myworkday.com) can help as a first-pass filter before the LLM
  call.

## Build order — isolate each layer, don't combine early
1. Environment setup: Python, virtualenv, VS Code, project folder.
2. Google Cloud Console: new project, enable Gmail API + Sheets API, set up
   OAuth consent screen (Testing mode is fine), download `credentials.json`.
3. Minimal script: authenticate to Gmail, print the last 5 email subjects.
   Nothing else yet — this proves auth works in isolation.
4. Minimal script: authenticate to Sheets, write one test row. Proves Sheets
   access independently of the Gmail piece.
5. Add classification + extraction logic on top of the working Gmail read.
6. Add update-vs-new-row logic using thread ID.
7. Wrap in a scheduled job (cron / Task Scheduler) for automation.
8. Polish: `.env` + `.env.example` (secrets never committed), README with
   setup steps, screenshot/GIF of the Sheet updating.

## Scope decisions already made
- MVP = polling + Google Sheets output only. No dashboard, no Pub/Sub push —
  those are explicitly out of scope for the first (personal-use) version.
- Target timeline: ~3 days for the personal-use MVP, achievable only if scope
  stays this narrow.

## Beyond personal use (later, not now)
- Plan to open-source on GitHub once working. Credentials must never be
  committed — `.env` + `.gitignore` from the start.
- Plan to use as a resume bullet — emphasize the API integration (Gmail +
  Sheets + OAuth), LLM-based extraction, and automation angle.

## Working style
- Prefers building and testing each piece in isolation before combining them,
  rather than writing the full pipeline in one pass.