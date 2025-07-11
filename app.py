import gradio as gr
import pandas as pd
from datetime import datetime
import os
import time
import json
import logging
import logging.handlers

# --- FIX: Correctly import all necessary functions ---
import config
from src.tavily_search import search_company_background
from src.email_generator import generate_fresher_email, track_email_performance, load_resume_text, analyze_and_choose_resume # Import load_resume_text and analyze_and_choose_resume
from src.gmail_api import get_gmail_service, create_message_with_attachment, send_message, clean_email_address
from src.google_sheets_api import get_sheets_service, write_to_google_sheet
from src.email_automation import check_and_follow_up



# --- Global Cache for Resumes ---
RESUME_CACHE = {}
GMAIL_SERVICE = None
SHEETS_SERVICE = None
STOP_BOT_FLAG = False # Global flag to stop the bot



# --- FIX: Define a strict schema to prevent column creep errors permanently ---
EXPECTED_COLUMNS = {
    "Company": str,
    "Recipient Name": str,
    "Recipient Email": str,
    "Title": str,
    # --- NEW COLUMNS ---
    "Referral Name": str,  # To store the name of the person referring you
    "Referral Company": str, # To store their company
    "Chosen Template": str, # To log the exact template used (e.g., "value_proposition")
    "Template Category": str, # To log the category (e.g., "Value-First")
    # --- END NEW COLUMNS ---
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
        df = pd.DataFrame(columns=list(EXPECTED_COLUMNS.keys())).astype(EXPECTED_COLUMNS)
    return df

def save_data():
    """Saves the global DataFrame to CSV, enforcing the schema and never saving the index."""
    global df
    # Ensure the dataframe always conforms to the schema before saving
    final_df = df.reindex(columns=EXPECTED_COLUMNS)
    final_df.to_csv(config.CSV_FILE, index=False, encoding='utf-8')

def sync_to_google_sheets_gradio():
    """Syncs the current DataFrame to the configured Google Sheet."""
    global df, SHEETS_SERVICE
    logging.info("Sync to Google Sheets initiated.")
    if SHEETS_SERVICE:
        try:
            write_to_google_sheet(SHEETS_SERVICE, config.SPREADSHEET_ID, config.RANGE_NAME, df)
            logging.info("Data synced to Google Sheets successfully!")
            return "Data synced to Google Sheets successfully!"
        except Exception as e:
            logging.error(f"Error syncing to Google Sheets: {e}")
            return f"Error syncing to Google Sheets: {e}"
    else:
        logging.warning("Google Sheets service not available. Sync skipped.")
        return "Google Sheets service not available. Sync skipped."


def start_outreach(input_csv_file, manual_resume_override, email_send_count):
    """Processes an uploaded CSV, uses AI to analyze, and starts the outreach process."""
    global df, GMAIL_SERVICE
    
    logging.info("Start Outreach button clicked.")
    
    if input_csv_file is not None:
        try:
            new_contacts_df = pd.read_csv(input_csv_file.name, encoding='utf-8')
            
            # Standardize column names
            rename_map = {
                "Name": "Recipient Name",
                "Email": "Recipient Email",
                "Referral_Name": "Referral Name",
                "Referral": "Referral Name"
            }
            new_contacts_df = new_contacts_df.rename(columns=lambda c: rename_map.get(c, c))
            
            new_contacts_df["Recipient Email"] = new_contacts_df["Recipient Email"].astype(str).apply(clean_email_address)
            
            # Create a master list of known emails
            known_emails = df["Recipient Email"].tolist()
            
            # Filter out contacts that are already in the master list
            genuinely_new_contacts_df = new_contacts_df[~new_contacts_df["Recipient Email"].isin(known_emails)].copy()
            
            if genuinely_new_contacts_df.empty:
                logging.info("No new contacts found in the uploaded CSV. All contacts already exist in the system.")
                return df, "No new contacts found in the uploaded CSV. All contacts already exist in the system."
            
            # **FIX: Only take the number of contacts we plan to send emails to**
            contacts_to_process = genuinely_new_contacts_df.head(email_send_count).copy()
            
            logging.info(f"Selected {len(contacts_to_process)} contacts for processing (from {len(genuinely_new_contacts_df)} available new contacts).")
            
            # Set initial status for contacts we're about to process
            contacts_to_process["Email Status"] = "Pending"
            
            # Fill any missing columns with empty strings to conform to schema
            for col in ["Referral Name", "Referral Company", "Chosen Template", "Template Category"]:
                if col not in contacts_to_process.columns:
                    contacts_to_process[col] = ""
            
            # **FIX: Only add contacts that we're actually processing**
            df = pd.concat([df, contacts_to_process], ignore_index=True)
            df = df.reindex(columns=list(EXPECTED_COLUMNS.keys())).astype(EXPECTED_COLUMNS)
            
            save_data()
            
            logging.info(f"Added {len(contacts_to_process)} contacts to process. {len(genuinely_new_contacts_df) - len(contacts_to_process)} contacts remain unprocessed.")
            
        except Exception as e:
            logging.error(f"Error processing uploaded CSV file for {input_csv_file.name}: {e}")
            return df, f"Error processing uploaded CSV file for {input_csv_file.name}: {e}"
    
    if not GMAIL_SERVICE:
        logging.warning("Gmail service not available. Cannot proceed with outreach.")
        return df, "Gmail service not available. Cannot proceed with outreach."
    
    sent_count = 0
    
    # Process only pending contacts (which are now limited to email_send_count)
    for index, row in df.iterrows():
        if STOP_BOT_FLAG:
            logging.info("Bot stopped by user.")
            return df, "Outreach stopped by user."
        
        if row["Email Status"] == "Pending":
            recipient_name = row["Recipient Name"]
            recipient_email = row["Recipient Email"]
            company_name = row["Company"]
            recruiter_title = row.get("Title", "")
            
            logging.info(f"--- Processing: {recipient_name} at {company_name} ---")
            
            # Research company
            logging.info("1. Researching company with Tavily...")
            company_info = search_company_background(company_name)
            df.loc[index, 'Company Info'] = json.dumps(company_info)
            
            if company_info:
                logging.info("-> Research complete.")
                
                # AI decides resume type
                final_resume_type = analyze_and_choose_resume(company_info, recruiter_title)
                resume_text = RESUME_CACHE.get(final_resume_type)
                
                if not resume_text:
                    logging.warning(f"-> Resume text for {final_resume_type} not found in cache. Skipping.")
                    continue
                
                # Generate email
                logging.info("2. Generating personalized email with AI...")
                email_generation_result = generate_fresher_email(
                    tavily_results=company_info,
                    recipient_name=recipient_name,
                    recipient_title=recruiter_title,
                    company_name=company_name,
                    role_type=final_resume_type,
                    resume_text=resume_text,
                    referral_name=row.get("Referral Name"),
                    referral_company=row.get("Referral Company")
                )
                
                if "error" in email_generation_result:
                    logging.error(f"-> Email generation failed: {email_generation_result['error']}. Skipping.")
                    continue
                
                # Extract email content
                email_subject = email_generation_result["email_subject"]
                email_body = email_generation_result["email_content"]
                should_attach = email_generation_result.get("should_attach_resume", False)
                safety_check_result = email_generation_result["safety_check_result"]
                chosen_template_name = email_generation_result["template_used"]
                
                # Track email performance
                track_email_performance(
                    template_name=chosen_template_name,
                    company_name=company_name,
                    response_received=False,
                    response_type=None
                )
                
                if safety_check_result == "APPROVE":
                    resume_path = config.AI_ML_RESUME if final_resume_type == "AI/ML" else config.FULLSTACK_RESUME
                    
                    # Create and send message
                    message = create_message_with_attachment(
                        config.SENDER_EMAIL,
                        recipient_email,
                        email_subject,
                        email_body,
                        file=resume_path if should_attach else None
                    )
                    
                    if send_message(GMAIL_SERVICE, "me", message, recipient_email):
                        df.loc[index, "Email Status"] = "Sent"
                        df.loc[index, "Sent Date"] = datetime.now().strftime("%Y-%m-%d")
                        df.loc[index, "Resume Type"] = final_resume_type
                        df.loc[index, "Chosen Template"] = chosen_template_name
                        df.loc[index, "Template Category"] = email_generation_result.get("template_category", "")
                        
                        logging.info(f"--> Email sent successfully to {recipient_email}. Resume attached: {should_attach}")
                        save_data()
                        time.sleep(15)
                        sent_count += 1
                    else:
                        logging.error(f"--> FAILED to send email to {recipient_email}.")
                        df.loc[index, "Email Status"] = "Failed"
                        save_data()
                else:
                    df.loc[index, "Email Status"] = "Pending Review"
                    df.loc[index, "Generated Subject"] = email_subject
                    df.loc[index, "Generated Body"] = email_body
                    logging.warning(f"[FLAGGED FOR REVIEW]: Email for {company_name} has been flagged and requires manual review.")
                    save_data()
            else:
                logging.warning(f"--> Failed to get company info from Tavily. Skipping.")
                df.loc[index, "Email Status"] = "Failed - No Company Info"
                save_data()
    
    logging.info(f"\n--- Outreach complete. Processed {sent_count} emails. ---")
    return df, f"Outreach complete. Processed {sent_count} emails out of {len(contacts_to_process)} loaded contacts."

def process_next_batch(email_send_count):
    """Processes the next batch of contacts from the uploaded CSV file."""
    global df
    
    logging.info("Processing next batch of contacts.")
    
    # Check if there are any contacts with status "Not Processed" (we'll need to track this)
    # For now, we'll return a message asking to upload a new CSV
    
    return df, f"To process more contacts, please upload a new CSV file with the remaining contacts you want to process."


def _check_and_follow_up_wrapper():
    """Wrapper function to integrate follow-up logic with the global df."""
    global df, RESUME_CACHE, GMAIL_SERVICE, STOP_BOT_FLAG
    if STOP_BOT_FLAG:
        logging.info("Bot stopped by user. Not performing follow-ups.")
        return df, "Follow-up check stopped by user."
    logging.info("Check Replies & Send Follow-ups initiated.")
    updated_df, log_messages = check_and_follow_up(GMAIL_SERVICE, df, RESUME_CACHE, STOP_BOT_FLAG)
    df = updated_df
    save_data()
    logging.info("Check Replies & Send Follow-ups complete.")
    return df, log_messages

def get_pending_review_emails():
    """Filters the global DataFrame to show only emails pending review."""
    global df
    return df[df["Email Status"] == "Pending Review"]

def display_for_review(pending_df, evt: gr.SelectData):
    """Displays the selected email for review and editing."""
    global df
    if evt.index is None:
        logging.warning("No row selected for review.")
        return "", "", get_pending_review_emails(), "No row selected.", None
    
    selected_row_index = evt.index[0] # Get the actual index from the original df
    
    if selected_row_index >= len(pending_df):
        logging.error("Invalid row selected for review.")
        return "", "", get_pending_review_emails(), "Invalid row selected.", None
        
    original_df_index = pending_df.iloc[selected_row_index].name

    subject = df.loc[original_df_index, "Generated Subject"]
    body = df.loc[original_df_index, "Generated Body"]
    company = df.loc[original_df_index, "Company"]
    recipient = df.loc[original_df_index, "Recipient Name"]
    
    logging.info(f"Loaded email for {recipient} at {company} (Index: {original_df_index}) for manual review.")
    return subject, body, get_pending_review_emails(), f"Loaded email for {recipient} at {company} (Index: {original_df_index})", original_df_index

def manually_send_email(selected_row_index_str, subject, body):
    """Sends the manually approved email."""
    global df, GMAIL_SERVICE
    logging.info("Manually send email initiated.")
    
    if not selected_row_index_str:
        logging.warning("No email selected for manual sending.")
        return get_pending_review_emails(), "", "", "Please select an email to send."

    try:
        # Convert the string index back to integer
        original_df_index = int(selected_row_index_str)

        row = df.loc[original_df_index]
        recipient_email = row["Recipient Email"]
        final_resume_type = row["Resume Type"]
        company_name = row["Company"]

        if not GMAIL_SERVICE:
            logging.error("Gmail service not available. Cannot send email manually.")
            return get_pending_review_emails(), "", "", "Gmail service not available. Cannot send email."

        resume_path = config.AI_ML_RESUME if final_resume_type == "AI/ML" else config.FULLSTACK_RESUME
        if not os.path.exists(resume_path):
            logging.error(f"Resume not found at {resume_path}. Cannot send email manually.")
            return get_pending_review_emails(), "", "", f"Resume not found at {resume_path}. Cannot send email."

        message = create_message_with_attachment(config.SENDER_EMAIL, recipient_email, subject, body, resume_path)
        try:
            if send_message(GMAIL_SERVICE, "me", message, recipient_email):
                df.loc[original_df_index, "Email Status"] = "Sent (Manual)"
                df.loc[original_df_index, "Sent Date"] = datetime.now().strftime("%Y-%m-%d")
                df.loc[original_df_index, "Generated Subject"] = ""
                df.loc[original_df_index, "Generated Body"] = ""
                save_data()
                logging.info(f"Successfully sent manual email to {recipient_email} for {company_name}.")
                return get_pending_review_emails(), "", "", f"Successfully sent manual email to {recipient_email} for {company_name}."
            else:
                logging.error(f"FAILED to send manual email to {recipient_email} for {company_name}. send_message returned None.")
                return get_pending_review_emails(), "", "", f"FAILED to send manual email to {recipient_email} for {company_name}."
        except Exception as send_e:
            logging.error(f"Exception during send_message for {recipient_email}: {send_e}")
            return get_pending_review_emails(), "", "", f"Exception during send_message for {recipient_email}: {send_e}"

    except Exception as e:
        logging.error(f"General error in manually_send_email: {e}")
        return get_pending_review_emails(), "", "", f"General error in manually_send_email: {e}"

def discard_email(selected_row_index_str):
    """Discards the flagged email."""
    global df
    logging.info("Discard email initiated.")

    if not selected_row_index_str:
        logging.warning("No email selected for discarding.")
        return get_pending_review_emails(), "", "", "Please select an email to discard."

    try:
        original_df_index = int(selected_row_index_str)

        df.loc[original_df_index, "Email Status"] = "Discarded"
        df.loc[original_df_index, "Generated Subject"] = ""
        df.loc[original_df_index, "Generated Body"] = ""
        save_data()
        logging.info(f"Email for {df.loc[original_df_index, 'Company']} discarded.")
        return get_pending_review_emails(), "", "", f"Email for {df.loc[original_df_index, 'Company']} discarded."
    except Exception as e:
        logging.error(f"Error discarding email: {e}")
        return get_pending_review_emails(), "", "", f"Error discarding email: {e}"

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
                email_send_count = gr.Number(label="Number of emails to send", value=10, minimum=1, step=1)
                start_button = gr.Button("3. Load Contacts & Start AI-Powered Outreach", variant="primary")
                stop_button = gr.Button("STOP Outreach", variant="stop")
        
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
        inputs=[input_csv, manual_resume_override_radio, email_send_count],
        outputs=[output_dataframe, outreach_log]
    ).then(
        load_data, outputs=[monitoring_dataframe] # Update the other tab's view
    ).then(
        get_pending_review_emails, outputs=[review_dataframe] # Update the review tab's view
    )

    def stop_bot():
        global STOP_BOT_FLAG
        STOP_BOT_FLAG = True
        logging.info("STOP_BOT_FLAG set to True. Bot will attempt to stop.")
        return "Bot stop requested. Please wait for current operation to finish."

    stop_button.click(
        stop_bot,
        inputs=[],
        outputs=[outreach_log]
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
        global RESUME_CACHE, GMAIL_SERVICE, SHEETS_SERVICE

        # Configure logging
        log_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(funcName)s - %(message)s')
        
        # Console Handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(log_formatter)
        
        # File Handler (Rotating)
        log_file = "bot_activity.log"
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=1024 * 1024 * 5,  # 5 MB
            backupCount=5
        )
        file_handler.setFormatter(log_formatter)
        
        # Get root logger and add handlers
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.INFO) # Set default logging level
        root_logger.addHandler(console_handler)
        root_logger.addHandler(file_handler)

        logging.info("Application startup: Pre-loading data and checking services.")

        logging.info("Pre-loading resume data...")
        try:
            RESUME_CACHE["AI/ML"] = load_resume_text(config.AI_ML_RESUME)
            RESUME_CACHE["Fullstack"] = load_resume_text(config.FULLSTACK_RESUME)
            logging.info("Resume data pre-loaded successfully.")
        except Exception as e:
            logging.error(f"Error pre-loading resume data: {e}")

        # Attempt to get Gmail service to trigger authentication if needed before server starts
        logging.info("Checking Google services authentication...")
        try:
            GMAIL_SERVICE = get_gmail_service()
            SHEETS_SERVICE = get_sheets_service()
            logging.info("Google services authentication successful.")
        except Exception as e:
            logging.error(f"Could not complete Google services authentication on startup: {e}")
            logging.warning("The app will continue, but email and sheets functions will fail until auth is resolved.")
        
        # Also load initial dataframe data for the UI
        initial_df = load_data()
        return initial_df, initial_df, initial_df[initial_df["Email Status"] == "Pending Review"]
    demo.load(_preload_data_on_startup, outputs=[output_dataframe, monitoring_dataframe, review_dataframe])

demo.launch()