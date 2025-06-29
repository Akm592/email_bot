import pandas as pd
from datetime import datetime, timedelta
import time
import os
import json
import logging


from src.gmail_api import get_gmail_service, create_message_with_attachment, send_message, check_for_replies, clean_email_address
from src.email_generator import populate_template # Import populate_template
from src.tavily_search import search_company_background # Import for company info
from .templates import FOLLOWUP_TEMPLATES # Import follow-up templates
import config

def check_and_follow_up(df: pd.DataFrame, resume_cache: dict):
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
            email_body, classification = check_for_replies(gmail_service, "me", recipient_email)
            if email_body:
                df.loc[index, "Response Status"] = f"Replied ({classification})"
                log_messages.append(f"Reply found from {recipient_email}! Classification: {classification}")
                
                # Stop follow-up sequence for human replies
                if classification == "human":
                    log_messages.append(f"Stopping follow-up sequence for {recipient_email} due to human reply.")
                    continue # Skip to next contact
                elif classification == "auto-reply (out of office)":
                    log_messages.append(f"Auto-reply detected from {recipient_email}. Pausing follow-up sequence.")
                    # We don't continue here, allowing the follow-up logic to potentially re-engage later
            else:
                log_messages.append(f"No replies found from {recipient_email}.")

        # Follow-up logic
        # Only proceed if no human reply and no follow-up 3 has been sent
        if row["Email Status"] == "Sent" and row["Response Status"] != "Replied (human)" and row["Follow-up 3 Date"] == "" and row["Sent Date"]:
            sent_date = datetime.strptime(row["Sent Date"], "%Y-%m-%d")
            today = datetime.now()

            # Common variables for follow-ups
            recipient_name = row["Recipient Name"]
            company_name = row["Company"]
            role_type = row["Resume Type"] # Using Resume Type as role_type for consistency
            resume_text = resume_cache.get(role_type)
            tavily_results = json.loads(row["Company Info"])

            # Determine resume path for attachment
            resume_path = config.AI_ML_RESUME if role_type == "AI/ML" else config.FULLSTACK_RESUME

            if not os.path.exists(resume_path):
                log_messages.append(f"-> Resume not found at {resume_path}. Skipping follow-up for {recipient_email}.")
                continue

            # Follow-up #1 (The Gentle Nudge)
            if row["Follow-up 1 Date"] == "" and (today - sent_date).days >= config.FOLLOWUP_1_DAYS and (today - sent_date).days <= config.FOLLOWUP_1_DAYS + 1:
                log_messages.append(f"Sending first follow-up to {recipient_email}...")
                template_name = "first_followup"
                
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
                    template_name=template_name,
                    tavily_results=tavily_results,
                    recipient_data=recipient_data,
                    sender_data=sender_data,
                    resume_text=resume_text
                )
                
                message = create_message_with_attachment(config.SENDER_EMAIL, recipient_email, follow_up_subject, follow_up_body, resume_path)
                if send_message(gmail_service, "me", message):
                    df.loc[index, "Follow-up 1 Date"] = today.strftime("%Y-%m-%d")
                    log_messages.append(f"First follow-up sent to {recipient_email}.")
                    time.sleep(10) # Rate limit
                else:
                    log_messages.append(f"Failed to send first follow-up to {recipient_email}.")

            # Follow-up #2 (The Value-Add)
            elif row["Follow-up 1 Date"] != "" and row["Follow-up 2 Date"] == "":
                follow_up_1_date = datetime.strptime(row["Follow-up 1 Date"], "%Y-%m-%d")
                if (today - follow_up_1_date).days >= config.FOLLOWUP_2_DAYS_AFTER_1:
                    log_messages.append(f"Sending second follow-up (value-add) to {recipient_email}...")
                    template_name = "value_add_followup"

                    # Smart Content Retrieval for Value-Add Follow-up
                    # Perform a targeted Tavily search for recent news/updates about the company
                    recent_company_info = search_company_background(f"Recent news, blog posts, or announcements from {company_name} in the last 7 days")
                    # Pass this new, small piece of information into the populate_template function
                    tavily_results['recent_news_for_followup'] = recent_company_info.get('recent_news', 'No new insights found.')

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
                        template_name=template_name,
                        tavily_results=tavily_results, # Now includes recent_news_for_followup
                        recipient_data=recipient_data,
                        sender_data=sender_data,
                        resume_text=resume_text
                    )

                    message = create_message_with_attachment(config.SENDER_EMAIL, recipient_email, follow_up_subject, follow_up_body, resume_path)
                    if send_message(gmail_service, "me", message):
                        df.loc[index, "Follow-up 2 Date"] = today.strftime("%Y-%m-%d")
                        log_messages.append(f"Second follow-up sent to {recipient_email}.")
                        time.sleep(10) # Rate limit
                    else:
                        log_messages.append(f"Failed to send second follow-up to {recipient_email}.")

            # Follow-up #3 (The Closing Loop)
            elif row["Follow-up 2 Date"] != "" and row["Follow-up 3 Date"] == "":
                follow_up_2_date = datetime.strptime(row["Follow-up 2 Date"], "%Y-%m-%d")
                if (today - follow_up_2_date).days >= config.FOLLOWUP_3_DAYS_AFTER_2:
                    log_messages.append(f"Sending third follow-up (closing loop) to {recipient_email}...")
                    template_name = "final_followup" # This template needs to be created

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
                        template_name=template_name,
                        tavily_results=tavily_results, # Will be enhanced in Pillar 2
                        recipient_data=recipient_data,
                        sender_data=sender_data,
                        resume_text=resume_text
                    )

                    message = create_message_with_attachment(config.SENDER_EMAIL, recipient_email, follow_up_subject, follow_up_body, resume_path)
                    if send_message(gmail_service, "me", message):
                        df.loc[index, "Follow-up 3 Date"] = today.strftime("%Y-%m-%d")
                        log_messages.append(f"Third follow-up sent to {recipient_email}.")
                        time.sleep(10) # Rate limit
                    else:
                        log_messages.append(f"Failed to send third follow-up to {recipient_email}.")

    return df, "\n".join(log_messages)