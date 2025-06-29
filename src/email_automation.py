import pandas as pd
from datetime import datetime, timedelta
import time
import os
import json
import logging

from src.gmail_api import get_gmail_service, create_message_with_attachment, send_message, check_for_replies, clean_email_address
from src.email_generator import populate_template, extract_sender_details_from_resume
from src.tavily_search import search_company_background
from .templates import FOLLOWUP_TEMPLATES
import config

def check_and_follow_up(df: pd.DataFrame, resume_cache: dict):
    log_messages = []
    gmail_service = get_gmail_service()
    if not gmail_service:
        log_messages.append("Failed to obtain Gmail service. Cannot proceed.")
        return df, "\n".join(log_messages)

    for index, row in df.iterrows():
        # --- REPLY CHECKING LOGIC (Remains the same, it's already excellent) ---
        recipient_email = clean_email_address(row["Recipient Email"])
        if not recipient_email:
            continue

        if row["Email Status"] == "Sent" and "Replied" not in str(row["Response Status"]):
            email_body, classification = check_for_replies(gmail_service, "me", recipient_email)
            if email_body:
                df.loc[index, "Response Status"] = f"Replied ({classification})"
                log_messages.append(f"Reply from {recipient_email} classified as '{classification}'.")
                # Immediately stop if a human replied
                if classification == "human":
                    log_messages.append(f"-> Sequence HALTED for {recipient_email}.")
                    continue # Move to the next person

        # --- RESTRUCTURED AND FIXED FOLLOW-UP LOGIC ---
        # Condition: Email was sent, no human has replied, and the sequence is not complete.
        if row["Email Status"] == "Sent" and "Replied (human)" not in str(row["Response Status"]) and pd.isna(row["Follow-up 3 Date"]):
            sent_date = datetime.strptime(row["Sent Date"], "%Y-%m-%d")
            today = datetime.now()
            
            # --- Common data preparation ---
            role_type = row["Resume Type"]
            resume_text = resume_cache.get(role_type)
            if not resume_text:
                log_messages.append(f"-> Resume text for {role_type} not found. Skipping follow-up for {recipient_email}.")
                continue
            
            # Dynamically parse sender details from the correct resume
            sender_details = extract_sender_details_from_resume(resume_text)
            sender_data = {
                'name': sender_details.get("name", config.YOUR_NAME),
                'degree': sender_details.get("degree", ""),
                'key_skills': sender_details.get("key_skills", ""),
                'project_experience': sender_details.get("project_experience", ""),
            }
            recipient_data = {'Company': row["Company"], 'Title': row.get("Title", "")}
            tavily_results = json.loads(row["Company Info"]) if pd.notna(row["Company Info"]) else {}
            resume_path = config.AI_ML_RESUME if role_type == "AI/ML" else config.FULLSTACK_RESUME

            # --- Stage 1: First Follow-up ---
            if pd.isna(row["Follow-up 1 Date"]):
                if (today - sent_date).days >= config.FOLLOWUP_1_DAYS:
                    log_messages.append(f"-> Sending Follow-up #1 to {recipient_email}...")
                    subject, body = populate_template('followup', "first_followup", tavily_results, recipient_data, sender_data, resume_text)
                    message = create_message_with_attachment(config.SENDER_EMAIL, recipient_email, subject, body, resume_path)
                    if send_message(gmail_service, "me", message):
                        df.loc[index, "Follow-up 1 Date"] = today.strftime("%Y-%m-%d")
                        log_messages.append(f"--> Follow-up #1 sent successfully.")
                        time.sleep(10)
                    else:
                        log_messages.append(f"--> FAILED to send Follow-up #1.")
                continue # Process one follow-up per run for a given contact

            # --- Stage 2: Second Follow-up (Value-Add) ---
            if pd.notna(row["Follow-up 1 Date"]) and pd.isna(row["Follow-up 2 Date"]):
                follow_up_1_date = datetime.strptime(row["Follow-up 1 Date"], "%Y-%m-%d")
                if (today - follow_up_1_date).days >= config.FOLLOWUP_2_DAYS_AFTER_1:
                    log_messages.append(f"-> Sending Follow-up #2 (Value-Add) to {recipient_email}...")
                    
                    # Add new, fresh insight for this specific follow-up
                    tavily_results['recent_news_for_followup'] = search_company_background(f"Recent news from {row['Company']} in the last 7 days").get('recent_news')
                    
                    subject, body = populate_template('followup', "value_add_followup", tavily_results, recipient_data, sender_data, resume_text)
                    message = create_message_with_attachment(config.SENDER_EMAIL, recipient_email, subject, body, resume_path)
                    if send_message(gmail_service, "me", message):
                        df.loc[index, "Follow-up 2 Date"] = today.strftime("%Y-%m-%d")
                        log_messages.append(f"--> Follow-up #2 sent successfully.")
                        time.sleep(10)
                    else:
                        log_messages.append(f"--> FAILED to send Follow-up #2.")
                continue

            # --- Stage 3: Third Follow-up (Closing Loop) ---
            if pd.notna(row["Follow-up 2 Date"]) and pd.isna(row["Follow-up 3 Date"]):
                follow_up_2_date = datetime.strptime(row["Follow-up 2 Date"], "%Y-%m-%d")
                if (today - follow_up_2_date).days >= config.FOLLOWUP_3_DAYS_AFTER_2:
                    log_messages.append(f"-> Sending Follow-up #3 (Closing Loop) to {recipient_email}...")
                    subject, body = populate_template('followup', "final_followup", tavily_results, recipient_data, sender_data, resume_text)
                    message = create_message_with_attachment(config.SENDER_EMAIL, recipient_email, subject, body, resume_path)
                    if send_message(gmail_service, "me", message):
                        df.loc[index, "Follow-up 3 Date"] = today.strftime("%Y-%m-%d")
                        log_messages.append(f"--> Follow-up #3 sent successfully.")
                        time.sleep(10)
                    else:
                        log_messages.append(f"--> FAILED to send Follow-up #3.")
                continue

    return df, "\n".join(log_messages)