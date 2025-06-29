import pandas as pd
from datetime import datetime, timedelta
import os
import time

import config
from src.tavily_search import search_company_background
from src.email_generator import generate_fresher_email, populate_template, load_resume_text, track_email_performance
from src.gmail_api import get_gmail_service, create_message_with_attachment, send_message, check_for_replies, clean_email_address
from src.google_sheets_api import get_sheets_service, write_to_google_sheet
from src.email_automation import check_and_follow_up
from src.templates import FOLLOWUP_TEMPLATES

# --- Configuration ---
SPREADSHEET_ID = config.SPREADSHEET_ID
SENDER_EMAIL = config.SENDER_EMAIL
RANGE_NAME = config.RANGE_NAME
CSV_FILE = config.CSV_FILE
AI_ML_RESUME = config.AI_ML_RESUME
FULLSTACK_RESUME = config.FULLSTACK_RESUME

# --- Define a strict schema to prevent column creep errors permanently ---
EXPECTED_COLUMNS = {
    "Company": str,
    "Recipient Name": str,
    "Recipient Email": str,
    "Title": str,
    "Resume Type": str,
    "Email Status": str,
    "Sent Date": str,
    "Follow-up 1 Date": str,
    "Follow-up 2 Date": str,
    "Response Status": str
}

# --- Global DataFrame (initialized here for consistency, but will be loaded in main) ---
df = pd.DataFrame(columns=list(EXPECTED_COLUMNS.keys())).astype(EXPECTED_COLUMNS)

def sync_to_google_sheets(current_df):
    print("Syncing data to Google Sheets...")
    sheets_service = get_sheets_service()
    if sheets_service:
        try:
            write_to_google_sheet(sheets_service, SPREADSHEET_ID, RANGE_NAME, current_df)
            print("Data synced to Google Sheets successfully!")
        except Exception as e:
            print(f"Error syncing to Google Sheets: {e}")
    else:
        print("Failed to obtain Google Sheets service. Skipping sync.")

def main():
    global df # Declare df as global to modify the global DataFrame
    print("Starting the cold emailing bot...")

    # Get Gmail service
    gmail_service = get_gmail_service()
    if not gmail_service:
        print("Failed to obtain Gmail service. Exiting.")
        return

    # Load existing data or create a new DataFrame
    try:
        temp_df = pd.read_csv(CSV_FILE, encoding='utf-8')
        df = temp_df.reindex(columns=list(EXPECTED_COLUMNS.keys())).astype(EXPECTED_COLUMNS)
        df["Recipient Email"] = df["Recipient Email"].astype(str).apply(clean_email_address)
        print(f"Loaded {len(df)} existing entries from {CSV_FILE}")
    except (FileNotFoundError, KeyError):
        df = pd.DataFrame(columns=list(EXPECTED_COLUMNS.keys())).astype(EXPECTED_COLUMNS)
        print(f"Created a new DataFrame with expected columns.")

    # Process pending emails and check for replies
    for index, row in df.iterrows():
        recipient_email = clean_email_address(row["Recipient Email"])
        if not recipient_email:
            print(f"Skipping {row['Recipient Name']} due to invalid email address: {row['Recipient Email']}")
            continue

        # Check for replies first if email was sent and no response yet
        if row["Email Status"] == "Sent" and row["Response Status"] == "":
            print(f"Checking for replies from {recipient_email}...")
            if check_for_replies(gmail_service, "me", recipient_email):
                df.loc[index, "Response Status"] = "Replied"
                print(f"Reply found from {recipient_email}!")
                # Track response for initial email
                track_email_performance(template_name=row["template_used"], company_name=row["Company"], response_received=True, response_type="positive")
            else:
                print(f"No replies found from {recipient_email}.")

        # Process pending emails
        if row["Email Status"] == "Pending":
            recipient_name = row["Recipient Name"]
            company_name = row["Company"]
            recruiter_title = row.get("Title", "")
            role_type = row.get("Resume Type", "") # Assuming Resume Type can be used as role_type

            print(f"--- Processing: {recipient_name} at {company_name} ---")
            
            print("1. Researching company with Tavily...")
            company_info = search_company_background(company_name)

            if company_info:
                print("-> Research complete.")
                
                print("2. Generating personalized email with AI...")
                email_generation_result = generate_fresher_email(
                    tavily_results=company_info,
                    recipient_name=recipient_name,
                    recipient_title=recruiter_title,
                    company_name=company_name,
                    role_type=role_type # Use role_type from CSV or default
                )

                if "error" in email_generation_result:
                    print(f"-> Email generation failed: {email_generation_result['error']}. Skipping.")
                    continue

                email_body = email_generation_result["email_content"]
                final_resume_type = email_generation_result["resume_choice"]
                chosen_template_name = email_generation_result["template_used"]

                print(f"-> AI generated email using '{chosen_template_name}' template. Quality Score: {email_generation_result['quality_score']}")
                
                resume_path = AI_ML_RESUME if final_resume_type == "AI/ML" else FULLSTACK_RESUME

                if not os.path.exists(resume_path):
                    print(f"-> Resume not found at {resume_path}. Skipping.")
                    continue

                message = create_message_with_attachment(SENDER_EMAIL, recipient_email, email_body.split('\n')[0].replace('Subject: ', ''), email_body, resume_path) # Extract subject from body
                if send_message(gmail_service, "me", message):
                    df.loc[index, "Email Status"] = "Sent"
                    df.loc[index, "Sent Date"] = datetime.now().strftime("%Y-%m-%d").astype(str)
                    df.loc[index, "Resume Type"] = final_resume_type.astype(str)
                    # Store the template used for tracking
                    df.loc[index, "template_used"] = chosen_template_name.astype(str)
                    print(f"--> Email sent successfully to {recipient_email}.")
                    # Track initial email send
                    track_email_performance(template_name=chosen_template_name, company_name=company_name, response_received=False)
                    time.sleep(15) # Increased sleep time for more API calls
                else:
                    print(f"--> FAILED to send email to {recipient_email}.")
            else:
                print(f"--> Failed to get company info from Tavily. Skipping.")

        # Follow-up logic (using check_and_follow_up from email_automation)
        # This part is now handled by the imported function
        # The main loop will just call it once after processing all initial emails

    # Save data after processing all emails
    df.to_csv(CSV_FILE, index=False, encoding='utf-8')
    print("Updated emails.csv.")

    # Run follow-up logic for all contacts
    print("Running follow-up checks...")
    updated_df, follow_up_log = check_and_follow_up(df)
    df = updated_df # Update global df with results from follow-up
    df.to_csv(CSV_FILE, index=False, encoding='utf-8') # Save again after follow-ups
    print(follow_up_log)

    # Sync to Google Sheets after processing
    sync_to_google_sheets(df)

    print("Bot finished.")

if __name__ == "__main__":
    main()