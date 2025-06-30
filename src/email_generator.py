# src/email_generator.py

import google.generativeai as genai
import pdfplumber
import json
from datetime import datetime
import config
from .templates import EMAIL_TEMPLATES, FOLLOWUP_TEMPLATES, SIGNATURE
import logging

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

# --- Key Achievements Arsenal ---
KEY_ACHIEVEMENTS = [
    "3.5x processing speed boost",
    "42% improved document summarization accuracy",
    "60% reduced semantic search latency",
    "70% faster deployment times",
    "35% boost in user retention",
    "30% faster load times"
]

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

def analyze_and_choose_resume(tavily_results: str, recruiter_title: str) -> str:
    """Uses Gemini to decide which resume to send based on Tavily search results."""
    model = genai.GenerativeModel(MODEL_NAME)
    prompt = f"""
    You are an expert career advisor. Your task is to choose the best resume to send based on the following information.

    **Company Research from Tavily:**
    {tavily_results}

    **Recruiter's Title:** "{recruiter_title}"

    Analyze the research and the recruiter's title. Should I send my "AI/ML" resume or my "Fullstack" resume?
    
    Your entire response MUST be ONLY ONE of the following two options:
    - AI/ML
    - Fullstack
    """
    try:
        response = model.generate_content(prompt)
        choice = response.text.strip()
        logger.info(f"AI chose resume type: {choice} for recruiter title: {recruiter_title}.")
        if choice in ["AI/ML", "Fullstack"]:
            return choice
        logger.warning(f"Unexpected resume choice from AI: {choice}. Defaulting to Fullstack.")
        return "Fullstack" # Default if the response is unexpected
    except Exception as e:
        logger.error(f"Gemini error during resume analysis: {e}")
        return "Fullstack" # Default on error

def extract_company_insights(tavily_results: str) -> dict:
    """Extract specific company details for hyper-personalization"""
    model = genai.GenerativeModel(MODEL_NAME)
    prompt = f"""
    Extract key company insights from this research for personalized outreach:
    
    {tavily_results}
    
    Return JSON with:
    - recent_achievements: Recent company milestones/funding/products
    - tech_stack: Technologies they use
    - company_size: Startup/mid-size/enterprise
    - industry_focus: Main business area
    - current_challenges: Problems they might be solving
    - hiring_indicators: Signs they're actively hiring
    
    Format as valid JSON only.
    """
    try:
        response = model.generate_content(prompt)
        cleaned_response = response.text.strip().replace('```json', '').replace('```', '').strip()
        return json.loads(cleaned_response)
    except Exception as e:
        logger.error(f"Error extracting company insights: {e}")
        logger.error(f"Raw AI response for company insights: {response.text.strip() if 'response' in locals() else 'No response'}")
        return {}

def determine_graduation_timeline() -> str:
    """Determine urgency based on current date and graduation timeline"""
    current_month = datetime.now().month
    if current_month >= 4 and current_month <= 6:
        return "May 2025"  # Final semester
    elif current_month >= 10 and current_month <= 12:
        return "December 2025"  # Mid-year graduation
    else:
        return "upcoming semester"

def extract_sender_details_from_resume(resume_text: str) -> dict:
    """Uses Gemini to extract key personal details from a resume text."""
    model = genai.GenerativeModel(MODEL_NAME)
    prompt = f"""
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
    """
    try:
        response = model.generate_content(prompt)
        cleaned_response = response.text.strip().replace('```json', '').replace('```', '').strip()
        return json.loads(cleaned_response)
    except Exception as e:
        logger.error(f"Error extracting sender details from resume: {e}")
        return {"degree": "", "key_skills": "", "project_experience": "", "name": ""}

def extract_achievement_keywords(resume_data: str) -> list:
    """Extract quantified achievements for subject lines and hooks"""
    model = genai.GenerativeModel(MODEL_NAME)
    prompt = f"""
    From this resume, extract the top 5 most impressive quantified achievements 
    that would make strong email subject lines:
    
    {resume_data}
    
    Return as a Python list of strings, focusing on:
    - Percentage improvements
    - Performance metrics
    - Scale achievements (users, data processed, etc.)
    
    Example format: ["60% latency reduction", "3.5x processing speed boost"]
    """
    try:
        response = model.generate_content(prompt)
        cleaned_response = response.text.strip().replace('```python', '').replace('```', '').replace('print(achievements)', '').strip()
        import ast
        return ast.literal_eval(cleaned_response)
    except Exception as e:
        logger.error(f"Error extracting achievement keywords: {e}")
        logger.error(f"Raw AI response for achievement keywords: {response.text.strip() if 'response' in locals() else 'No response'}")
        return ["Built scalable AI systems", "Achieved significant performance gains"]

def get_best_performing_template() -> str:
    """Get the template with highest response rate"""
    try:
        with open('email_performance.json', 'r') as f:
            data = json.load(f)
        
        best_template = "project_showcase"  # default
        best_rate = 0
        
        for template, stats in data.get("stats", {}).items():
            if stats["sent"] >= 5 and stats["response_rate"] > best_rate:  # minimum 5 sends
                best_rate = stats["response_rate"]
                best_template = template
        
        return best_template
    except Exception as e:
        logger.error(f"Error getting best performing template: {e}")
        return "project_showcase"

def choose_initial_template(tavily_results: str, role_type: str) -> str:
    """
    Uses Gemini to select the best initial outreach template based on role and research.
    """
    model = genai.GenerativeModel(MODEL_NAME)
    
    # Define the purpose of each template style for the AI
    template_style_descriptions = """
    - `quick_question`: A polite and direct inquiry, best for general outreach or when the company's specific needs are unknown.
    - `metric_driven`: Leads with a specific, quantifiable achievement. Ideal for companies that appear data-driven or results-oriented.
    - `story`: Uses a narrative to showcase problem-solving and adaptability. Good for companies with a strong culture or brand story.
    - `curiosity`: Poses a question to spark interest and frame a problem. Best for innovative companies or when you can offer a unique perspective.
    - `direct_bullets`: A concise, scannable summary of achievements. Perfect for busy recruiters or very formal corporate environments.
    """

    # Dynamically select the list of templates based on the role
    if role_type == "AI/ML":
        available_templates = [key for key in EMAIL_TEMPLATES.keys() if key.startswith('ai_')]
        role_context = "The user is applying for an AI/ML or Data Science role."
    else: # Default to Fullstack
        available_templates = [key for key in EMAIL_TEMPLATES.keys() if key.startswith('fullstack_')]
        role_context = "The user is applying for a Fullstack or Frontend developer role."

    prompt = f"""
    You are an expert career strategist. Your task is to select the single best email template for a job-seeking fresher.

    **Context:** {role_context}

    **Company Research from Tavily:**
    {tavily_results}

    **Available Template Styles and Their Purpose:**
    {template_style_descriptions}

    **List of Available Template Names for this Role:**
    {available_templates}

    Analyze all the information. Based on the company research, choose the most appropriate template NAME from the list provided. Your response MUST be ONLY the single template name you choose.
    """
    try:
        response = model.generate_content(prompt)
        choice = response.text.strip()
        logger.info(f"AI chose initial template: {choice} for role type: {role_type}.")
        if choice in available_templates:
            return choice
        logger.warning(f"Unexpected template choice from AI: {choice}. Defaulting to {available_templates[0]}.")
        # Fallback logic: return the first available template for the role
        return available_templates[0]
    except Exception as e:
        logger.error(f"Gemini error during template selection: {e}")
        return available_templates[0] # Default on error

def populate_template(template_type: str, template_name: str, tavily_results: str, recipient_data: dict, sender_data: dict, resume_text: str) -> tuple[str, str]:
    """
    Uses Gemini to fill in template placeholders, including dynamic metrics.
    """
    model = genai.GenerativeModel(MODEL_NAME)

    if template_type == 'initial':
        template_text = EMAIL_TEMPLATES.get(template_name)
    elif template_type == 'followup':
        template_text = FOLLOWUP_TEMPLATES.get(template_name)
    else:
        raise ValueError("Invalid template_type specified.")

    # Format the structured insights into a clean string for the prompt
    tavily_research_summary = (
        f"1. Recent News: {tavily_results.get('recent_news')}\n"
        f"2. Tech Stack: {tavily_results.get('tech_stack')}\n"
        f"3. Mission & Values: {tavily_results.get('mission_and_values')}"
    )

    if template_name == "value_add_followup":
        tavily_research_summary += f"\n4. Recent Company Updates (for value-add follow-up): {tavily_results.get('recent_news_for_followup', 'No specific recent updates found.')}"

    prompt = f"""
    You are a master copywriter. Your task is to take a template and fill its placeholders to create a compelling cold email.

    **My Personal Details (from resume):**
    - My Name: {sender_data.get('name')}
    - My Degree: {sender_data.get('degree')}
    - My Key Skills: {sender_data.get('key_skills')}
    - Relevant Project Experience Summary: {sender_data.get('project_experience')}
    - Graduation Timeline: {determine_graduation_timeline()}

    **Company Research (for context):**
    {tavily_research_summary}
    
    **My Full Resume Text (for deep analysis):**
    {resume_text}

    **Email Template to Populate:**
    ---
    {template_text}
    ---

    **CRITICAL INSTRUCTIONS:**
    1.  **Fill Placeholders:** Creatively fill in all placeholders like `{{company_name}}`, `{{role_type}}`, etc.
    2.  **Dynamic Metrics:** The template may contain a `{{metric}}` placeholder. Analyze my resume and project experience to find the most relevant and impressive number or statistic for that specific template. Replace `{{metric}}` with that number (e.g., replace '{{metric}}%' with '40%').
    3.  **Salutation:** For the greeting, you MUST use the exact placeholder `{{recipient_name_placeholder}}`. Do NOT use the actual recipient's name.
    4.  **HTML Formatting:** The final email body must be formatted with simple HTML (`<p>`, `<br>`, `<ul>`, `<li>`, `<b>`). Every new line MUST be an HTML tag.
    5.  **JSON Output:** Your entire response MUST be a single, valid JSON object with "subject" and "body" keys. The body should NOT include my signature.

    **Example JSON Output:**
    {{
      "subject": "Boosted web app performance by 30% — idea for {recipient_data.get('Company')}",
      "body": "<p>Hello {{recipient_name_placeholder}},</p><p>I’m Ashish, a full-stack developer (React/Node) and recent IT graduate...</p>"
    }}
    """
    try:
        response = model.generate_content(prompt)
        cleaned_json_string = response.text.strip().replace('```json', '').replace('```', '').strip()
        email_data = json.loads(cleaned_json_string)
        
        subject = email_data.get("subject", f"Inquiry regarding {recipient_data.get('Company')}")
        body = email_data.get("body", "Hello {{recipient_name_placeholder}},\n\nCould not generate email content.")
        
        # Return the raw body with the placeholder. DO NOT add the signature here.
        return subject, body
        
    except (Exception, json.JSONDecodeError) as e:
        logger.error(f"Gemini error or JSON parsing failed during template population: {e}")
        subject = f"Inquiry regarding opportunities at {recipient_data.get('Company')}"
        body = f"<p>Dear {{recipient_name_placeholder}},</p><p>I am writing to express my strong interest in potential roles at your company.</p>"
        return subject, body

def is_email_safe_to_send(email_subject: str, email_body: str, role_type: str, company_name: str) -> str:
    """Uses Gemini to act as a quality guardrail, checking for relevance and critical errors."""
    model = genai.GenerativeModel(MODEL_NAME)
    prompt = f"""
    You are a Quality Assurance agent. The user is a '{role_type}' graduate applying to '{company_name}'.

    Analyze the following email subject and body. Does this email contain any highly irrelevant topics,
    such as asking for a role in HR, marketing, sales, or any other field that is completely unrelated to the user's profile?
    Does it mention goals or technologies that are nonsensical for a tech applicant?

    Email Subject: {email_subject}
    Email Body: {email_body}

    Your entire response MUST be a single word: 'APPROVE' or 'REJECT'.
    """
    try:
        response = model.generate_content(prompt)
        return response.text.strip().upper()
    except Exception as e:
        logger.error(f"Error during email safety check: {e}")
        return "REJECT" # Default to reject on error for safety

def track_email_performance(
    template_name: str, 
    company_name: str, 
    response_received: bool,
    response_type: str = None
) -> None:
    """Track email performance for optimization"""
    
    # Load existing data
    try:
        with open('email_performance.json', 'r') as f:
            data = json.load(f)
    except:
        data = {"campaigns": [], "stats": {}}
    
    # Add new record
    record = {
        "date": datetime.now().isoformat(),
        "template": template_name,
        "company": company_name,
        "response": response_received,
        "response_type": response_type,  # "positive", "negative", "auto-reply"
    }
    
    data["campaigns"].append(record)
    
    # Calculate stats
    template_stats = {}
    for campaign in data["campaigns"]:
        template = campaign["template"]
        if template not in template_stats:
            template_stats[template] = {"sent": 0, "responses": 0}
        
        template_stats[template]["sent"] += 1
        if campaign["response"]:
            template_stats[template]["responses"] += 1
    
    # Calculate response rates
    for template in template_stats:
        stats = template_stats[template]
        stats["response_rate"] = stats["responses"] / stats["sent"] if stats["sent"] > 0 else 0
    
    data["stats"] = template_stats
    
    # Save updated data
    with open('email_performance.json', 'w') as f:
        json.dump(data, f, indent=2)
    
    logging.info(f"Performance tracked: {template_name} - {'✓' if response_received else '✗'}")

def generate_fresher_email(
    tavily_results: str,
    recipient_name: str,
    recipient_title: str,
    company_name: str,
    role_type: str,
    resume_text: str # Added resume_text as a direct argument
) -> dict:
    """
    Complete fresher-optimized email generation pipeline.
    This function now handles the final name replacement and signature attachment.
    """
    logger.info("Starting fresher-optimized email generation...")
    
    # 1. Determine which resume type was chosen (for tracking/reporting)
    resume_choice = analyze_and_choose_resume(tavily_results, recipient_title)
    
    if not resume_text:
        logger.error("Resume text not provided to generate_fresher_email.")
        return {"error": "Resume text not provided."}
    
    # Extract sender details directly from the resume
    sender_details = extract_sender_details_from_resume(resume_text)
    if not sender_details["name"] or not sender_details["degree"]:
        logger.error("Could not extract essential sender details from resume.")
        return {"error": "Could not extract essential sender details from resume."}

    # 2. Choose optimal template
    template_name = choose_initial_template(tavily_results, role_type)
    
    # 3. Prepare data for the template (NOTE: recipient_name is not needed by the AI anymore)
    recipient_data = {
        'Company': company_name,
        'Title': recipient_title
    }
    sender_data = {
        'name': sender_details["name"],
        'degree': sender_details["degree"],
        'key_skills': sender_details["key_skills"],
        'project_experience': sender_details["project_experience"],
    }

    # 4. Generate email with a placeholder for the name
    subject_line, ai_generated_body = populate_template(
        template_type='initial',
        template_name=template_name,
        tavily_results=tavily_results,
        recipient_data=recipient_data,
        sender_data=sender_data,
        resume_text=resume_text
    )

    # 5. --- THIS IS THE GUARDRAIL ---
    # Replace the placeholder with the real name and attach the standard signature.
    sanitized_body = ai_generated_body.replace('\n', '<br>')
    final_email_body = sanitized_body.replace('{{recipient_name_placeholder}}', recipient_name).replace('{recipient_name_placeholder}', recipient_name) + SIGNATURE

    # 6. Run the pre-send quality guardrail
    safety_check_result = is_email_safe_to_send(subject_line, final_email_body, role_type, company_name)
    if safety_check_result == "REJECT":
        logger.warning(f"[GUARDRAIL REJECTED]: Email for {company_name} was deemed irrelevant and has been blocked.")
    else:
        logger.info("Failsafe check passed.")

    def validate_email_quality(email_content: str, resume_text: str) -> dict:
        """Uses Gemini to evaluate the quality of the generated email against the resume."""
        model = genai.GenerativeModel(MODEL_NAME)
        prompt = f"""
        You are an expert email quality assurance specialist. Your task is to evaluate the following cold email
        against the provided resume to ensure it is highly personalized, relevant, and compelling for a job application.
    
        **Email Content:**
        {email_content}
    
        **Candidate's Resume Text:**
        {resume_text}
    
        **Evaluation Criteria:**
        1.  **Relevance (0-10):** How well does the email align with the candidate's skills and experience as presented in the resume?
        2.  **Personalization (0-10):** How well does the email incorporate specific details from the resume or imply research into the candidate's background? (e.g., mentioning specific projects, skills, or achievements from the resume).
        3.  **Clarity & Conciseness (0-10):** Is the email easy to read, to the point, and free of jargon?
        4.  **Call to Action (0-10):** Is there a clear, polite, and effective call to action?
        5.  **Overall Impact (0-10):** How likely is this email to get a positive response based on its quality and personalization?
    
        Provide a JSON object with the following structure:
        -   `overall_score`: An integer from 0-10 (average of the above scores).
        -   `strengths`: A list of bullet points highlighting what the email does well.
        -   `improvements`: A list of bullet points suggesting specific ways to improve the email.
        -   `reasoning`: A brief paragraph explaining the overall score and key observations.
    
        Example JSON Output:
        {{
          "overall_score": 8,
          "strengths": [
            "Clearly highlights relevant project experience.",
            "Good personalization by mentioning specific skills."
          ],
          "improvements": [
            "Could include a more direct call to action.",
            "Subject line could be more engaging."
          ],
          "reasoning": "The email is well-structured and personalized, effectively showcasing the candidate's relevant experience. A stronger call to action would further enhance its effectiveness."
        }}
        """
        try:
            response = model.generate_content(prompt)
            cleaned_json_string = response.text.strip().replace('```json', '').replace('```', '').strip()
            return json.loads(cleaned_json_string)
        except Exception as e:
            logger.error(f"Error validating email quality: {e}")
            return {
                "overall_score": 5,
                "strengths": ["Basic email structure is present."],
                "improvements": ["Failed to run quality check. Manual review needed."],
                "reasoning": "An error occurred during the AI quality validation process."
            }

    # 7. Validate quality
    quality_report = validate_email_quality(f"Subject: {subject_line}\n\n{final_email_body}", resume_text)

    # 8. Prepare result with the finalized content
    result = {
        "email_subject": subject_line,
        "email_content": final_email_body, # Return the final, processed body
        "template_used": template_name,
        "resume_choice": resume_choice,
        "quality_score": quality_report.get("overall_score", 0),
        "recommendations": quality_report.get("improvements", []),
        "strengths": quality_report.get("strengths", []),
        "safety_check_result": safety_check_result # Add the safety check result here
    }
    
    print(f"✅ Email generated successfully! Name inserted and signature attached.")
    
    return result


# Example usage and testing
if __name__ == '__main__':
    # Test the complete system
    test_data = {
        "tavily_results": "Google is hiring for multiple engineering roles in their Cloud AI division. They recently announced significant investments in LLM research and are looking for fresh talent to join their team.",
        "recipient_name": "Sarah Chen",
        "recipient_title": "Senior Technical Recruiter - AI Engineering",
        "company_name": "Google",
        "role_type": "Software Engineer - AI/ML"
    }
    
    result = generate_fresher_email(**test_data)
    
    if "error" not in result:
        print("\n" + "="*50)
        print("GENERATED EMAIL:")
        print("="*50)
        print(result["email_content"])
        print("\n" + "="*50)
        print(f"Quality Score: {result['quality_score']}/10")
        print(f"Template: {result['template_used']}")
        print(f"Resume: {result['resume_choice']}")
        if result["recommendations"]:
            print("Recommendations:", ", ".join(result["recommendations"]))