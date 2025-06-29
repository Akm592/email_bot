# src/templates.py

# This signature block will be appended by the generation function
# src/templates.py

# ... (keep your EMAIL_TEMPLATES and FOLLOWUP_TEMPLATES) ...

# --- NEW PROFESSIONAL HTML SIGNATURE ---
SIGNATURE = """
<br><br>
Best regards,<br>
Ashish Kumar Mishra<br><br>
<b>Phone:</b> 9579690648<br>
<b>LinkedIn:</b> <a href="https://www.linkedin.com/in/ashishkumarmishra952/">ashishkumarmishra952</a><br>
<b>Portfolio:</b> <a href="https://www.ashishmishra.site/">ashishmishra.site</a><br>
<b>GitHub:</b> <a href="https://github.com/Akm592">Akm592</a>
"""

EMAIL_TEMPLATES = {
    # Lead with your single most impressive project result.
    "project_showcase": """
Subject: Idea for {company_name}'s {specific_project_or_product}

Hi {recipient_name},

I saw you're hiring for the {role_type} role.

In a recent project, I built an AI platform that boosted processing speed by 3.5x and cut semantic search latency by 60%.

Given your focus on {company's_focus_area}, I believe a similar approach could create significant value for your team.

My resume is attached, and my portfolio has the full project breakdown.

Are you the right person to chat with about this?
""",

    # Directly map one of your skills to a problem the company likely has.
    "skill_to_problem_match": """
Subject: Question about your {a_specific_technical_challenge}

Hi {recipient_name},

Many companies struggle with {common_problem} when scaling their {technology_they_use}.

I recently focused on solving this by designing a RAG pipeline that improved document summarization accuracy by 42%.

If improving {metric_they_care_about} is a priority at {company_name}, I'm confident my skills can help.

My resume is attached for more details. Worth a quick chat?
""",

    # A short, brutally direct email that uses a stat as the hook.
    "brutally_direct_proof": """
Subject: 70% faster deployment times

Hi {recipient_name},

That subject line comes from a CI/CD pipeline I built for an AI microservices project.

I saw the {role_type} role requires deep experience in {specific_skill_from_job_description}. My portfolio and resume (attached) show I've delivered quantifiable results using these exact technologies.

Let me know if this looks like a potential fit.
"""
}

FOLLOWUP_TEMPLATES = {
    "first_followup": """
Subject: Following up on {{Company}} opportunity

<p>Dear {{recipient_name_placeholder}},</p><p>I hope you're having a great week. I'm writing to follow up on my previous email regarding my interest in {{Company}}.</p><p>{{personalized_line_based_on_research}}</p><p>I'm still very excited about the possibility of contributing to your team.</p>    """,
    
    "value_add_followup": """
Subject: Thought you'd find this interesting - {relevant_topic}

Hi {recipient_name},

I came across {relevant_article_or_trend} and thought it might interest you given {company_name}'s work in {company_focus_area}.

This relates to my experience with {relevant_project} where I {relevant_achievement}. Still excited about the {role_type} opportunity we discussed.

Best regards,
Ashish Kumar Mishra
""",
    
    "final_followup": """
Subject: Final note - {role_type} timeline

Hi {recipient_name},

As I complete my final semester preparations, I wanted to reach out one last time about the {role_type} position.

My graduation timeline of {graduation_date} means I'm actively finalizing my career path. {company_name} remains my top choice because of {specific_company_reason}.

If the timing isn't right now, I'd appreciate staying connected for future opportunities.

Best regards,
Ashish Kumar Mishra
"""
}

ALL_TEMPLATES = {
    'initial': EMAIL_TEMPLATES,
    'followup': FOLLOWUP_TEMPLATES
}

def get_template(template_type: str, template_name: str) -> str:
    return ALL_TEMPLATES[template_type][template_name]