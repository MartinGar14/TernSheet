# TernSheet — Handoff (as of 2026-09-18)

## What this project is
Personal internship-application tracker. Watches Gmail for application
confirmation emails, extracts structured info via LLM, and logs/updates rows
in a Google Sheet automatically. Full spec in `Claude.md`. User-facing setup
instructions live in `README.md`.

## Status: steps 1–7 of the build order are done, MVP is live

| Step | Status |
|---|---|
| 1. Environment setup (venv, folder) | ✅ Done |
| 2. Google Cloud project + OAuth credentials | ✅ Done |
| 3. Minimal Gmail auth script | ✅ Done, tested working |
| 4. Minimal Sheets auth script | ✅ Done, tested working |
| 5. Classification + extraction (LLM) | ✅ Done — `extract_email.py`, Claude Haiku (`claude-haiku-4-5-20251001`) |
| 6. Update-vs-new-row logic (thread ID) | ✅ Done — `sync_to_sheet.py` |
| 7. Scheduled job (cron) | ✅ Done — runs hourly |
| 8. Polish (.env.example, README, screenshots) | Partial — README done, no screenshots yet |

The tracker is running for real: as of today the Sheet has 10 real
internship applications pulled from the user's inbox (Figma, Howmet
Aerospace, Epic, Cognizant ×2, DTCC, LCSR, BNY, NYC ×2).

## Repo
- GitHub: https://github.com/MartinGar14/TernSheet (private)
- Local path: `/Users/mg/Desktop/Tern Sheets`
- Branch: `main`, all work pushed (latest commit `e050cdd`)

## What exists in the repo
- `Claude.md` — full project spec/context
- `README.md` — setup + usage instructions (the one to follow on a fresh machine)
- `google_auth.py` — shared OAuth helper (installed-app flow, cached token, forces the Google account picker via `prompt="select_account"` rather than silently reusing a cached browser session)
- `extract_email.py` — Gmail fetch + Claude extraction layer; prints results only, no Sheets writes. Also owns the Gmail query builder, date-bound + state-file dedup logic, and body-parsing helper — `sync_to_sheet.py` imports from it rather than duplicating.
- `sync_to_sheet.py` — **the real pipeline**, run this one. Gmail fetch → Claude extraction → Sheets upsert keyed on thread ID.
- `test_extract_email.py`, `test_sync_to_sheet.py` — offline self-checks (body parser, row-merge logic), no network calls
- `test_gmail_auth.py`, `test_sheets_auth.py` — original minimal proof-of-auth scripts from steps 3–4, still standalone
- `requirements.txt` — Google API client libs, `python-dotenv`, `anthropic`
- `.env.example` — template for `SHEET_ID`, `SHEET_NAME`, `ANTHROPIC_API_KEY`, `START_DATE`
- `.gitignore` — excludes `venv/`, `.env`, `credentials.json`, `token*.json`, `state.json`, `sync.log`

## Local-only files (gitignored, NOT in repo)
- `credentials.json` (locally saved as `Credentials.json` — case mismatch, harmless on macOS's case-insensitive filesystem and git's case-insensitive matching here, but would break on Linux; not yet renamed)
- `token.json` (Gmail OAuth, readonly scope), `token_sheets.json` (Sheets OAuth, spreadsheets scope)
- `.env` — real `SHEET_ID` (`1BGYjXXcugkbOohoyNRpMWNtVDu3gY9DcwEU-kYt0Yks`), `SHEET_NAME=Sheet1`, `ANTHROPIC_API_KEY`, `START_DATE=2026-09-01`
- `state.json` — IDs of already-processed emails, so nothing is re-sent to the LLM or re-scanned once seen
- `sync.log` — stdout/stderr from cron runs
- `venv/` — Python 3.9 (EOL, Google libs warn on every run but work fine)

## Automation
Cron entry (hourly, installed via `crontab -e`):
```
0 * * * * cd "/Users/mg/Desktop/Tern Sheets" && venv/bin/python sync_to_sheet.py >> sync.log 2>&1
```
Caveats to know about, not bugs:
- Only runs while the Mac is awake; doesn't catch up missed runs (it just re-queries Gmail next time it fires, so nothing is lost, just delayed).
- OAuth consent screen is in **Testing** mode — Google expires refresh tokens after ~7 days for unverified apps. When that happens, `sync.log` will show an auth error; fix is deleting `token.json`/`token_sheets.json` and running `sync_to_sheet.py` interactively once to re-auth.

## Design decisions made along the way
- OAuth client type: **Desktop app**, consent screen in Testing mode, user's Rutgers email as test user.
- Gmail and Sheets auth use separate token files/scopes, factored into one shared `google_auth.py` helper (was duplicated 3x before being factored out).
- Model: **Claude Haiku** (`claude-haiku-4-5-20251001`), not Sonnet — this is simple classify+extract, not a task that benefits from heavier reasoning. Side-by-side test on real emails showed Haiku was actually *more* accurate than Sonnet here (Sonnet was force-labeling non-application emails with `status: "Applied"`; Haiku correctly returned `null`).
- Gmail query is **subject-keyword-based, not domain-based**: the original plan (filter by ATS domains like `greenhouse.io`) missed almost every real email, since companies send from their own domain (`no-reply@figma.com`), not the ATS's. Fixed to match on subject keywords (`application`, `applying`, `interview`, `internship`) plus the ATS domains as a bonus signal; false positives are cheap since the LLM step filters them (`company: null` → skipped, not written to the sheet).
- Thread-ID matching (per `Claude.md`) has one known edge case, accepted rather than engineered around: if a company's mail server threads two *different* job applications into the same Gmail conversation (happened once, two different Cognizant reqs), they'll merge into one sheet row. Considered more reliable than fuzzy company-name matching overall, per the original spec.
- Dedup state (`state.json`) tracks processed message IDs rather than advancing a date cursor — avoids Gmail's day-granularity `after:` boundary causing same-day re-scans or gaps.

## Bugs found and fixed this session (via testing against the real inbox, not spec review)
1. Sonnet 5 (later Haiku too, defensively) returns a `ThinkingBlock` before the text block by default — code was assuming `content[0]` was text and crashed. Now finds the `text`-typed block explicitly.
2. Model sometimes wraps JSON output in ` ```json ` fences — stripped before parsing.
3. `max_tokens=500` let thinking consume the whole budget with zero text output on one real response — bumped to 1024, plus a graceful fallback (`{"error": ...}`) instead of crashing if it recurs.
4. Sheets API 403 "caller does not have permission" — not a code bug, a Google-account mismatch (OAuth popup silently reused a cached browser session for the wrong account). Fixed by forcing `prompt="select_account"` in `google_auth.py` so the account picker always shows.
5. Gmail filter too narrow (see design decisions above) — broadened to subject keywords.
6. Same-run thread-dedup bug: `thread_map` was loaded once at the start of a run and never updated as new rows were written *during* that run, so two emails on the same thread in one batch created two rows instead of the second updating the first. Fixed by updating the in-memory map immediately after every append/update.

## Not done yet (step 8 polish, later per user)
- Screenshot/GIF of the Sheet updating, for the README
- Rename local `Credentials.json` → `credentials.json` for cross-platform safety
- Public release (currently private repo; user said "later")
- No notification mechanism built (email/push/etc. on real status changes) — `Claude.md` specifies the *behavior* (only flag real status changes, not every touch), which `sync_to_sheet.py` does via console output (`STATUS CHANGE [...]`), but there's no delivery mechanism beyond that console line + `sync.log`. Worth asking the user whether they want one before building it — not specified in the original build order.
