# src/email_generator.py

import google.generativeai as genai
import pdfplumber
import json
from datetime import datetime
import config
from .templates import EMAIL_TEMPLATES, FOLLOWUP_TEMPLATES, SIGNATURE

MODEL_NAME = "gemini-2.0-flash-lite"
AI_ML_RESUME_PATH = config.AI_ML_RESUME
FULLSTACK_RESUME_PATH = config.FULLSTACK_RESUME
gem_key=config.GEMINI_API_KEY


try:
   

    genai.configure(api_key=gem_key)
 
  
except Exception as e:
    print(f"Error configuring Gemini API: {e}")

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
        print(f"Error loading resume from {resume_path}: {e}")
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
        if choice in ["AI/ML", "Fullstack"]:
            return choice
        return "Fullstack" # Default if the response is unexpected
    except Exception as e:
        print(f"Gemini error during resume analysis: {e}")
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
        print(f"Error extracting company insights: {e}")
        print(f"Raw AI response for company insights: {response.text.strip() if 'response' in locals() else 'No response'}")
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
        print(f"Error extracting achievement keywords: {e}")
        print(f"Raw AI response for achievement keywords: {response.text.strip() if 'response' in locals() else 'No response'}")
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
        print(f"Error getting best performing template: {e}")
        return "project_showcase"

def choose_initial_template(tavily_results: str, role_applied_for: str) -> str:
    """
    Uses Gemini to select the best initial outreach template.
    """
    model = genai.GenerativeModel(MODEL_NAME)
    
    # Describes the purpose of each template for the AI
    template_descriptions = """
    - `project_showcase`: Lead with your single most impressive project result.
    - `skill_to_problem_match`: Directly map one of your skills to a problem the company likely has.
    - `brutally_direct_proof`: A short, brutally direct email that uses a stat as the hook.
    """

    # Dynamically adjust the prompt based on whether a specific role is provided
    if role_applied_for:
        context_prompt = f"The user is applying for a specific role: '{role_applied_for}'."
    else:
        context_prompt = "The user is making a general inquiry about potential opportunities, not applying for a specific listed role."

    prompt = f"""
    You are an expert career strategist. Your task is to select the single best email template for a job-seeking fresher.

    **Context:** {context_prompt}

    **Company Research from Tavily:**
    {tavily_results}

    **Available Templates and Their Purpose:**
    {template_descriptions}

    Analyze all the information and choose the most appropriate template name from the list. Your response MUST be ONLY a single template name.
    """
    try:
        response = model.generate_content(prompt)
        choice = response.text.strip()
        if choice in EMAIL_TEMPLATES.keys():
            return choice
        # Fallback logic
        return "skill_to_problem_match" if role_applied_for else "project_showcase"
    except Exception as e:
        print(f"Gemini error during template selection: {e}")
        return "general_startup"



def validate_email_quality(email_content: str, resume_data: str) -> dict:
    """Comprehensive email quality validation"""
    model = genai.GenerativeModel(MODEL_NAME)
    
    prompt = f"""
    Evaluate this cold email for a fresh graduate and provide quality scores:
    
    **EMAIL:**
    {email_content}
    
    **RESUME CONTEXT:**
    {resume_data}
    
    Rate each aspect from 1-10 and provide feedback:
    
    1. **Personalization Level**: How specific and tailored is this email?
    2. **Fresher Positioning**: How well does it position the candidate as a strong fresh graduate?
    3. **Technical Credibility**: How effectively does it demonstrate technical skills?
    4. **Business Value**: How clearly does it connect skills to business impact?
    5. **Professionalism**: How professional and polished is the writing?
    6. **Call-to-Action**: How clear and compelling is the next step?
    7. **Length Appropriateness**: Is it concise yet comprehensive? (ideal: 75-125 words)
    
    Return as JSON:
    {{
        "scores": {{"personalization": 8, "fresher_positioning": 7, ...}},
        "overall_score": 7.8,
        "feedback": "Specific improvement suggestions",
        "strengths": ["What works well"],
        "improvements": ["What to fix"]
    }}
    """
    
    try:
        response = model.generate_content(prompt)
        cleaned_response = response.text.strip().replace('```json', '').replace('```', '').strip()
        return json.loads(cleaned_response)
    except Exception as e:
        print(f"Error validating email quality: {e}")
        print(f"Raw AI response for email quality: {response.text.strip() if 'response' in locals() else 'No response'}")
        return {"overall_score": 0, "feedback": "Could not validate email quality"}

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
    
    print(f"Performance tracked: {template_name} - {'✓' if response_received else '✗'}")

def choose_optimal_template(tavily_results: str, recipient_info: dict, performance_data: dict = None) -> str:
    """Choose template based on context and performance data"""
    
    # Get performance-based recommendation
    best_performing = get_best_performing_template() if performance_data else "project_showcase"
    
    # Get context-based recommendation  
    context_based = choose_initial_template(tavily_results, recipient_info)
    
    # If performance data is strong, weight it heavily
    if performance_data and performance_data.get(best_performing, {}).get("sent", 0) >= 10:
        return best_performing
    else:
        return context_based

def populate_template(template_type: str, template_name: str, tavily_results: str, recipient_data: dict, sender_data: dict, resume_text: str) -> tuple[str, str]:
    """
    Uses Gemini to fill in template placeholders. It is explicitly told to use a placeholder
    for the recipient's name, which will be replaced later.
    """
    model = genai.GenerativeModel(MODEL_NAME)

    if template_type == 'initial':
        template_text = EMAIL_TEMPLATES.get(template_name, EMAIL_TEMPLATES['project_showcase'])
    elif template_type == 'followup':
        template_text = FOLLOWUP_TEMPLATES.get(template_name, FOLLOWUP_TEMPLATES['first_followup'])
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
    You are a master copywriter specializing in professional emails. Your task is to take a template and fill its placeholders to create a compelling cold email.

    **Company and Role Data:**
    - Company Name: {recipient_data.get('Company')}
    - Specific Role (if any): {recipient_data.get('Title')}

    **My Personal Details:**
    - My Name: {sender_data.get('name')}
    - My Degree: {sender_data.get('degree')}
    - My Key Skills: {sender_data.get('key_skills')}
    - Relevant Project Experience: {sender_data.get('project_experience')}
    - Graduation Timeline: {determine_graduation_timeline()}

    **Company Research from Tavily (for context):**
    {tavily_research_summary}

    **My Resume Text (for deep analysis):
    {resume_text}

    **Email Template to Populate:**
    ---
    {template_text}
    ---

    **CRITICAL INSTRUCTIONS:**
    1.  You are a career strategist. Your primary source of truth for the candidate's skills is the provided resume text. Analyze it deeply and extract the most relevant project, skill, or achievement that aligns with the target company's profile. Use this insight to write the email.
    2.  For the salutation (e.g., "Dear..."), you MUST use the exact placeholder `{{recipient_name_placeholder}}`. Do NOT use the actual recipient's name. For example, write "Dear {{recipient_name_placeholder}},"
    3.  Creatively fill in all other placeholders (e.g., `{{company_mission}}`).
    4.  The final email body must be formatted with simple HTML (`<p>` and `<br>`).
    5.  Your entire response MUST be a single, valid JSON object with two keys: "subject" and "body". The body should NOT include my signature.
    6.  If this is a follow-up email (template_type is 'followup'), briefly reference a specific point from the initial research (e.g., {tavily_results.get('recent_news')} or {tavily_results.get('mission_and_values')}) to remind the recipient why you are interested. Do not repeat the entire first email.
    7.  If the template is `value_add_followup`, incorporate the `Recent Company Updates` from the Tavily research into the email to provide new, relevant information.
    8. CRITICAL: Every new line or paragraph break MUST be an HTML tag (<br> or <p>). Do not use \n.
"""

    **Example JSON Output:**
    {{
      "subject": "Interest in AI/ML Opportunities at {recipient_data.get('Company')}",
      "body": "<p>Dear {{recipient_name_placeholder}},</p><p>I was impressed to learn about {recipient_data.get('Company')}'s recent launch of...</p>"
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
        print(f"Gemini error or JSON parsing failed: {e}")
        subject = f"Inquiry regarding opportunities at {recipient_data.get('Company')}"
        body = f"<p>Dear {{recipient_name_placeholder}},</p><p>I am writing to express my strong interest in potential roles at your company.</p>"
        return subject, body

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
    print(" Starting fresher-optimized email generation...")
    
    # 1. Determine which resume type was chosen (for tracking/reporting)
    resume_choice = analyze_and_choose_resume(tavily_results, recipient_title)
    
    if not resume_text:
        return {"error": "Resume text not provided."}
    
    # 2. Choose optimal template
    template_name = choose_initial_template(tavily_results, role_type)
    
    # 3. Prepare data for the template (NOTE: recipient_name is not needed by the AI anymore)
    recipient_data = {
        'Company': company_name,
        'Title': recipient_title
    }
    sender_data = {
        'name': config.YOUR_NAME,
        'degree': config.YOUR_DEGREE,
        'key_skills': config.YOUR_KEY_SKILLS,
        'project_experience': config.YOUR_PROJECT_EXPERIENCE,
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

    # 6. Validate quality
    quality_report = validate_email_quality(f"Subject: {subject_line}\n\n{final_email_body}", resume_text)

    # 7. Prepare result with the finalized content
    result = {
        "email_subject": subject_line,
        "email_content": final_email_body, # Return the final, processed body
        "template_used": template_name,
        "resume_choice": resume_choice,
        "quality_score": quality_report.get("overall_score", 0),
        "recommendations": quality_report.get("improvements", []),
        "strengths": quality_report.get("strengths", [])
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