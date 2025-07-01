# AI-Powered Cold Emailing Bot

This project provides an automated solution for sending personalized cold emails for job applications, particularly for "fresher" roles. It leverages Artificial Intelligence (AI) to research companies, generate tailored email content, and manage the outreach process, including follow-ups. The bot offers both a user-friendly Gradio web interface and a command-line interface (CLI) for operation.

## Features

*   **Automated Company Research:** Utilizes Tavily Search to gather comprehensive background information on target companies.
*   **AI-Powered Email Generation:** Generates highly personalized cold emails using the Gemini API, adapting content based on company insights and recipient details.
*   **Intelligent Resume Selection:** Automatically analyzes company information and job titles to recommend and attach the most relevant resume (e.g., AI/ML or Fullstack).
*   **Gmail Integration:** Sends emails directly through the Gmail API, supporting attachments.
*   **Automated Follow-ups:** Checks for email replies and sends timely follow-up emails to maximize engagement.
*   **Google Sheets Synchronization:** Keeps track of all outreach activities, email statuses, and responses by syncing data with a Google Sheet.
*   **CSV Import:** Easily import recruiter contact lists from CSV files.
*   **Manual Review & Approval:** Provides a mechanism to review and manually approve or discard AI-generated emails before sending, ensuring quality control.
*   **Comprehensive Logging:** Logs all bot activities for monitoring and debugging.

## Project Structure

```
.
├── .github/                 # GitHub Actions workflows (e.g., CI/CD)
├── data/                    # Stores CSV data for contacts and potentially other data files
│   └── Copy of hr_emails - Sheet1.csv # Example HR email list
├── resumes/                 # Stores different versions of your resume (e.g., AI/ML, Fullstack)
│   ├── Resume_Ashish.pdf    # Example AI/ML resume
│   └── Ashish_Resume.pdf    # Example Fullstack resume
├── src/                     # Core source code modules
│   ├── __init__.py
│   ├── email_automation.py  # Logic for checking replies and sending follow-ups
│   ├── email_generator.py   # AI-powered email content generation and resume analysis
│   ├── gmail_api.py         # Functions for interacting with the Gmail API
│   ├── google_sheets_api.py # Functions for interacting with the Google Sheets API
│   ├── tavily_search.py     # Functions for company research using Tavily
│   ├── templates.py         # Email templates used by the generator
│   └── web_scraper.py       # (Potentially for future use or specific data extraction)
├── .gitignore               # Specifies intentionally untracked files to ignore
├── app.py                   # The Gradio web application interface
├── config.py                # Centralized configuration settings and API keys
├── main.py                  # Command-line interface (CLI) for running the bot
├── requirements.txt         # Python dependencies required for the project
└── README.md                # This documentation file
```

## How It Works (High-Level Flow)

1.  **Configuration:** API keys for Google (Gmail, Sheets), Gemini, and Tavily are loaded from environment variables (`.env` file) via `config.py`. Resume paths and personal details are also configured here.
2.  **Data Loading:** The bot loads existing contact data from `data/emails.csv` or initializes a new DataFrame.
3.  **Contact Import (Gradio):** Users can upload a CSV file containing recruiter contacts via the Gradio interface. New contacts are added to the main dataset.
4.  **Company Research:** For each "Pending" contact, `tavily_search.py` is used to research the target company, gathering relevant information.
5.  **Email Generation:** `email_generator.py` utilizes the Gemini API to craft a personalized cold email. It intelligently selects the most appropriate resume from the `resumes/` directory based on the company and role.
6.  **Safety Check & Review:** AI-generated emails undergo a safety check. If flagged, they are sent to a "Pending Review" queue in the Gradio UI for manual approval or discard.
7.  **Email Sending:** Approved emails are sent via `gmail_api.py` with the selected resume attached. The email status is updated to "Sent".
8.  **Follow-up Automation:** `email_automation.py` periodically checks for replies to sent emails. If no reply is received after a configured period, automated follow-up emails are sent.
9.  **Google Sheets Sync:** All updated contact data, including email statuses and response statuses, is synchronized with a designated Google Sheet via `google_sheets_api.py`.

## Setup and Installation

### Prerequisites

*   Python 3.8+
*   Google Cloud Project with Gmail API and Google Sheets API enabled.
*   A Google account for authentication.
*   Gemini API Key.
*   Tavily API Key.

### 1. Clone the Repository

```bash
git clone https://github.com/your-username/email_bot.git # Replace with your actual repo URL
cd email_bot
```

### 2. Create a Virtual Environment (Recommended)

```bash
python -m venv venv
source venv/bin/activate # On Windows: `venv\Scripts\activate`
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Google API Credentials Setup

1.  Go to the [Google Cloud Console](https://console.cloud.google.com/).
2.  Create a new project or select an existing one.
3.  Enable the **Gmail API** and **Google Sheets API** for your project.
4.  Go to "APIs & Services" > "Credentials".
5.  Create an **OAuth 2.0 Client ID** for a "Desktop app".
6.  Download the `credentials.json` file and place it in the root directory of this project (where `app.py` is located). Rename it to `credentials.json` if it has a different name.
    *   The first time you run the bot, a browser window will open asking you to authenticate with your Google account. Follow the prompts to grant necessary permissions.

### 5. Obtain API Keys

*   **Gemini API Key:** Get your API key from [Google AI Studio](https://aistudio.google.com/app/apikey).
*   **Tavily API Key:** Sign up and get your API key from [Tavily AI](https://tavily.com/).

### 6. Configure Environment Variables

Create a `.env` file in the root directory of the project and add the following:

```dotenv
# Google Sheet Configuration
SPREADSHEET_ID="YOUR_GOOGLE_SHEET_ID" # Find this in the URL of your Google Sheet
RANGE_NAME="Sheet1!A:J" # Adjust if your sheet structure is different

# Email Configuration
SENDER_EMAIL="your.email@example.com" # The email address you will send from

# AI API Keys
GEMINI_API_KEY="YOUR_GEMINI_API_KEY"
TAVILY_API_KEY="YOUR_TAVILY_API_KEY"

# Personal Details for Email Templates (Update with your own information)
YOUR_NAME="Your Name"
YOUR_DEGREE="Your Degree"
YOUR_KEY_SKILLS="Your Key Skills (e.g., Python, ML, Web Dev)"
YOUR_PROJECT_EXPERIENCE="A brief description of a key project experience"
```

**Important:** Replace the placeholder values with your actual IDs, keys, and personal information.

### 7. Prepare Resumes

Place your resume PDF files in the `resumes/` directory. Update `config.py` if your resume filenames are different from `Resume_Ashish.pdf` (for AI/ML) and `Ashish_Resume.pdf` (for Fullstack).

```python
# config.py
# ...
AI_ML_RESUME = "resumes/Your_AI_ML_Resume.pdf"
FULLSTACK_RESUME = "resumes/Your_Fullstack_Resume.pdf"
# ...
```

### 8. Prepare Data CSV

The bot expects a CSV file at `data/emails.csv` to store contact information. You can start with an empty CSV or use the provided example structure. The CSV should have at least `Company`, `Recipient Name`, and `Recipient Email` columns.

## Usage

### Running the Gradio Web Interface (Recommended)

This is the primary way to interact with the bot.

```bash
python app.py
```

After running, open your web browser and navigate to the URL provided by Gradio (usually `http://127.0.0.1:7860`).

**Gradio Interface Walkthrough:**

1.  **Outreach Tab:**
    *   **Manual Resume Override (Optional):** Choose a specific resume type if you want to force its use for a batch, otherwise, let the AI decide.
    *   **Upload Recruiter CSV:** Upload your CSV file containing recruiter contacts.
    *   **Load Contacts & Start AI-Powered Outreach:** Click this button to initiate the company research, email generation, and sending process.
    *   **Outreach Progress:** Monitor the status of emails in the displayed DataFrame.
    *   **Outreach Log:** View real-time logs of the bot's activities.

2.  **Monitoring & Sync Tab:**
    *   **Check Replies & Send Follow-ups:** Manually trigger the process to check for new email replies and send automated follow-ups.
    *   **Sync with Google Sheets:** Manually synchronize the current data with your configured Google Sheet.
    *   **Monitoring Log:** View logs related to monitoring and syncing.

3.  **Review & Manual Send Tab:**
    *   **Emails Flagged for Review:** This table displays emails that the AI flagged for manual review (e.g., due to safety concerns).
    *   **Review and Edit Email:** Select a row from the table to load the AI-generated subject and body. You can edit them here.
    *   **Approve & Send Manually:** Send the email after reviewing/editing.
    *   **Discard Email:** Discard the email if you don't want to send it.

### Running the CLI Interface (Alternative)

The `main.py` script provides a command-line way to run the core logic. This is useful for scheduled tasks or if you prefer a non-GUI approach.

```bash
python main.py
```

This script will:
1.  Load existing data from `data/emails.csv`.
2.  Check for replies to previously sent emails.
3.  Process any "Pending" emails (research, generate, send).
4.  Run the follow-up logic.
5.  Sync all data to Google Sheets.

## Technologies Used

*   **Python 3**
*   **Gradio:** For creating the interactive web UI.
*   **Pandas:** For data manipulation and management of contact information.
*   **Google Generative AI (Gemini API):** For AI-powered email content generation.
*   **Tavily API:** For real-time company background research.
*   **Google API Python Client:** For interacting with Gmail and Google Sheets.
*   **`python-dotenv`:** For managing environment variables.
*   **`pdfplumber`:** For extracting text from PDF resumes.

## Contributing

Feel free to fork the repository, open issues, and submit pull requests.

## License

This project is open-source and available under the [MIT License](LICENSE).