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

SCOPES = ['https://www.googleapis.com/auth/gmail.send', 'https://www.googleapis.com/auth/gmail.readonly']

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
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=8080)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
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

def send_message(service, user_id, message):
    for attempt in range(3):
        try:
            sent_msg = service.users().messages().send(userId=user_id, body=message).execute()
            print(f"Message Id: {sent_msg['id']}")
            return sent_msg
        except Exception as e:
            print(f"Attempt {attempt + 1} failed: {e}")
            import time, random
            time.sleep(2 ** attempt + random.uniform(0.5, 1.5))
    return None

def check_for_replies(service, user_id, from_email):
    try:
        # --- FIX THE QUERY ---
        # Search for emails FROM the person, IN YOUR INBOX, that are UNREAD.
        # This is a much more reliable way to detect a new reply.
        query = f"from:{from_email} in:inbox is:unread"
        # --- END OF FIX ---
        response = service.users().messages().list(userId=user_id, q=query).execute()
        messages = response.get('messages', [])
        return len(messages) > 0
    except Exception as e:
        print(f'An error occurred while checking for replies: {e}')
        return False
