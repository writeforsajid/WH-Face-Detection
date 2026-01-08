from __future__ import print_function
import os.path
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from db.database import get_connection
from datetime import datetime
from utilities.environment_variables import load_environment
import asyncio
SCOPES = ['https://www.googleapis.com/auth/contacts']
load_environment("./../data/.env.webapp")


GOOGLE_PATH=os.getenv("GOOGLE_PATH","./../data/Google")

def get_people_service():
    creds = None
    tokenfilepath = os.path.join(GOOGLE_PATH, 'token.json')
    credentialsfilepath= os.path.join(GOOGLE_PATH, 'credentials.json')
    if os.path.exists(tokenfilepath):
        creds = Credentials.from_authorized_user_file(tokenfilepath, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                credentialsfilepath, SCOPES)
            creds = flow.run_local_server(port=0)

        with open(tokenfilepath, 'w') as token:
            token.write(creds.to_json())

    from googleapiclient.discovery import build
    return build('people', 'v1', credentials=creds)


def find_contact_by_phone(service, phone):
    results = service.people().searchContacts(
        query=phone,
        readMask="names,phoneNumbers"
    ).execute()

    return results.get("results", [])


def create_contact(service, name, phone):
    new_contact = {
        "names": [{"givenName": name}],
        "phoneNumbers": [{"value": phone}]
    }

    service.people().createContact(body=new_contact).execute()
    print("Contact created:", name)

def update_contact(service, resource_name, etag, new_name):
    update_body = {
        "etag": etag,
        "names": [{"givenName": new_name}]
    }

    service.people().updateContact(
        resourceName=resource_name,
        updatePersonFields="names",
        body=update_body
    ).execute()

    print("Contact updated:", new_name)

def is_docker():
    return os.path.exists("/.dockerenv")

def _add_or_edit_contact(guest_id,name):
    if not  is_docker():
        return{
            "status": 'failed - not in docker'
            }
    conn = get_connection() 
    cur = conn.cursor()
    cur.execute("SELECT phone_number FROM guests WHERE guest_id = ?", (guest_id,))
    row = cur.fetchone()
    if row:
        phone = row[0]          # Extract phone number
       
    conn.close()

    if not phone or not name:
        raise ValueError("guest_id and name are required.")
    service = get_people_service()

    matches = find_contact_by_phone(service, phone)

    if matches:
        contact = matches[0]['person']
        resource_name = contact['resourceName']
        etag = contact['etag']

        update_contact(service, resource_name, etag, name)
    else:
        create_contact(service, name, phone)

    return{
            "status": 'success'
            }


# # ---------- ASYNC WRAPPER ----------
# async def add_or_edit_contact(guest_id, name):
#     return await asyncio.to_thread(
#         _add_or_edit_contact_sync,
#         guest_id,
#         name
#     )

semaphore = asyncio.Semaphore(5)  # tune: 3–10

async def safe_add_or_edit_contact(guest_id, name):
    async with semaphore:
        return await _add_or_edit_contact(guest_id, name)