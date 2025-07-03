import logging

logger = logging.getLogger(__name__)

TEMPLATES = {
    "initial": {
        # Tier 1: Referral (Highest Performance)
        "referral_introduction": {
            "subject": "Introduction from {referral_name} regarding {Company}",
            "body": """Hi {{recipient_name_placeholder}},

My name is {sender_name}, and I'm writing to you at the suggestion of {referral_name} from {referral_company}. They mentioned you were the best person to connect with regarding opportunities in {role_type} at {Company}.

Based on my research, {Company} is a leader in [mention specific area from Tavily research], which aligns perfectly with my passion and skills in [mention 1-2 key skills from resume]. I was particularly impressed by [mention a specific project or value of the company].

I've attached my resume, which details my experience, including a project where I [mention a key achievement, e.g., 'improved data processing efficiency by 20%'].

I am confident that my background in {role_type} would allow me to contribute significantly to your team. Would you be open to a brief conversation next week?

Best regards,
{sender_name}
{sender_linkedin}
{sender_github}""",
            "performance_tier": "Tier 1: Referral",
            "category": "Referral"
        },

        # Tier 2: Value-First & Research (High Performance)
        "value_proposition": {
            "subject": "A thought on {Company}'s [specific project/product]",
            "body": """Hi {{recipient_name_placeholder}},

My name is {sender_name}, and I've been following {Company}'s innovative work in the industry. Your recent progress on [mention specific project from Tavily research] caught my attention, and it aligns closely with my expertise in {role_type}.

In a recent project, I [mention a quantifiable achievement, e.g., 'developed a full-stack feature that increased user engagement by 15%']. I believe a similar approach could bring significant value to your current initiatives.

I've attached my resume for your review. I'm eager to discuss how my skills could help {Company} achieve its goals.

Best regards,
{sender_name}
{sender_linkedin}
{sender_github}""",
            "performance_tier": "Tier 2: Value-First",
            "category": "Value-First"
        },
        "problem_solution": {
            "subject": "Idea for tackling [relevant challenge] at {Company}",
            "body": """Hi {{recipient_name_placeholder}},

My name is {sender_name}. While researching {Company}, I was thinking about the challenge of [mention a relevant industry problem, e.g., 'optimizing data pipelines for real-time analytics'].

My background in {role_type} has equipped me with the skills to address such problems. For instance, I recently [describe a project where you solved a similar problem], which resulted in [quantifiable outcome].

I am very impressed by {Company}'s approach to innovation and would welcome the opportunity to discuss how I could contribute. My resume is attached.

Best regards,
{sender_name}
{sender_linkedin}
{sender_github}""",
            "performance_tier": "Tier 2: Value-First",
            "category": "Value-First"
        },
        "company_insight": {
            "subject": "Regarding {Company}'s recent achievement",
            "body": """Hi {{recipient_name_placeholder}},

My name is {sender_name}. I was excited to read about {Company}'s recent [mention news or announcement from Tavily research]. It's a testament to your team's expertise and forward-thinking vision.

This development resonates with my own experience in {role_type}, where I've focused on [mention relevant skill or technology]. I believe my background could be a strong asset to your team as you continue to build on this success.

I have attached my resume and would appreciate the chance to discuss this further.

Best regards,
{sender_name}
{sender_linkedin}
{sender_github}""",
            "performance_tier": "Tier 2: Research",
            "category": "Company Research"
        },
        "industry_trend": {
            "subject": "The trend towards [industry trend] and {Company}",
            "body": """Hi {{recipient_name_placeholder}},

My name is {sender_name}. With the growing importance of [mention industry trend], I've been closely following how innovative companies like {Company} are adapting.

My work in {role_type} has given me hands-on experience in this area, including [mention a relevant project or skill]. I'm confident I could help your team stay ahead of the curve.

My resume is attached for your consideration. I look forward to the possibility of connecting.

Best regards,
{sender_name}
{sender_linkedin}
{sender_github}""",
            "performance_tier": "Tier 2: Research",
            "category": "Company Research"
        },

        # Tier 3: Metric-Driven (Solid Performance)
        "fullstack_performance": {
            "subject": "Full-Stack Developer | Performance Optimization",
            "body": """Hi {{recipient_name_placeholder}},

My name is {sender_name}. I am a Full-Stack Developer with a focus on performance. In a past project, I successfully reduced API response times by 40% through strategic code optimization.

I am very interested in opportunities at {Company}. My resume is attached.

Best regards,
{sender_name}
{sender_linkedin}
{sender_github}""",
            "performance_tier": "Tier 3: Metric-Driven",
            "category": "Metric-Driven"
        },
        "ai_accuracy": {
            "subject": "AI/ML Engineer | Model Accuracy Improvement",
            "body": """Hi {{recipient_name_placeholder}},

My name is {sender_name}. As an AI/ML Engineer, I specialize in enhancing model performance. I recently improved a classification model's accuracy from 85% to 92% by implementing advanced feature engineering techniques.

I am drawn to the work being done at {Company}. My resume is attached.

Best regards,
{sender_name}
{sender_linkedin}
{sender_github}""",
            "performance_tier": "Tier 3: Metric-Driven",
            "category": "Metric-Driven"
        },
        "ai_efficiency": {
            "subject": "AI/ML Engineer | Model Efficiency",
            "body": """Hi {{recipient_name_placeholder}},

My name is {sender_name}, an AI/ML Engineer focused on computational efficiency. I recently optimized a deep learning model, reducing its inference time by 60% and memory usage by 45%.

I am excited by the challenges at {Company}. My resume is attached.

Best regards,
{sender_name}
{sender_linkedin}
{sender_github}""",
            "performance_tier": "Tier 3: Metric-Driven",
            "category": "Metric-Driven"
        },
        "fullstack_scalability": {
            "subject": "Full-Stack Developer | Scalable Architectures",
            "body": """Hi {{recipient_name_placeholder}},

My name is {sender_name}. I am a Full-Stack Developer who designs systems for scale. I have architected and deployed applications on AWS that serve over 100,000 daily active users.

I am looking for a new challenge and {Company} is at the top of my list. My resume is attached.

Best regards,
{sender_name}
{sender_linkedin}
{sender_github}""",
            "performance_tier": "Tier 3: Metric-Driven",
            "category": "Metric-Driven"
        },

        # Tier 4: Story-Based (Good Performance)
        "journey_narrative": {
            "subject": "My path to {role_type} and my interest in {Company}",
            "body": """Hi {{recipient_name_placeholder}},

My name is {sender_name}. My journey into {role_type} began with a fascination for [mention a specific interest], which led me to build [mention a personal project]. This experience taught me the power of combining creativity with technical skill to solve meaningful problems.

I see this same spirit in {Company}'s work, especially [mention a company value or project]. I am eager to contribute my passion and skills to your team.

My resume is attached, and I would love to share more about my story.

Best regards,
{sender_name}
{sender_linkedin}
{sender_github}""",
            "performance_tier": "Tier 4: Story-Based",
            "category": "Story-Based"
        },
        "challenge_overcome": {
            "subject": "How a past challenge prepared me for a role at {Company}",
            "body": """Hi {{recipient_name_placeholder}},

My name is {sender_name}. In a recent academic project, we hit a major roadblock with [describe a technical challenge]. I took the lead on architecting a new solution using [mention technology], which not only solved the problem but also improved our results by [quantifiable metric].

This experience reinforced my passion for collaborative problem-solving. I am confident I can bring this same proactive and resilient mindset to {Company}.

My resume is attached. I look forward to hearing from you.

Best regards,
{sender_name}
{sender_linkedin}
{sender_github}""",
            "performance_tier": "Tier 4: Story-Based",
            "category": "Story-Based"
        }
    },
    "follow_up": {
        "polite_check_in": {
            "subject": "Re: {original_subject}",
            "body": """Hi {{recipient_name_placeholder}},

I hope you're having a productive week.

I'm writing to follow up on my previous email regarding a {role_type} position. I'm still very interested in the possibility of joining your team at {Company} and believe my skills in [mention 1-2 key skills] would be a great match.

Would you have a moment to connect in the coming days?

Best regards,
{sender_name}""",
            "performance_tier": "N/A",
            "category": "Follow-Up"
        },
        "value_add": {
            "subject": "Re: {original_subject}",
            "body": """Hi {{recipient_name_placeholder}},

Hope you're well.

I saw the recent news about [mention recent company news or article] and it reminded me of my interest in {Company}. It's exciting to see your progress in this area.

As a quick reminder, my background in {role_type} includes [mention a relevant skill or achievement].

I've re-attached my resume for your convenience.

Best regards,
{sender_name}""",
            "performance_tier": "N/A",
            "category": "Follow-Up"
        }
    }
}

def get_template_performance_tier(template_name: str) -> str:
    """Returns the performance tier of a given template."""
    for template_group in TEMPLATES.values():
        if template_name in template_group:
            return template_group[template_name].get("performance_tier", "Unknown")
    logger.warning(f"Could not find performance tier for template: {template_name}")
    return "Unknown"

def get_template_category(template_name: str) -> str:
    """Returns the category of a given template."""
    for template_group in TEMPLATES.values():
        if template_name in template_group:
            return template_group[template_name].get("category", "Unknown")
    logger.warning(f"Could not find category for template: {template_name}")
    return "Unknown"

def populate_template(template_type: str, template_name: str, recipient_data: dict, sender_data: dict, tavily_results: str, resume_text: str) -> tuple[str, str]:
    """
    Populates a template with dynamic data.
    (This is a simplified placeholder - the real logic is now in the AI prompt of generate_fresher_email)
    """
    try:
        template = TEMPLATES[template_type][template_name]
        subject = template['subject']
        body = template['body']

        # Combine all data sources
        all_data = {**recipient_data, **sender_data}

        # Basic placeholder replacement
        for key, value in all_data.items():
            placeholder = "{" + key + "}"
            # Ensure value is a string before replacing
            str_value = str(value) if value is not None else ""
            subject = subject.replace(placeholder, str_value)
            body = body.replace(placeholder, str_value)

        return subject, body

    except KeyError:
        logger.error(f"Template '{template_name}' not found in type '{template_type}'.")
        return "Error: Template not found", "Could not generate email body because the template was not found."
    except Exception as e:
        logger.error(f"Failed to populate template '{template_name}': {e}")
        return "Error: Generation failed", f"An unexpected error occurred: {e}"