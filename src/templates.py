# src/templates.py

# This signature block will be appended by the generation function
SIGNATURE = """
<br><br>
Best regards,<br>
Ashish Kumar Mishra<br><br>
<b>Phone:</b> 9579690648<br>
<b>LinkedIn:</b> <a href="https://www.linkedin.com/in/ashishkumarmishra952/">ashishkumarmishra952</a><br>
<b>Portfolio:</b> <a href="https://www.ashishmishra.site/">ashishmishra.site</a><br>
<b>GitHub:</b> <a href="https://github.com/Akm592">Akm592</a>
"""

# --- NEW ROLE-SPECIFIC EMAIL TEMPLATES ---
EMAIL_TEMPLATES = {
    # --- Fullstack/Frontend Role Templates ---
    "fullstack_quick_question": """
Subject: Quick question about {role_type} positions at {company_name}

<p>Hello {recipient_name},</p>
<p>My name is Ashish Kumar Mishra, a recent B.Tech IT graduate and passionate full-stack developer. I admire the innovative projects at {company_name}, and I’m interested in any {role_type} opportunities on your team.</p>
<p>In my recent project CodeQuest101 (an interactive learning platform), I developed a React/D3.js interface that increased user engagement by 40%. I believe I could bring that same dedication and skill set to {company_name}.</p>
<p>Could you kindly direct me to the person who handles {role_type} hiring, or let me know the best way to apply? I’d be grateful for any guidance or a brief chat about how I can contribute to your team.</p>
""",
    "fullstack_metric_driven": """
Subject: Boosted web app performance by {metric}% — idea for {company_name}

<p>Hello {recipient_name},</p>
<p>I’m Ashish, a full-stack developer (React/Node) and recent IT graduate. For a recent project, Real-Time Chat App, I optimized the MERN stack to support over 1K concurrent users with sub-20ms latency, effectively reducing load times by {metric}%.</p>
<p>Seeing that {company_name} values high-performance web solutions, I believe this result-driven approach could benefit your team.</p>
<p>I would love to schedule a brief call to discuss how my experience could drive similar improvements at {company_name}.</p>
""",
    "fullstack_story": """
Subject: How a hackathon challenge led to a {metric}% engagement boost

<p>Hello {recipient_name},</p>
<p>At a college hackathon, a teammate stepped away from our project, and I volunteered to develop the front end. I built the CodeQuest101 React/D3.js interface from scratch, and our platform saw a {metric}% increase in student engagement. This experience showed me how quickly I can adapt and deliver results under pressure.</p>
<p>I’m excited about the possibility of bringing this problem-solving mindset to {company_name}'s {role_type} team. Could we set up a short meeting to talk about how my full-stack expertise can contribute to {company_name}? I appreciate your consideration and hope to connect soon.</p>
""",
    "fullstack_curiosity": """
Subject: {recipient_name}, curious how interactive UI can boost engagement?

<p>Hello {recipient_name},</p>
<p>Have you ever wondered how interactive user interfaces can transform learning experiences? At CodeQuest101, I created a dynamic React + D3 visualization for complex CS concepts, resulting in a 50% increase in time students spent on the platform.</p>
<p>Given {company_name}’s commitment to innovation, I’m curious if you’re exploring similar front-end solutions. I’d love to share more about how these techniques could benefit your team—perhaps in a brief demo or call.</p>
""",
    "fullstack_direct_bullets": """
Subject: Full-stack impact in 3 bullet points

<p>Hello {recipient_name},</p>
<p>I’ll get straight to the point – here are three highlights of my full-stack experience:</p>
<ul>
    <li><b>CodeQuest101 (React/D3):</b> Increased user engagement by 40% through interactive visualizations.</li>
    <li><b>Real-Time Chat App (MERN):</b> Scaled to 1K+ concurrent users with <20ms latency.</li>
    <li><b>Personal Portfolio (Next.js):</b> Reduced page load time by 30% via optimized code and caching.</li>
</ul>
<p>I’m passionate about building high-performance web apps, and I’d love to bring these skills to {company_name}. Can we schedule a quick chat to discuss how I can contribute to your {role_type} team?</p>
""",

    # --- AI/ML/Data Role Templates ---
    "ai_metric_driven": """
Subject: Improved NLP accuracy by {metric}% — idea for {company_name}'s AI team

<p>Hello {recipient_name},</p>
<p>I’m Ashish Kumar Mishra, a data enthusiast and recent B.Tech graduate specializing in AI/ML. In my Intelligent Research Nexus (IRN) project, I implemented a LangChain-based document analysis pipeline, improving retrieval accuracy by {metric}%.</p>
<p>I understand {company_name} values data-driven innovation, and I’m confident that this result-driven approach can advance your AI initiatives.</p>
<p>I’d welcome the chance to discuss how my experience could be applied at {company_name}—perhaps in a brief call.</p>
""",
    "ai_quick_question": """
Subject: Quick question about {role_type} roles at {company_name}

<p>Hello {recipient_name},</p>
<p>I hope you’re well. My name is Ashish and I’m exploring AI/ML opportunities as a new graduate. I recently completed a project called Reddit NLP Tracker, where I built a sentiment analysis pipeline on social media comments, achieving around 90% accuracy.</p>
<p>I noticed that {company_name} tackles interesting data challenges, and I’m keen to learn if there are {role_type} openings on your team. Could you point me to the right person, or let me know the best way to apply?</p>
""",
    "ai_story": """
Subject: My journey from 2048 game bot to data science graduate

<p>Hello {recipient_name},</p>
<p>As a fun challenge during my studies, I built an AI bot to play the game 2048 using Deep Q-Learning. The bot reached the 95th percentile performance in over 10K simulated games. That project fueled my passion for machine learning, leading me to more advanced work like the IRN document analysis tool.</p>
<p>Now as a graduate, I’m excited to apply this hands-on experience at {company_name}. Could we connect for a quick chat about how my skills might fit your AI/ML team?</p>
""",
    "ai_curiosity": """
Subject: {recipient_name}, have you tried leveraging LLMs for data insights?

<p>Hello {recipient_name},</p>
<p>Have you explored using large language models for enhanced data analysis? In my latest project, IRN, I used GPT and LangChain to summarize research papers, cutting information processing time by 50%.</p>
<p>Given {company_name}’s focus on innovation, I thought this approach might be relevant. If you’re curious, I’d love to demo the tool I built or discuss how these techniques could assist {company_name}. Would you be available for a brief conversation or portfolio review?</p>
""",
    "ai_direct_bullets": """
Subject: 3 AI/ML highlights: IRN, 95% accuracy, {metric}X speedup

<p>Hello {recipient_name},</p>
<p>Three quick facts about my AI/ML work:</p>
<ul>
    <li><b>Intelligent Research Nexus (IRN):</b> Built an AI pipeline using RAG and LangChain, reducing research time by {metric}%.</li>
    <li><b>Reddit NLP Tracker:</b> Developed a sentiment analysis model achieving 95% accuracy.</li>
    <li><b>2048 Game Bot:</b> Created a deep learning agent reaching the 95th percentile in performance over 10K games.</li>
</ul>
<p>I’m confident these skills can drive results at {company_name}. Would you have time for a short call to discuss how I can contribute to your {role_type} team’s success?</p>
"""
}


# --- FOLLOW-UP TEMPLATES (Unchanged) ---
FOLLOWUP_TEMPLATES = {
    "first_followup": f"""
Subject: Following up on {{Company}} opportunity

<p>Dear {{recipient_name_placeholder}},</p><p>I hope you're having a great week. I'm writing to follow up on my previous email regarding my interest in {{Company}}.</p><p>{{personalized_line_based_on_research}}</p><p>I'm still very excited about the possibility of contributing to your team.</p>{SIGNATURE}
""",

    "value_add_followup": f"""
Subject: Thought you'd find this interesting - {{relevant_topic}}

<p>Hi {{recipient_name_placeholder}},</p>
<p>I came across {{relevant_article_or_trend}} and thought it might interest you given {{company_name}}'s work in {{company_focus_area}}.</p>
<p>This relates to my experience with {{relevant_project}} where I {{relevant_achievement}}. Still excited about the {{role_type}} opportunity we discussed.</p>
{SIGNATURE}
""",

    "final_followup": f"""
Subject: Final note - {{role_type}} timeline

<p>Hi {{recipient_name_placeholder}},</p>
<p>As I complete my final semester preparations, I wanted to reach out one last time about the {{role_type}} position.</p>
<p>My graduation timeline of {{graduation_date}} means I'm actively finalizing my career path. {{company_name}} remains my top choice because of {{specific_company_reason}}.</p>
<p>If the timing isn't right now, I'd appreciate staying connected for future opportunities.</p>
{SIGNATURE}
"""
}


ALL_TEMPLATES = {
    'initial': EMAIL_TEMPLATES,
    'followup': FOLLOWUP_TEMPLATES
}

def get_template(template_type: str, template_name: str) -> str:
    """
    Retrieves a template by type and name.
    """
    try:
        return ALL_TEMPLATES[template_type][template_name]
    except KeyError as e:
        raise ValueError(f"Template not found for type '{template_type}' and name '{template_name}'") from e
