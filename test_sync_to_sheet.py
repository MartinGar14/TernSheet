"""Self-check for merge_row — no network calls."""

from sync_to_sheet import HEADERS, merge_row


def demo():
    old = ["Acme", "SWE Intern", "2026-09-05", "", "acme@ats.com", "Applied", "2026-09-05", "Applied.", "t1"]

    # Follow-up with a real status change; other fields null -> keep old.
    fields = {"company": None, "position": None, "date_applied": None, "link": None,
              "status": "Interview", "notes": "Interview invite."}
    merged = merge_row(old, fields, "acme@ats.com", "t1", "2026-09-10")
    assert merged[0] == "Acme"  # company preserved
    assert merged[5] == "Interview"  # status updated
    assert merged[6] == "2026-09-10"  # last updated bumped
    assert merged[7] == "Interview invite."  # notes updated
    assert len(merged) == len(HEADERS)

    # Vague nudge with no status extracted -> status stays, notes still bump.
    fields = {"company": None, "position": None, "date_applied": None, "link": None,
              "status": None, "notes": "Still reviewing applications."}
    merged = merge_row(old, fields, "acme@ats.com", "t1", "2026-09-12")
    assert merged[5] == "Applied"  # status unchanged, no false status-change

    print("ok")


if __name__ == "__main__":
    demo()
