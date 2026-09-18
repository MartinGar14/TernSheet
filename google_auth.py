"""Shared OAuth helper for Gmail/Sheets scripts — installed-app flow with a
cached token file, refreshed automatically when expired."""

import os

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

CREDENTIALS_PATH = "credentials.json"


def get_credentials(scopes, token_path):
    creds = None
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, scopes)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, scopes)
            # Force the Google account picker instead of silently reusing
            # whatever session is cached in the browser.
            creds = flow.run_local_server(port=0, prompt="select_account")

        with open(token_path, "w") as token_file:
            token_file.write(creds.to_json())

    return creds
