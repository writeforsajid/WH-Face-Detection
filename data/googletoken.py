from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
import os

SCOPES = ['https://www.googleapis.com/auth/contacts']

def get_token():
    creds = None
    token_file = 'token.json'

    if os.path.exists(token_file):
        print("token.json already exists.")
        return

    flow = InstalledAppFlow.from_client_secrets_file(
        'credentials.json', SCOPES
    )
    creds = flow.run_local_server(port=0)

    with open(token_file, 'w') as token:
        token.write(creds.to_json())

    print("token.json created!")

get_token()
