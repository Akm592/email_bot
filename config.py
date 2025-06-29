# config.py
import os
import dotenv

dotenv.load_dotenv()

# Google Sheet Configuration
SPREADSHEET_ID = os.getenv('SPREADSHEET_ID') # IMPORTANT: Replace with your actual Google Sheet ID
RANGE_NAME = os.getenv('RANGE_NAME') # Adjust based on your sheet columns

# Email Configuration
SENDER_EMAIL = os.getenv('SENDER_EMAIL') # IMPORTANT: Replace with your actual sender email

# Gemini API Configuration
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY') # IMPORTANT: Replace with your actual Gemini API Key

TAVILY_API_KEY = os.getenv('TAVILY_API_KEY') # IMPORTANT: Replace with your actual Tavily API Key

# Resume Paths
# CSV_FILE = "contacts.csv"
AI_ML_RESUME = "resumes/Resume_Ashish.pdf"
FULLSTACK_RESUME = "resumes/Ashish_Resume.pdf"
# Data File Paths
CSV_FILE = "data/emails.csv"


# Your Personal Details for Email Templates
YOUR_NAME = "Ashish Kumar Mishra"
YOUR_DEGREE = "B.Tech in Information Technology"
YOUR_KEY_SKILLS = "AI, Machine Learning, Fullstack Development, Data Science"
YOUR_PROJECT_EXPERIENCE = "built an AI platform that boosted processing speed by 3.5x and cut semantic search latency by 60%"
