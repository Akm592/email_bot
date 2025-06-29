import pandas as pd
from datetime import datetime, timedelta
import time
import os

from src.gmail_api import get_gmail_service, create_message_with_attachment, send_message, check_for_replies, clean_email_address
from src.email_generator import populate_template, load_resume_text # Import populate_template and load_resume_text
from src.tavily_search import search_company_background # Import for company info
from .templates import FOLLOWUP_TEMPLATES # Import follow-up templates
import config

def check_and_follow_up(df: pd.DataFrame):
    log_messages = []
    gmail_service = get_gmail_service()
    if not gmail_service:
        log_messages.append("Failed to obtain Gmail service. Cannot check for replies or send follow-ups.")
        return df, "\n".join(log_messages)

    for index, row in df.iterrows():
        recipient_email = clean_email_address(row["Recipient Email"])
        if not recipient_email:
            log_messages.append(f"Skipping follow-up for {row['Recipient Name']} due to invalid email address: {row['Recipient Email']}")
            continue

        # Check for replies
        if row["Email Status"] == "Sent" and row["Response Status"] == "":
            if check_for_replies(gmail_service, "me", recipient_email):
                df.loc[index, "Response Status"] = "Replied"
                log_messages.append(f"Reply found from {recipient_email}!")
            else:
                log_messages.append(f"No replies found from {recipient_email}.")

        # Follow-up logic
        if row["Email Status"] == "Sent" and row["Response Status"] == "" and row["Sent Date"]:
            sent_date = datetime.strptime(row["Sent Date"], "%Y-%m-%d")
            today = datetime.now()

            # Common variables for follow-ups
            recipient_name = row["Recipient Name"]
            company_name = row["Company"]
            role_type = row["Resume Type"] # Using Resume Type as role_type for consistency
            resume_path = config.AI_ML_RESUME if role_type == "AI/ML" else config.FULLSTACK_RESUME
            resume_text = load_resume_text(resume_path)
            tavily_results = json.loads(row["Company Info"])

            # First follow-up (24 hours after sent date)
            if (today - sent_date).days >= 1 and row["Follow-up 1 Date"] == "":
                log_messages.append(f"Sending first follow-up to {recipient_email}...")
                
                recipient_data = {
                    'Recipient Name': recipient_name,
                    'Company': company_name,
                    'Title': role_type
                }
                sender_data = {
                    'name': config.YOUR_NAME,
                    'degree': config.YOUR_DEGREE,
                    'key_skills': config.YOUR_KEY_SKILLS,
                    'project_experience': config.YOUR_PROJECT_EXPERIENCE,
                }
                follow_up_subject, follow_up_body = populate_template(
                    template_type='followup',
                    template_name="first_followup",
                    tavily_results=tavily_results,
                    recipient_data=recipient_data,
                    sender_data=sender_data
                )
                
                message = create_message_with_attachment(config.SENDER_EMAIL, recipient_email, follow_up_subject, follow_up_body, resume_path)
                if send_message(gmail_service, "me", message):
                    df.loc[index, "Follow-up 1 Date"] = today.strftime("%Y-%m-%d")
                    log_messages.append(f"First follow-up sent to {recipient_email}.")
                    time.sleep(10) # Rate limit
                else:
                    log_messages.append(f"Failed to send first follow-up to {recipient_email}.")

            # Second follow-up (72 hours after sent date)
            if (today - sent_date).days >= 3 and row["Follow-up 2 Date"] == "" and row["Follow-up 1 Date"] != "":
                log_messages.append(f"Sending second follow-up to {recipient_email}...")
                
                recipient_data = {
                    'Recipient Name': recipient_name,
                    'Company': company_name,
                    'Title': role_type
                }
                sender_data = {
                    'name': config.YOUR_NAME,
                    'degree': config.YOUR_DEGREE,
                    'key_skills': config.YOUR_KEY_SKILLS,
                    'project_experience': config.YOUR_PROJECT_EXPERIENCE,
                }
                follow_up_subject, follow_up_body = populate_template(
                    template_type='followup',
                    template_name="final_followup",
                    tavily_results=tavily_results,
                    recipient_data=recipient_data,
                    sender_data=sender_data
                )

                message = create_message_with_attachment(config.SENDER_EMAIL, recipient_email, follow_up_subject, follow_up_body, resume_path)
                if send_message(gmail_service, "me", message):
                    df.loc[index, "Follow-up 2 Date"] = today.strftime("%Y-%m-%d")
                    log_messages.append(f"Second follow-up sent to {recipient_email}.")
                    time.sleep(10) # Rate limit
                else:
                    log_messages.append(f"Failed to send second follow-up to {recipient_email}.")

    return df, "\n".join(log_messages)