import logging

import os.path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

logger = logging.getLogger(__name__)

SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

def get_sheets_service():
    creds = None
    logger.info("Attempting to get Google Sheets service.")
    if os.path.exists('token_sheets.json'):
        try:
            creds = Credentials.from_authorized_user_file('token_sheets.json', SCOPES)
        except ValueError:
            logger.warning("Invalid token_sheets.json found, re-authenticating.")
            creds = None  # Invalid token, proceed to re-authenticate
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            logger.info("Refreshing Google Sheets API credentials.")
            creds.refresh(Request())
        else:
            if os.path.exists('token_sheets.json'):
                os.remove('token_sheets.json') # Remove invalid token
                logger.info("Removed invalid token_sheets.json.")
            logger.info("Initiating new Google Sheets API authentication flow.")
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=8081, access_type='offline', prompt='consent') # Added access_type and prompt
        with open('token_sheets.json', 'w') as token:
            token.write(creds.to_json())
        logger.info("Google Sheets API authentication successful, token saved.")
    return build('sheets', 'v4', credentials=creds)

def write_to_google_sheet(service, spreadsheet_id, range_name, dataframe):
    logging.info(f"Attempting to write data to Google Sheet: {spreadsheet_id} in range {range_name}.")
    try:
        # Clear existing data
        service.spreadsheets().values().clear(
            spreadsheetId=spreadsheet_id, range=range_name
        ).execute()

        # Prepare data for writing (including headers)
        values = [dataframe.columns.values.tolist()] + dataframe.values.tolist()
        body = {'values': values}

        result = service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id, range=range_name,
            valueInputOption='RAW', body=body).execute()
        logging.info("Data successfully written to Google Sheet.")
        return result
    except Exception as e:
        logging.error(f"Error writing data to Google Sheet: {e}")
        raise
