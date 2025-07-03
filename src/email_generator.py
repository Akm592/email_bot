# src/email_generator.py

import google.generativeai as genai
import pdfplumber
import json
from datetime import datetime
import config
from .templates import TEMPLATES
import logging
import pandas as pd

# Get logger for this module
logger = logging.getLogger(__name__)

MODEL_NAME = "gemini-2.0-flash-lite"
AI_ML_RESUME_PATH = config.AI_ML_RESUME
FULLSTACK_RESUME_PATH = config.FULLSTACK_RESUME
gem_key=config.GEMINI_API_KEY

try:
    genai.configure(api_key=gem_key)
except Exception as e:
    logger.error(f"Error configuring Gemini API: {e}")

def load_resume_text(resume_path: str) -> str:
    """Loads text from a PDF resume."""
    try:
        with pdfplumber.open(resume_path) as pdf:
            text = ""
            for page in pdf.pages:
                text += page.extract_text() or ""
            return text
    except Exception as e:
        logger.error(f"Error loading resume from {resume_path}: {e}")
        return ""

def analyze_and_choose_resume(tavily_results: dict, recruiter_title: str) -> str:
    """Uses Gemini to decide which resume to send based on structured Tavily results."""
    model = genai.GenerativeModel(MODEL_NAME)
    
    research_summary_for_prompt = json.dumps(tavily_results, indent=2)

    prompt = f'''
    You are an expert career advisor. Your task is to choose the best resume to send based on the following information.

    **Comprehensive Company Research (Structured JSON):**
    {research_summary_for_prompt}

    **Recruiter's Title:** "{recruiter_title}"

    Analyze the research, especially the `technicalProfile` and `hiringIntelligence` sections, and the recruiter's title. 
    Should I send my "AI/ML" resume or my "Fullstack" resume?

    Your entire response MUST be ONLY ONE of the following two options:
    - AI/ML
    - Fullstack
    '''
    try:
        response = model.generate_content(prompt)
        choice = response.text.strip()
        logger.info(f"AI chose resume type: {choice} for recruiter title: {recruiter_title}.")
        if choice in ["AI/ML", "Fullstack"]:
            return choice
        logger.warning(f"Unexpected resume choice from AI: {choice}. Defaulting to Fullstack.")
        return "Fullstack"
    except Exception as e:
        logger.error(f"Gemini error during resume analysis: {e}")
        return "Fullstack"

def determine_graduation_timeline() -> str:
    """Determine urgency based on current date and graduation timeline"""
    current_month = datetime.now().month
    if 4 <= current_month <= 6:
        return "May 2025"
    elif 10 <= current_month <= 12:
        return "December 2025"
    else:
        return "upcoming semester"

def extract_sender_details_from_resume(resume_text: str) -> dict:
    """Uses Gemini to extract key personal details from a resume text."""
    model = genai.GenerativeModel(MODEL_NAME)
    prompt = f'''
    From the following resume text, extract the candidate's degree, a concise list of their key technical skills,
    a summary of their most impressive project accomplishment, and their full name.

    Return this as a JSON object with the following keys:
    - degree: (e.g., "B.Tech in Information Technology")
    - key_skills: (comma-separated list, e.g., "Python, TensorFlow, PyTorch, RAG")
    - project_experience: (concise, one-sentence summary of the most impressive and quantifiable project)
    - name: (Full name of the candidate)

    Resume Text:
    {resume_text}

    Example JSON Output:
    {{
      "degree": "B.Tech in Information Technology",
      "key_skills": "Python, TensorFlow, PyTorch, RAG, CI/CD, React.js",
      "project_experience": "Developed an AI platform that enhanced data processing speed by 3.5x and significantly reduced search latency by 60%.",
      "name": "John Doe"
    }}
    '''
    try:
        response = model.generate_content(prompt)
        cleaned_response = response.text.strip().replace('```json', '').replace('```', '').strip()
        return json.loads(cleaned_response)
    except Exception as e:
        logger.error(f"Error extracting sender details from resume: {e}")
        return {"degree": "", "key_skills": "", "project_experience": "", "name": ""}

def choose_initial_template(tavily_results: dict, role_type: str, referral_name: str = None) -> tuple[str, str]:
    """
    Strategically selects the best initial outreach template based on structured data.
    """
    logger.info("Strategically choosing an email template...")

    if referral_name and pd.notna(referral_name) and referral_name.strip() != "":
        logger.info(f"Referral found: {referral_name}. Selecting 'referral_introduction' template.")
        return "initial", "referral_introduction"

    model = genai.GenerativeModel(MODEL_NAME)
    
    research_summary_for_prompt = json.dumps(tavily_results, indent=2)
    
    template_style_descriptions = '''
    - `value_proposition`, `problem_solution`: (Value-First) Leads with a specific, quantifiable achievement or solution. Ideal for data-driven companies.
    - `company_insight`, `industry_trend`: (Company Research) Shows you've done homework. Good for companies with recent news.
    - `fullstack_performance`, `ai_accuracy`, etc.: (Metric-Driven) A direct, concise summary of achievements. Perfect for busy recruiters.
    - `journey_narrative`, `challenge_overcome`: (Story-Based) Uses a narrative to showcase problem-solving. Good for companies with a strong culture.
    '''

    if role_type == "AI/ML":
        available_templates = ['value_proposition', 'problem_solution', 'company_insight', 'ai_accuracy', 'ai_efficiency', 'journey_narrative']
        role_context = "The user is applying for an AI/ML or Data Science role."
    else:
        available_templates = ['value_proposition', 'company_insight', 'fullstack_performance', 'fullstack_scalability', 'challenge_overcome']
        role_context = "The user is applying for a Fullstack or Frontend developer role."

    prompt = f'''
    You are an expert career strategist. Your task is to select the single best email template for a job-seeking fresher.

    **Context:** {role_context}
    
    **Comprehensive Company Research (Structured JSON):**
    {research_summary_for_prompt}

    **Available Template Styles and Their Purpose:**
    {template_style_descriptions}
    
    **List of Available Template Names for this Role:**
    {available_templates}

    Analyze all the information. Based on the `primaryInsights` and `actionableIntelligence` in the research, choose the most appropriate template NAME from the list provided. Your response MUST be ONLY the single template name you choose.
    '''
    try:
        response = model.generate_content(prompt)
        choice = response.text.strip()
        logger.info(f"AI chose template: {choice} for role type: {role_type}.")
        if choice in available_templates:
            return "initial", choice
        logger.warning(f"AI returned a template name not in the available list: '{choice}'. Defaulting.")
        return "initial", available_templates[0]
    except Exception as e:
        logger.error(f"Gemini error during template selection: {e}")
        return "initial", available_templates[0]

def populate_template(template_type: str, template_name: str, tavily_results: dict, recipient_data: dict, sender_data: dict, resume_text: str) -> tuple[str, str]:
    """
    Uses Gemini to fill in template placeholders using the new structured research data.
    """
    model = genai.GenerativeModel(MODEL_NAME)

    template_text = ""
    if template_type == 'initial':
        template_text = TEMPLATES.get(template_name, {}).get('content', f'Template {template_name} not found.')
    else:
        # In a real scenario, you might have FOLLOWUP_TEMPLATES
        logger.warning(f"Template type '{template_type}' not fully supported, using initial templates as fallback.")
        template_text = TEMPLATES.get(template_name, {}).get('content', f'Template {template_name} not found.')

    research_summary_for_prompt = json.dumps(tavily_results, indent=2)

    prompt = f'''
    You are a master copywriter and career strategist. Your task is to write a hyper-personalized cold email to a recruiter using a template and highly-structured research data.

    **1. My Personal Details (from my resume):**
    - My Name: {sender_data.get('name')}
    - My Degree: {sender_data.get('degree')}
    - My Key Skills: {sender_data.get('key_skills')}
    - My Most Impressive Project: {sender_data.get('project_experience')}
    - My Graduation Timeline: {determine_graduation_timeline()}

    **2. The Recipient:**
    - Company: {recipient_data.get('Company')}
    - Title: {recipient_data.get('Title')}

    **3. Comprehensive Company Research (Structured JSON):**
    Here is the detailed intelligence report you must use:
    ```json
    {research_summary_for_prompt}
    ```

    **4. The Email Template to Populate:**
    ---
    {template_text}
    ---

    **CRITICAL INSTRUCTIONS (Follow these meticulously):**

    1.  **Deconstruct the Research:** Deeply analyze the structured JSON.
        *   `primaryInsights`: These are your most important points. Your email MUST prioritize these.
        *   `personalizationHooks`: Use these to craft a compelling opening. For example, use `congratulateOn` for a recent achievement or `askAboutChallenge` to show you've thought about their problems.
        *   `actionableIntelligence`: This is critical for your call to action. If `hiringUrgency` is 'High', be direct. If a `referralPathway` exists (like alumni), mention it subtly.
        *   `secondaryContext`: Weave in details from here to show you've done thorough research beyond the headlines.

    2.  **Strategic Content Generation:**
        *   **Opening:** Start with a hook from `personalizationHooks`. It's more powerful than a generic opening.
        *   **Body:** Connect my skills and project experience directly to the `primaryInsights`. If an insight mentions they use 'PyTorch for NLP', and my skills include 'PyTorch', explicitly connect those dots.
        *   **Call to Action:** Frame your "ask" based on `actionableIntelligence`. If `hiringUrgency` is 'High', you might suggest a brief chat next week.

    3.  **Tone Adjustment:**
        *   Adjust tone based on `actionableIntelligence.hiringUrgency` and `secondaryContext.peopleAndCulture.missionAndValues`. If the company culture seems very formal, be more formal. If it's a startup, be more conversational.

    4.  **Placeholder Rules:**
        *   Fill all placeholders like `{{company_name}}`, `{{role_type}}`, etc., using the provided data.
        *   For the greeting, you MUST use the exact placeholder `{{recipient_name_placeholder}}`. Do NOT use the actual recipient's name.

    5.  **HTML Formatting:** The final email body must be formatted with simple HTML (`<p>`, `<br>`, `<ul>`, `<li>`, `<b>`). Every new paragraph MUST be enclosed in `<p>` tags.

    6.  **JSON Output:** Your entire response MUST be a single, valid JSON object with "subject" and "body" keys. The body should NOT include my signature.

    **Example JSON Output:**
    {{
      "subject": "Idea for leveraging LLMs in your new product line",
      "body": "<p>Hello {{recipient_name_placeholder}},</p><p>I saw the news about your recent funding to expand your AI division and wanted to congratulate you. Given your focus on NLP, I was thinking about how my experience in building RAG systems with PyTorch could help accelerate your roadmap.</p><p>...</p>"
    }}
    '''
    try:
        response = model.generate_content(prompt)
        cleaned_json_string = response.text.strip().replace('```json', '').replace('```', '').strip()
        email_data = json.loads(cleaned_json_string)

        subject = email_data.get("subject", f"Inquiry regarding {recipient_data.get('Company')}")
        body = email_data.get("body", "Hello {{recipient_name_placeholder}},\n\nCould not generate email content.")

        return subject, body

    except (Exception, json.JSONDecodeError) as e:
        logger.error(f"Gemini error or JSON parsing failed during template population: {e}")
        raw_response = "No response object"
        if 'response' in locals() and hasattr(response, 'text'):
            raw_response = response.text.strip()
        logger.error(f"Raw AI response: {raw_response}")
        subject = f"Inquiry regarding opportunities at {recipient_data.get('Company')}"
        body = f"<p>Dear {{recipient_name_placeholder}},</p><p>I am writing to express my strong interest in potential roles at your company.</p>"
        return subject, body

def is_email_safe_to_send(email_subject: str, email_body: str, role_type: str, company_name: str) -> str:
    """Uses Gemini to act as a quality guardrail, checking for relevance and critical errors."""
    model = genai.GenerativeModel(MODEL_NAME)
    prompt = f'''
    You are a Quality Assurance agent. The user is a '{role_type}' graduate applying to '{company_name}'.

    Analyze the following email subject and body. Does this email contain any highly irrelevant topics,
    such as asking for a role in HR, marketing, sales, or any other field that is completely unrelated to the user's profile?
    Does it mention goals or technologies that are nonsensical for a tech applicant?

    Email Subject: {email_subject}
    Email Body: {email_body}

    Your entire response MUST be a single word: 'APPROVE' or 'REJECT'.
    '''
    try:
        response = model.generate_content(prompt)
        return response.text.strip().upper()
    except Exception as e:
        logger.error(f"Error during email safety check: {e}")
        return "REJECT"

def generate_fresher_email(
    tavily_results: dict,
    recipient_name: str,
    recipient_title: str,
    company_name: str,
    role_type: str,
    resume_text: str,
    referral_name: str = None,
    referral_company: str = None
) -> dict:
    """
    Complete fresher-optimized email generation pipeline.
    """
    logger.info("Starting strategic email generation...")
    
    sender_data = extract_sender_details_from_resume(resume_text)
    
    template_category, template_name = choose_initial_template(tavily_results, role_type, referral_name)
    
    recipient_data = {
        'Company': company_name,
        'Title': recipient_title,
        'referral_name': referral_name,
        'referral_company': referral_company,
        'recipient_name': recipient_name  # Add recipient_name here
    }
    
    subject_line, ai_generated_body = populate_template(
        template_type=template_category,
        template_name=template_name,
        tavily_results=tavily_results,
        recipient_data=recipient_data,
        sender_data=sender_data,
        resume_text=resume_text
    )

    safety_check = is_email_safe_to_send(subject_line, ai_generated_body, role_type, company_name)
    if safety_check != "APPROVE":
        logger.warning(f"Email failed safety check. Reason: {safety_check}")
        return {"error": "Email generation failed safety check.", "safety_check_result": safety_check}

    final_email_body = ai_generated_body.replace("{recipient_name_placeholder}", recipient_name)
    
    # Signature is appended here in the final step
    signature = f"<br><br><p>Best regards,</p><p>{sender_data.get('name')}</p>"
    final_email_body += signature

    result = {
        "email_subject": subject_line,
        "email_content": final_email_body,
        "template_used": template_name,
        "template_category": template_category,
        "resume_choice": role_type,
        "safety_check_result": safety_check,
        "performance_tier": "Tier 1"  # Placeholder
    }
    return result


def generate_follow_up_email(
    original_thread_id: str,
    recipient_name: str,
    company_name: str,
    role_type: str,
    resume_text: str,
    follow_up_number: int
) -> dict:
    """
    Generates a concise and polite follow-up email.
    """
    logger.info(f"Generating follow-up #{follow_up_number} for {company_name}...")
    
    sender_data = extract_sender_details_from_resume(resume_text)
    
    # Simple logic to choose a follow-up template
    follow_up_templates = {
        1: "quick_check_in",
        2: "value_add",
        3: "final_check_in"
    }
    template_name = follow_up_templates.get(follow_up_number, "quick_check_in")
    
    # In a real system, you'd have a FOLLOWUP_TEMPLATES dictionary
    template_text = TEMPLATES.get(template_name, {}).get('content', "Following up on my previous email.")
    
    model = genai.GenerativeModel(MODEL_NAME)
    
    prompt = f'''
    You are a professional communicator. Write a concise and polite follow-up email.

    **My Details:**
    - My Name: {sender_data.get('name')}
    - Role I'm interested in: {role_type}

    **Recipient:**
    - Company: {company_name}

    **Template to use:**
    ---
    {template_text}
    ---

    **Instructions:**
    1.  Fill in the placeholders.
    2.  Keep the tone professional and respectful.
    3.  The entire response must be a single JSON object with "subject" and "body" keys.
    4.  The subject should be the same as the original email, just with "Re: " prepended.
    5.  The body should NOT include my signature.
    6.  Use the placeholder `{{recipient_name_placeholder}}` for the greeting.

    **Example JSON Output:**
    {{
      "subject": "Re: Idea for leveraging LLMs",
      "body": "<p>Hello {{recipient_name_placeholder}},</p><p>Just wanted to quickly follow up on my previous email regarding the {role_type} role. I'm still very interested in the possibility of joining {company_name}.</p>"
    }}
    '''
    try:
        response = model.generate_content(prompt)
        cleaned_json_string = response.text.strip().replace('```json', '').replace('```', '').strip()
        email_data = json.loads(cleaned_json_string)
        
        subject = email_data.get("subject", f"Re: Inquiry regarding {company_name}")
        body = email_data.get("body", "Following up.")
        
        # Replace placeholder and add signature
        final_body = body.replace("{recipient_name_placeholder}", recipient_name)
        signature = f"<br><br><p>Best regards,</p><p>{sender_data.get('name')}</p>"
        final_body += signature
        
        return {
            "email_subject": subject,
            "email_content": final_body
        }
        
    except (Exception, json.JSONDecodeError) as e:
        logger.error(f"Error generating follow-up email: {e}")
        return {"error": "Failed to generate follow-up email."}

def track_email_performance(template_name: str, company_name: str, response_received: bool, response_type: str = None):
    """
    Tracks the performance of email templates by logging to a CSV file.
    """
    log_file = 'email_performance.csv'
    log_entry = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "template_name": template_name,
        "company_name": company_name,
        "response_received": response_received,
        "response_type": response_type
    }
    
    try:
        # Check if file exists to write header
        file_exists = pd.io.common.file_exists(log_file)
        
        # Append to CSV
        pd.DataFrame([log_entry]).to_csv(log_file, mode='a', header=not file_exists, index=False)
        
    except Exception as e:
        logger.error(f"Error tracking email performance: {e}")