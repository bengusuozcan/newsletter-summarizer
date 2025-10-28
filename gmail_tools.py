from __future__ import annotations
import base64, os, re, html
from typing import List, Dict
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly",
          "https://www.googleapis.com/auth/gmail.modify"]

def gmail_service():
    creds = None
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    if not creds or not creds.valid:
        flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
        creds = flow.run_local_server(port=0)
        with open("token.json","w") as f:
            f.write(creds.to_json())
    return build("gmail","v1", credentials=creds)

def list_newsletters(q: str, max_results=20) -> List[Dict]:
    svc = gmail_service()
    resp = svc.users().messages().list(userId="me", q=q, maxResults=max_results).execute()
    ids = [m["id"] for m in resp.get("messages", [])]
    msgs = [svc.users().messages().get(userId="me", id=i, format="full").execute() for i in ids]
    return msgs

def extract_plain_text(msg: Dict):
    headers = {h["name"].lower(): h["value"] for h in msg["payload"].get("headers", [])}
    subject = headers.get("subject","")
    parts = [msg["payload"]]
    text_chunks = []
    while parts:
        p = parts.pop()
        if p.get("parts"): parts.extend(p["parts"])
        data = p.get("body",{}).get("data")
        if not data: continue
        content = base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")
        if "text/plain" in p.get("mimeType",""):
            text_chunks.append(content)
        elif "text/html" in p.get("mimeType","") and not text_chunks:
            text = re.sub("<[^>]+>", " ", content)
            text_chunks.append(html.unescape(text))
    return subject, "\n".join(text_chunks).strip()

def archive_message(message_id: str):
    svc = gmail_service()
    svc.users().messages().modify(
        userId="me", id=message_id,
        body={"removeLabelIds": ["INBOX"]}
    ).execute()

def get_labels_map():
    svc = gmail_service()
    resp = svc.users().labels().list(userId="me").execute()
    return {l["name"]: l["id"] for l in resp.get("labels", [])}

def get_or_create_label(label_name: str) -> str:
    svc = gmail_service()
    labels = get_labels_map()
    if label_name in labels:
        return labels[label_name]
    body = {"name": label_name, "labelListVisibility": "labelShow", "messageListVisibility": "show"}
    created = svc.users().labels().create(userId="me", body=body).execute()
    return created["id"]

def add_label_id(message_id: str, label_id: str):
    svc = gmail_service()
    svc.users().messages().modify(userId="me", id=message_id, body={"addLabelIds": [label_id]}).execute()

def remove_label_id(message_id: str, label_id: str):
    svc = gmail_service()
    svc.users().messages().modify(userId="me", id=message_id, body={"removeLabelIds": [label_id]}).execute()

def list_all_by_label(label_name: str, include_spam_trash=False) -> list[dict]:
    """Return ALL messages for a label (paginated)."""
    svc = gmail_service()
    label_id = get_or_create_label(label_name)
    msgs, page = [], None
    while True:
        resp = svc.users().messages().list(
            userId="me",
            labelIds=[label_id],
            includeSpamTrash=include_spam_trash,
            pageToken=page,
            maxResults=500
        ).execute()
        for m in resp.get("messages", []):
            full = svc.users().messages().get(userId="me", id=m["id"], format="full").execute()
            msgs.append(full)
        page = resp.get("nextPageToken")
        if not page: break
    return msgs

def list_all_by_query(q: str) -> list[dict]:
    """Return ALL messages matching a Gmail search query (paginated)."""
    svc = gmail_service()
    msgs, page = [], None
    while True:
        resp = svc.users().messages().list(userId="me", q=q, pageToken=page, maxResults=500).execute()
        for m in resp.get("messages", []):
            full = svc.users().messages().get(userId="me", id=m["id"], format="full").execute()
            msgs.append(full)
        page = resp.get("nextPageToken")
        if not page: break
    return msgs

