# --- FIXED GMAIL UTILS ---
import os.path
import base64
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import re # Import re for regex operations

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import quopri

import google.generativeai as genai
import config

SCOPES = ['https://www.googleapis.com/auth/gmail.send', 'https://www.googleapis.com/auth/gmail.readonly']

try:
    genai.configure(api_key=config.GEMINI_API_KEY)
except Exception as e:
    print(f"Error configuring Gemini API in gmail_api: {e}")

def classify_email_body(email_body: str) -> str:
    model = genai.GenerativeModel("gemini-2.0-flash-lite")
    prompt = f"""
    Analyze the following email body and classify it as 'human', 'auto-reply (out of office)', or 'other (promotional/spam)'.
    Respond with ONLY ONE of these classifications.

    Email: '{email_body}'
    """
    try:
        response = model.generate_content(prompt)
        classification = response.text.strip().lower()
        if "human" in classification:
            return "human"
        elif "auto-reply" in classification or "out of office" in classification:
            return "auto-reply (out of office)"
        else:
            return "other (promotional/spam)"
    except Exception as e:
        print(f"Error classifying email body with Gemini: {e}")
        return "unknown"

def check_for_replies(service, user_id, from_email):
    try:
        query = f"from:{from_email} in:inbox is:unread"
        response = service.users().messages().list(userId=user_id, q=query).execute()
        messages = response.get('messages', [])

        if not messages:
            return None, None # No new messages

        # Get the first unread message
        msg_id = messages[0]['id']
        message = service.users().messages().get(userId=user_id, id=msg_id, format='full').execute()

        # Extract email body
        payload = message['payload']
        parts = payload.get('parts', [])
        email_body = ""
        if parts:
            for part in parts:
                if part['mimeType'] == 'text/plain':
                    data = part['body']['data']
                    email_body = base64.urlsafe_b64decode(data).decode('utf-8')
                    break
        else:
            data = payload['body']['data']
            email_body = base64.urlsafe_b64decode(data).decode('utf-8')

        # Mark the message as read after processing
        service.users().messages().modify(userId=user_id, id=msg_id, body={'removeLabelIds': ['UNREAD']}).execute()

        classification = classify_email_body(email_body)
        return email_body, classification

    except Exception as e:
        print(f'An error occurred while checking for replies: {e}')
        return None, None
