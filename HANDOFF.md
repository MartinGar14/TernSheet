# TernSheet — Handoff (as of 2026-09-17)

## What this project is
Personal internship-application tracker. Watches Gmail for application
confirmation emails, extracts structured info via LLM, and logs/updates rows
in a Google Sheet automatically. Full spec in `Claude.md`.

## Status: steps 1–4 of the build order are done

| Step | Status |
|---|---|
| 1. Environment setup (venv, folder) | ✅ Done |
| 2. Google Cloud project + OAuth credentials | ✅ Done |
| 3. Minimal Gmail auth script | ✅ Done, tested working |
| 4. Minimal Sheets auth script | ✅ Done, tested working |
| 5. Classification + extraction (LLM) | ⏳ Not started — blocked on Anthropic API key decision |
| 6. Update-vs-new-row logic (thread ID) | Not started |
| 7. Scheduled job (cron) | Not started |
| 8. Polish (.env.example, README, screenshots) | Partially done (`.env.example` exists) |

## Repo
- GitHub: https://github.com/MartinGar14/TernSheet (private)
- Local path: `/Users/mg/Desktop/Tern Sheets`
- Branch: `main`, all work pushed

## What exists in the repo
- `Claude.md` — full project spec/context
- `requirements.txt` — Google API client libs + `python-dotenv`
- `.env.example` — template for `SHEET_ID`, `SHEET_NAME`, `ANTHROPIC_API_KEY`
- `.gitignore` — excludes `venv/`, `.env`, `credentials.json`, `token*.json`
- `test_gmail_auth.py` — proves Gmail OAuth works in isolation; prints last 5
  email subjects. Run via `python test_gmail_auth.py` (browser OAuth popup on
  first run, caches to `token.json`).
- `test_sheets_auth.py` — proves Sheets OAuth works in isolation; appends one
  test row to the target sheet. Run via `python test_sheets_auth.py` (browser
  OAuth popup on first run, caches to `token_sheets.json`).

## Local-only files (gitignored, NOT in repo — exist on this machine only)
- `credentials.json` — OAuth client secret downloaded from Google Cloud
  Console (Desktop app type)
- `token.json` — cached Gmail OAuth token (readonly scope)
- `token_sheets.json` — cached Sheets OAuth token (spreadsheets scope)
- `.env` — contains the real `SHEET_ID` (pointing at a live test Google
  Sheet: `1676xwRZ5atq-sJVTz86_rcA1fdVpDAf94et52q5FODY`)
- `venv/` — Python 3.9 virtualenv (note: 3.9 is EOL, Google libs warn on
  every run but work fine; consider upgrading Python later)

If picking this up on a different machine, these five need to be recreated:
`credentials.json` (from Google Cloud Console → same project → Credentials),
`.env` (copy `.env.example`, fill in `SHEET_ID`), and the two `token*.json`
files regenerate automatically on first script run.

## Design decisions made along the way
- OAuth client type: **Desktop app** (not Web), consent screen in Testing
  mode with the user's Rutgers email added as a test user.
- Gmail and Sheets auth use **separate token files** with separate scopes
  (`gmail.readonly` and `spreadsheets`) rather than one combined-scope token
  — keeps the two layers testable in isolation per the project's working
  style.
- GitHub repo created **private** for now; plan is to make it public once
  the MVP works end-to-end (per `Claude.md`'s "beyond personal use" section).

## Next step when resuming: Step 5 — classification + extraction
Decision needed first: get an `ANTHROPIC_API_KEY` from console.anthropic.com
and add it to `.env` (already has a commented-out placeholder line for it).

Once that's in place, the next script should:
1. Read real emails from Gmail (reuse the working auth from
   `test_gmail_auth.py`), pulling subject + sender + body snippet.
2. Optionally pre-filter using known ATS domains (`greenhouse.io`,
   `lever.co`, `myworkday.com`, etc.) before spending an LLM call.
3. Send subject+body to Claude, prompted to extract: company, position,
   date applied, link, status (`Applied`/`Interview`/`Rejected`/`Offer`/
   `Replied`).
4. Print the extracted structured result — still not touching Sheets yet,
   to keep this layer isolated and testable per the project's build order.

Only after that works reliably should update-vs-new-row logic (step 6, keyed
on Gmail thread ID) get wired in.
