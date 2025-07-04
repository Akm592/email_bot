# src/email_generator.py

import google.generativeai as genai
import pdfplumber
import json
from datetime import datetime
import config
from .templates import TEMPLATES
import logging
import pandas as pd
import hashlib
from typing import Dict, Any

class ResumeAnalysisCache:
    def __init__(self):
        self.cache = {}

    def get_analysis(self, resume_type: str, resume_text: str, analysis_func) -> Dict:
        text_hash = hashlib.md5(resume_text.encode()).hexdigest()
        cache_key = f"{resume_type}:{text_hash}"
        if cache_key in self.cache:
            logging.info(f"Resume analysis cache hit for {resume_type}")
            return self.cache[cache_key]
        
        logging.info(f"Resume analysis cache miss for {resume_type}. Performing analysis...")
        analysis = analysis_func(resume_text) # Call the actual analysis function
        self.cache[cache_key] = analysis
        return analysis

resume_analysis_cache = ResumeAnalysisCache()

# Get logger for this module
logger = logging.getLogger(__name__)

MODEL_NAME = "gemini-2.0-flash"
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

def _perform_resume_choice_analysis_internal(tavily_results: dict, recruiter_title: str) -> str:
    """Internal function to perform the actual Gemini call for resume choice analysis."""
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

def _perform_resume_choice_analysis_wrapper(input_string: str) -> str:
    """Wrapper to parse input string and call the internal resume choice analysis function."""
    try:
        data = json.loads(input_string)
        tavily_results = data['tavily_results']
        recruiter_title = data['recruiter_title']
        return _perform_resume_choice_analysis_internal(tavily_results, recruiter_title)
    except Exception as e:
        logger.error(f"Error in resume choice analysis wrapper: {e}")
        return "Fullstack" # Default fallback

def analyze_and_choose_resume(tavily_results: dict, recruiter_title: str) -> str:
    """Uses Gemini to decide which resume to send based on structured Tavily results, with caching."""
    input_for_cache = json.dumps({
        "tavily_results": tavily_results,
        "recruiter_title": recruiter_title
    })
    
    return resume_analysis_cache.get_analysis(
        resume_type="resume_choice",
        resume_text=input_for_cache,
        analysis_func=_perform_resume_choice_analysis_wrapper
    )

def decide_whether_to_attach_resume(tavily_results: dict) -> bool:
    """
    Decides whether to attach a resume based on whether a specific job opening was found.
    """
    logger.info("Deciding whether to attach resume...")
    # Check if the specific search for a job opening yielded a concrete result.
    job_opening_data = tavily_results.get("hiringIntelligence", {}).get("relevantJobOpening")
    if job_opening_data and "Unable to answer" not in job_opening_data.get("data", ""):
        logger.info("-> Decision: ATTACH resume (specific job opening found).")
        return True
    logger.info("-> Decision: DO NOT ATTACH resume (general outreach).")
    return False

def determine_graduation_timeline() -> str:
    """Determine urgency based on current date and graduation timeline"""
    current_month = datetime.now().month
    if 4 <= current_month <= 6:
        return "May 2025"
    elif 10 <= current_month <= 12:
        return "December 2025"
    else:
        return "upcoming semester"

def _perform_sender_details_extraction(resume_text: str) -> dict:
    """Internal function to perform the actual Gemini call for sender details extraction."""
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

def extract_sender_details_from_resume(resume_text: str) -> dict:
    """Uses cache for sender details extraction from a resume text."""
    return resume_analysis_cache.get_analysis(
        resume_type="sender_details",
        resume_text=resume_text,
        analysis_func=_perform_sender_details_extraction
    )

from src.context_manager import context_aware_processor

def _perform_template_choice_internal(tavily_results: dict, role_type: str, referral_name: str = None) -> tuple[str, str]:
    """Internal function to perform the actual Gemini call for template choice."""    
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

    # Use ContextAwareProcessor to select the optimal template
    company_cluster = tavily_results.get("secondaryContext", {}).get("businessContext", {}).get("companyName", "") # Placeholder for actual clustering
    if not company_cluster:
        company_cluster = tavily_results.get("secondaryContext", {}).get("businessContext", {}).get("companyWebsite", {}).get("data", "unknown_company")

    optimal_template = context_aware_processor.select_optimal_template(available_templates, company_cluster)
    
    # If the optimal template is not one of the available ones, fall back to the first available
    if optimal_template not in available_templates:
        optimal_template = available_templates[0]

    # The rest of the Gemini call for template selection is no longer needed if we rely on performance data
    # However, if we want Gemini to *learn* and *suggest* new templates, this part would be re-integrated
    # For now, we're using the performance data directly.
    logger.info(f"Selected optimal template: {optimal_template} for role type: {role_type}.")
    return "initial", optimal_template

def _perform_template_choice_wrapper(input_string: str) -> tuple[str, str]:
    """Wrapper to parse input string and call the internal template choice function."""
    try:
        data = json.loads(input_string)
        tavily_results = data['tavily_results']
        role_type = data['role_type']
        referral_name = data.get('referral_name')
        return _perform_template_choice_internal(tavily_results, role_type, referral_name)
    except Exception as e:
        logger.error(f"Error in template choice wrapper: {e}")
        return "initial", "value_proposition" # Default fallback

def choose_initial_template(tavily_results: dict, role_type: str, referral_name: str = None) -> tuple[str, str]:
    """
    Strategically selects the best initial outreach template based on structured data, with caching.
    """
    logger.info("Strategically choosing an email template...")

    if referral_name and pd.notna(referral_name) and referral_name.strip() != "":
        logger.info(f"Referral found: {referral_name}. Selecting 'referral_introduction' template.")
        return "initial", "referral_introduction"

    input_for_cache = json.dumps({
        "tavily_results": tavily_results,
        "role_type": role_type,
        "referral_name": referral_name
    })

    return resume_analysis_cache.get_analysis(
        resume_type="template_choice",
        resume_text=input_for_cache,
        analysis_func=_perform_template_choice_wrapper
    )

def populate_template(template_type: str, template_name: str, tavily_results: dict, recipient_data: dict, sender_data: dict, resume_text: str, should_attach_resume: bool) -> tuple[str, str]:
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

    # DYNAMIC INSTRUCTION based on the decision
    attachment_instruction = ""
    if should_attach_resume:
        attachment_instruction = "The resume WILL BE ATTACHED to this email. Your email body MUST mention this. For example: 'I have attached my resume for your convenience and further details.'"
    else:
        attachment_instruction = "The resume WILL NOT be attached. Your email body MUST reflect this by politely OFFERING to send it. For example: 'I would be happy to share my resume if you find my background relevant.'"

    prompt = f'''
    You are a master copywriter writing a cold email to an IT hiring manager.

    **MISSION:** Write a concise, personalized email based on the context provided.

    **1. SITUATIONAL CONTEXT (VERY IMPORTANT):**
    *   **Attachment Status:** {attachment_instruction}

    **2. DATA TO USE:**
    *   **My Profile:** {json.dumps(sender_data)}
    *   **Recipient:** {json.dumps(recipient_data)}
    *   **Company Research & Job Openings:** {research_summary_for_prompt}

    **3. WRITING RULES:**
    *   **Follow the Attachment Instruction:** Your email's content about the resume MUST match the instruction in the "Attachment Status" above. This is the most important rule.
    *   **Be Specific:** If the research found a `relevantJobOpening`, mention it in the subject and body. This makes the email a direct application. If not, treat it as a networking request.
    *   **Structure:** Keep it to 3-4 short paragraphs (Intro -> Value Prop -> Alignment -> CTA).
    *   **CTA:** Your call to action should be a brief chat.

    **4. OUTPUT FORMAT:**
    *   A single, valid JSON object with "subject" and "body" keys.
    *   The body must be simple HTML.
    *   Use the placeholder `{{recipient_name_placeholder}}` for the greeting.
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

def _perform_safety_check_internal(email_subject: str, email_body: str, role_type: str, company_name: str) -> str:
    """Internal function to perform the actual Gemini call for email safety check."""
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

def _perform_safety_check_wrapper(input_string: str) -> str:
    """Wrapper to parse input string and call the internal safety check function."""
    try:
        data = json.loads(input_string)
        return _perform_safety_check_internal(
            data['email_subject'],
            data['email_body'],
            data['role_type'],
            data['company_name']
        )
    except Exception as e:
        logger.error(f"Error in safety check wrapper: {e}")
        return "REJECT" # Default fallback

def is_email_safe_to_send(email_subject: str, email_body: str, role_type: str, company_name: str) -> str:
    """Uses Gemini to act as a quality guardrail, checking for relevance and critical errors, with caching."""
    input_for_cache = json.dumps({
        "email_subject": email_subject,
        "email_body": email_body,
        "role_type": role_type,
        "company_name": company_name
    })
    return resume_analysis_cache.get_analysis(
        resume_type="email_safety_check",
        resume_text=input_for_cache,
        analysis_func=_perform_safety_check_wrapper
    )

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

    # NEW: Make the attachment decision early
    should_attach = decide_whether_to_attach_resume(tavily_results)

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
        resume_text=resume_text,
        should_attach_resume=should_attach # Pass the decision
    )

    safety_check = is_email_safe_to_send(subject_line, ai_generated_body, role_type, company_name)
    if safety_check != "APPROVE":
        logger.warning(f"Email failed safety check. Reason: {safety_check}")
        return {"error": "Email generation failed safety check.", "safety_check_result": safety_check}

    final_email_body = ai_generated_body.replace("{recipient_name_placeholder}", recipient_name)
    
    # Construct the new professional signature
    signature_links = [
        config.YOUR_LINKEDIN_URL,
        config.YOUR_GITHUB_URL,
        config.YOUR_PORTFOLIO_URL
    ]
    # Filter out any empty links
    valid_links = [link for link in signature_links if link]
    def get_display_name(url):
        if "linkedin" in url:
            return "LinkedIn"
        elif "github" in url:
            return "GitHub"
        elif "portfolio" in url:
            return "Portfolio"
        else:
            return url.split("://")[-1].split("/")[0] # Fallback to domain name
    signature_html = " | ".join(f'<a href="{link}">{get_display_name(link)}</a>' for link in valid_links)

    signature = f"<br><br><p>Best regards,</p><p>{sender_data.get('name')}<br>{signature_html}</p>"
    final_email_body += signature

    result = {
        "email_subject": subject_line,
        "email_content": final_email_body,
        "should_attach_resume": should_attach, # CRITICAL: Return the decision
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
    Tracks the performance of email templates by logging to a CSV file and updating the ContextAwareProcessor.
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
        
        # Update context-aware processor
        from src.context_manager import context_aware_processor
        context_aware_processor.update_template_performance(template_name, company_name, response_received)
        
    except Exception as e:
        logger.error(f"Error tracking email performance: {e}")