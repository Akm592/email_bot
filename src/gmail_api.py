import logging

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

logger = logging.getLogger(__name__)

SCOPES = ['https://www.googleapis.com/auth/gmail.send', 'https://www.googleapis.com/auth/gmail.readonly', 'https://www.googleapis.com/auth/gmail.modify']

try:
    genai.configure(api_key=config.GEMINI_API_KEY)
except Exception as e:
    logger.error(f"Error configuring Gemini API in gmail_api: {e}")

def clean_email_address(email):
    email = str(email).strip()
    # Explicitly replace +AEA- with @
    email = email.replace('+AEA-', '@')
    try:
        # Attempt to decode if it looks like it might be quoted-printable
        if '=' in email:
            email = quopri.decodestring(email).decode('utf-8')
    except Exception:
        pass # Ignore decoding errors, use original string

    # Regex to find a valid email address, even if surrounded by other text or names
    match = re.search(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', email)
    if match:
        return match.group(0)
    return None # Return None if no valid email address is found

def get_gmail_service():
    creds = None
    logger.info("Attempting to get Gmail service.")
    if os.path.exists('token.json'):
        try:
            creds = Credentials.from_authorized_user_file('token.json', SCOPES)
        except ValueError:
            logger.warning("Invalid token.json found, re-authenticating.")
            creds = None  # Invalid token, proceed to re-authenticate
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            logger.info("Refreshing Gmail API credentials.")
            creds.refresh(Request())
        else:
            if os.path.exists('token.json'):
                os.remove('token.json') # Remove invalid token
                logger.info("Removed invalid token.json.")
            logger.info("Initiating new Gmail API authentication flow.")
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=8080, access_type='offline', prompt='consent')
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
        logger.info("Gmail API authentication successful, token saved.")
    return build('gmail', 'v1', credentials=creds)

def create_message_with_attachment(sender, to, subject, message_text, file):
    """Create a message for an email. Now sends as HTML."""
    if not isinstance(message_text, str):
        raise TypeError(f"message_text must be a string, got {type(message_text)}")

    message = MIMEMultipart()
    cleaned_to = clean_email_address(to)
    if not cleaned_to:
        raise ValueError(f"Invalid recipient email address: {to}")

    message['to'] = cleaned_to
    cleaned_sender = clean_email_address(sender)
    if not cleaned_sender:
        raise ValueError(f"Invalid sender email address: {sender}")
    message['subject'] = subject
    
    # --- THIS IS THE KEY CHANGE ---
    # We now attach the message as 'html' instead of 'plain'
    message.attach(MIMEText(message_text, 'html', 'utf-8'))

    with open(file, 'rb') as fp:
        part = MIMEBase('application', 'octet-stream')
        part.set_payload(fp.read())
    encoders.encode_base64(part)
    part.add_header('Content-Disposition', f'attachment; filename="{os.path.basename(file)}"')
    message.attach(part)

    raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
    return {'raw': raw_message}

def send_message(service, user_id, message, recipient_email):
    """Sends an email message."""
    logger.info(f"Attempting to send email to {recipient_email}.")
    for attempt in range(3):
        try:
            sent_msg = service.users().messages().send(userId=user_id, body=message).execute()
            logger.info(f"Message sent to {recipient_email}, Message Id: {sent_msg['id']}")
            return sent_msg
        except Exception as e:
            logger.warning(f"Attempt {attempt + 1} failed to send email to {recipient_email}: {e}")
            import time, random
            time.sleep(2 ** attempt + random.uniform(0.5, 1.5))
    logger.error(f"Failed to send email after 3 attempts to {recipient_email}.")
    return None

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
        logger.error(f"Error classifying email body with Gemini: {e}")
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