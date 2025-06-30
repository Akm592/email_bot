import gradio as gr
import pandas as pd
from datetime import datetime
import os
import time
import json

# --- FIX: Correctly import all necessary functions ---
import config
from src.tavily_search import search_company_background
from src.email_generator import generate_fresher_email, track_email_performance, validate_email_quality, load_resume_text, analyze_and_choose_resume # Import load_resume_text and analyze_and_choose_resume
from src.gmail_api import get_gmail_service, create_message_with_attachment, send_message, clean_email_address
from src.google_sheets_api import get_sheets_service, write_to_google_sheet
from src.email_automation import check_and_follow_up



# --- Global Cache for Resumes ---
RESUME_CACHE = {}



# --- FIX: Define a strict schema to prevent column creep errors permanently ---
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
    "Follow-up 3 Date": str,
    "Response Status": str,
    "Company Info": str,
    "Generated Subject": str,
    "Generated Body": str
}

# --- Global DataFrame ---
df = pd.DataFrame(columns=list(EXPECTED_COLUMNS.keys())).astype(EXPECTED_COLUMNS)

def load_data():
    """Loads data and enforces the expected schema, preventing corruption."""
    global df
    try:
        temp_df = pd.read_csv(config.CSV_FILE, encoding='utf-8')
        # Only keep columns that are expected. This throws away any junk 'Unnamed' columns.
        df = temp_df.reindex(columns=list(EXPECTED_COLUMNS.keys())).astype(EXPECTED_COLUMNS)
        df["Recipient Email"] = df["Recipient Email"].astype(str).apply(clean_email_address)
    except (FileNotFoundError, KeyError):
        df = pd.DataFrame(columns=EXPECTED_COLUMNS)
    return df

def save_data():
    """Saves the global DataFrame to CSV, enforcing the schema and never saving the index."""
    global df
    # Ensure the dataframe always conforms to the schema before saving
    final_df = df.reindex(columns=EXPECTED_COLUMNS)
    final_df.to_csv(config.CSV_FILE, index=False, encoding='utf-8')

def sync_to_google_sheets_gradio():
    """Syncs the current DataFrame to the configured Google Sheet."""
    global df
    log_messages = []
    sheets_service = get_sheets_service()
    if sheets_service:
        try:
            write_to_google_sheet(sheets_service, config.SPREADSHEET_ID, config.RANGE_NAME, df)
            log_messages.append("Data synced to Google Sheets successfully!")
        except Exception as e:
            log_messages.append(f"Error syncing to Google Sheets: {e}")
    else:
        log_messages.append("Failed to obtain Google Sheets service. Sync skipped.")
    return "\n".join(log_messages)

def start_outreach(input_csv_file, manual_resume_override):
    """Processes an uploaded CSV, uses AI to analyze, and starts the outreach process."""
    global df
    log_messages = []

    if input_csv_file is not None:
        try:
            new_contacts_df = pd.read_csv(input_csv_file.name, encoding='utf-8')
            new_contacts_df = new_contacts_df.rename(columns={"Name": "Recipient Name", "Email": "Recipient Email"})
            new_contacts_df["Recipient Email"] = new_contacts_df["Recipient Email"].astype(str).apply(clean_email_address)
            new_contacts_df["Email Status"] = "Pending"
            
            # Create a master list of known emails
            known_emails = df["Recipient Email"].tolist()

            # Filter out contacts that are already in the master list
            genuinely_new_contacts_df = new_contacts_df[~new_contacts_df["Recipient Email"].isin(known_emails)].copy()

            if genuinely_new_contacts_df.empty:
                log_messages.append("No new contacts found in the uploaded CSV. All contacts already exist in the system.")
                return df, "\n".join(log_messages)

            # Add only genuinely new contacts
            df = pd.concat([df, genuinely_new_contacts_df], ignore_index=True).astype(EXPECTED_COLUMNS)
            df.drop_duplicates(subset=["Recipient Email"], keep="last", inplace=True) # Ensure no duplicates after concat
            df = df.reindex(columns=list(EXPECTED_COLUMNS.keys())).astype(EXPECTED_COLUMNS) # Enforce schema
            save_data()
            log_messages.append(f"Loaded {len(genuinely_new_contacts_df)} new, unique contacts. Removed duplicates.")
        except Exception as e:
            log_messages.append(f"Error processing uploaded CSV: {e}")
            return df, "\n".join(log_messages)

    gmail_service = get_gmail_service()
    if not gmail_service:
        log_messages.append("Failed to obtain Gmail service. Cannot proceed with outreach.")
        return df, "\n".join(log_messages)

    for index, row in df.iterrows():
        if row["Email Status"] == "Pending":
            recipient_name = row["Recipient Name"]
            recipient_email = row["Recipient Email"]
            company_name = row["Company"]
            recruiter_title = row.get("Title", "")

            log_messages.append(f"--- Processing: {recipient_name} at {company_name} ---")
            
            log_messages.append("1. Researching company with Tavily...")
            company_info = search_company_background(company_name)
            df.loc[index, 'Company Info'] = json.dumps(company_info)

            if company_info:
                log_messages.append("-> Research complete.")

                # AI Decides which resume type to use
                final_resume_type = analyze_and_choose_resume(company_info, recruiter_title)
                # Instant Fetch: Retrieve the corresponding text instantly from the global cache
                resume_text = RESUME_CACHE.get(final_resume_type)

                if not resume_text:
                    log_messages.append(f"-> Resume text for {final_resume_type} not found in cache. Skipping.")
                    continue

                log_messages.append("2. Generating personalized email with AI...")
                email_generation_result = generate_fresher_email(
                    tavily_results=company_info,
                    recipient_name=recipient_name,
                    recipient_title=recruiter_title,
                    company_name=company_name,
                    role_type=final_resume_type, # Use the AI-chosen resume type
                    resume_text=resume_text # Pass the pre-loaded resume text
                )

                if "error" in email_generation_result:
                    log_messages.append(f"-> Email generation failed: {email_generation_result['error']}. Skipping.")
                    continue

                email_subject = email_generation_result["email_subject"]
                email_body = email_generation_result["email_content"]
                final_resume_type = email_generation_result["resume_choice"]
                chosen_template_name = email_generation_result["template_used"]
                safety_check_result = email_generation_result["safety_check_result"]

                log_messages.append(f"-> AI generated email using '{chosen_template_name}' template. Quality Score: {email_generation_result['quality_score']}")
                
                # Track email performance
                track_email_performance(
                    template_name=chosen_template_name,
                    company_name=company_name,
                    response_received=False, # Initial send, no response yet
                    response_type=None
                )
                
                if safety_check_result == "APPROVE":
                    resume_path = config.AI_ML_RESUME if final_resume_type == "AI/ML" else config.FULLSTACK_RESUME

                    if not os.path.exists(resume_path):
                        log_messages.append(f"-> Resume not found at {resume_path}. Skipping.")
                        continue

                    message = create_message_with_attachment(config.SENDER_EMAIL, recipient_email, email_subject, email_body, resume_path)
                    if send_message(gmail_service, "me", message):
                        df.loc[index, "Email Status"] = "Sent"
                        df.loc[index, "Sent Date"] = datetime.now().strftime("%Y-%m-%d")
                        df.loc[index, "Resume Type"] = final_resume_type
                        log_messages.append(f"--> Email sent successfully to {recipient_email}.")
                        save_data()
                        time.sleep(15) # Increased sleep time for more API calls
                    else:
                        log_messages.append(f"--> FAILED to send email to {recipient_email}.")
                else: # safety_check_result == "REJECT"
                    df.loc[index, "Email Status"] = "Pending Review"
                    df.loc[index, "Generated Subject"] = email_subject
                    df.loc[index, "Generated Body"] = email_body
                    log_messages.append(f"[FLAGGED FOR REVIEW]: Email for {company_name} has been flagged and requires manual review.")
                    save_data() # Save immediately after flagging
            else:
                log_messages.append(f"--> Failed to get company info from Tavily. Skipping.")

    save_data()
    log_messages.append("\n--- Outreach complete for all pending contacts. ---")
    return df, "\n".join(log_messages)

def _check_and_follow_up_wrapper():
    """Wrapper function to integrate follow-up logic with the global df."""
    global df, RESUME_CACHE
    updated_df, log_messages = check_and_follow_up(df, RESUME_CACHE)
    df = updated_df
    save_data()
    return df, log_messages

def get_pending_review_emails():
    """Filters the global DataFrame to show only emails pending review."""
    global df
    return df[df["Email Status"] == "Pending Review"]

def display_for_review(evt: gr.SelectData):
    """Displays the selected email for review and editing."""
    global df
    if evt.index is None:
        return "", "", get_pending_review_emails(), "No row selected.", None
    
    selected_row_index = evt.index[0] # Get the actual index from the original df
    
    pending_df = get_pending_review_emails()
    if selected_row_index >= len(pending_df):
        return "", "", get_pending_review_emails(), "Invalid row selected.", None
        
    original_df_index = pending_df.iloc[selected_row_index].name

    subject = df.loc[original_df_index, "Generated Subject"]
    body = df.loc[original_df_index, "Generated Body"]
    company = df.loc[original_df_index, "Company"]
    recipient = df.loc[original_df_index, "Recipient Name"]
    
    log_message = f"Loaded email for {recipient} at {company} (Index: {original_df_index})"
    return subject, body, get_pending_review_emails(), log_message, original_df_index

def manually_send_email(selected_row_index_str, subject, body):
    """Sends the manually approved email."""
    global df
    log_messages = []
    
    if not selected_row_index_str:
        return get_pending_review_emails(), "", "", "Please select an email to send."

    try:
        # Convert the string index back to integer
        selected_row_index = int(selected_row_index_str)
        
        pending_df = get_pending_review_emails()
        if selected_row_index >= len(pending_df):
            return get_pending_review_emails(), "", "", "Invalid row selected for sending."
        original_df_index = pending_df.iloc[selected_row_index].name

        row = df.loc[original_df_index]
        recipient_email = row["Recipient Email"]
        final_resume_type = row["Resume Type"]
        company_name = row["Company"]

        gmail_service = get_gmail_service()
        if not gmail_service:
            log_messages.append("Failed to obtain Gmail service. Cannot send email.")
            return get_pending_review_emails(), "", "", "\n".join(log_messages)

        resume_path = config.AI_ML_RESUME if final_resume_type == "AI/ML" else config.FULLSTACK_RESUME
        if not os.path.exists(resume_path):
            log_messages.append(f"Resume not found at {resume_path}. Cannot send email.")
            return get_pending_review_emails(), "", "", "\n".join(log_messages)

        message = create_message_with_attachment(config.SENDER_EMAIL, recipient_email, subject, body, resume_path)
        if send_message(gmail_service, "me", message):
            df.loc[original_df_index, "Email Status"] = "Sent (Manual)"
            df.loc[original_df_index, "Sent Date"] = datetime.now().strftime("%Y-%m-%d")
            df.loc[original_df_index, "Generated Subject"] = ""
            df.loc[original_df_index, "Generated Body"] = ""
            save_data()
            log_messages.append(f"Successfully sent manual email to {recipient_email} for {company_name}.")
        else:
            log_messages.append(f"FAILED to send manual email to {recipient_email} for {company_name}.")

    except Exception as e:
        log_messages.append(f"Error sending manual email: {e}")
    
    return get_pending_review_emails(), "", "", "\n".join(log_messages)

def discard_email(selected_row_index_str):
    """Discards the flagged email."""
    global df
    log_messages = []

    if not selected_row_index_str:
        return get_pending_review_emails(), "", "", "Please select an email to discard."

    try:
        selected_row_index = int(selected_row_index_str)
        
        pending_df = get_pending_review_emails()
        if selected_row_index >= len(pending_df):
            return get_pending_review_emails(), "", "", "Invalid row selected for discarding."
        original_df_index = pending_df.iloc[selected_row_index].name

        df.loc[original_df_index, "Email Status"] = "Discarded"
        df.loc[original_df_index, "Generated Subject"] = ""
        df.loc[original_df_index, "Generated Body"] = ""
        save_data()
        log_messages.append(f"Email for {df.loc[original_df_index, 'Company']} discarded.")
    except Exception as e:
        log_messages.append(f"Error discarding email: {e}")
    
    return get_pending_review_emails(), "", "", "\n".join(log_messages)

# --- Gradio UI Definition ---
with gr.Blocks(theme=gr.themes.Soft()) as demo:
    gr.Markdown("# Cold Emailing Bot Dashboard")

    with gr.Tab("Outreach"):
        with gr.Row():
            with gr.Column(scale=1):
                # --- FIX: Changed name for clarity ---
                manual_resume_override_radio = gr.Radio(
                    ["", "AI/ML", "Fullstack"], # Empty string means "Let AI Decide"
                    label="1. Manual Resume Override (Optional)",
                    value="",
                    info="Leave blank to let the AI decide. Select a type to force its use for this batch."
                )
                input_csv = gr.File(label="2. Upload Recruiter CSV")
            with gr.Column(scale=2, min_width=100):
                start_button = gr.Button("3. Load Contacts & Start AI-Powered Outreach", variant="primary")
        
        gr.Markdown("### Outreach Progress")
        output_dataframe = gr.DataFrame(value=load_data(), label="Email Status", interactive=True)
        outreach_log = gr.Textbox(label="Outreach Log", lines=10, interactive=False)

    with gr.Tab("Monitoring & Sync"):
        with gr.Row():
            check_followup_button = gr.Button("Check Replies & Send Follow-ups")
            sync_sheets_button = gr.Button("Sync with Google Sheets")
        monitoring_dataframe = gr.DataFrame(value=load_data(), label="Email Status", interactive=True)
        monitoring_log = gr.Textbox(label="Monitoring Log", lines=10, interactive=False)

    with gr.Tab("Review & Manual Send"):
        gr.Markdown("### Emails Flagged for Review")
        review_dataframe = gr.DataFrame(value=pd.DataFrame(columns=list(EXPECTED_COLUMNS.keys())), label="Emails Pending Review", interactive=True)
        
        with gr.Column():
            gr.Markdown("### Review and Edit Email")
            review_subject = gr.Textbox(label="Email Subject", interactive=True)
            review_body = gr.Textbox(label="Email Body", interactive=True, lines=20)
            
            with gr.Row():
                approve_send_button = gr.Button("Approve & Send Manually", variant="primary")
                discard_button = gr.Button("Discard Email")
            
            review_log = gr.Textbox(label="Review Log", lines=5, interactive=False)
            selected_row_original_index_state = gr.State(value=None)

    # --- Button Click Handlers ---
    start_button.click(
        start_outreach,
        inputs=[input_csv, manual_resume_override_radio],
        outputs=[output_dataframe, outreach_log]
    ).then(
        load_data, outputs=[monitoring_dataframe] # Update the other tab's view
    ).then(
        get_pending_review_emails, outputs=[review_dataframe] # Update the review tab's view
    )

    check_followup_button.click(
        _check_and_follow_up_wrapper,
        inputs=[],
        outputs=[monitoring_dataframe, monitoring_log]
    ).then(
        load_data, outputs=[output_dataframe] # Update the other tab's view
    ).then(
        get_pending_review_emails, outputs=[review_dataframe] # Update the review tab's view
    )

    sync_sheets_button.click(
        sync_to_google_sheets_gradio,
        inputs=[],
        outputs=[monitoring_log]
    ).then(
        get_pending_review_emails, outputs=[review_dataframe] # Update the review tab's view
    )

    # Review & Manual Send Tab Handlers
    review_dataframe.select(
        display_for_review,
        inputs=[review_dataframe],
        outputs=[review_subject, review_body, review_dataframe, review_log, selected_row_original_index_state]
    )

    approve_send_button.click(
        manually_send_email,
        inputs=[selected_row_original_index_state, review_subject, review_body],
        outputs=[review_dataframe, review_subject, review_body, review_log]
    )

    discard_button.click(
        discard_email,
        inputs=[selected_row_original_index_state],
        outputs=[review_dataframe, review_subject, review_body, review_log]
    )

    # --- FIX: Correct way to load initial data for multiple dataframes ---
    def _preload_data_on_startup():
        global RESUME_CACHE
        print("Pre-loading resume data...")
        try:
            RESUME_CACHE["AI/ML"] = load_resume_text(config.AI_ML_RESUME)
            RESUME_CACHE["Fullstack"] = load_resume_text(config.FULLSTACK_RESUME)
            print("Resume data pre-loaded successfully.")
        except Exception as e:
            print(f"Error pre-loading resume data: {e}")
        
        # Also load initial dataframe data for the UI
        initial_df = load_data()
        return initial_df, initial_df, initial_df[initial_df["Email Status"] == "Pending Review"]
    demo.load(_preload_data_on_startup, outputs=[output_dataframe, monitoring_dataframe, review_dataframe])

demo.launch()