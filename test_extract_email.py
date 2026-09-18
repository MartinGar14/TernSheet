"""Self-check for the Gmail payload body-parsing logic — no network calls."""

import base64

from extract_email import get_body_text


def b64(text):
    return base64.urlsafe_b64encode(text.encode()).decode()


def demo():
    flat = {"mimeType": "text/plain", "body": {"data": b64("hello flat")}}
    assert get_body_text(flat) == "hello flat"

    multipart = {
        "mimeType": "multipart/alternative",
        "parts": [
            {"mimeType": "text/html", "body": {"data": b64("<p>html</p>")}},
            {"mimeType": "text/plain", "body": {"data": b64("hello multipart")}},
        ],
    }
    assert get_body_text(multipart) == "hello multipart"

    empty = {"mimeType": "text/html", "body": {"data": b64("<p>only html</p>")}}
    assert get_body_text(empty) == ""

    print("ok")


if __name__ == "__main__":
    demo()
