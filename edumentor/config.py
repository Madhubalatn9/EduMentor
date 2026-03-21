import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'edumentor-dev-secret-key')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///edumentor.db')
    if SQLALCHEMY_DATABASE_URI and SQLALCHEMY_DATABASE_URI.startswith("postgres://"):
        SQLALCHEMY_DATABASE_URI = SQLALCHEMY_DATABASE_URI.replace("postgres://", "postgresql://", 1)
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SUPABASE_URL = os.environ.get('SUPABASE_URL', '')
    SUPABASE_KEY = os.environ.get('SUPABASE_KEY', '')
    GROQ_API_KEY = os.environ.get('GROQ_API_KEY', '')
    JUDGE0_API_KEY = os.environ.get('JUDGE0_API_KEY', '')
    JUDGE0_URL = 'https://judge0-ce.p.rapidapi.com'
    GROQ_MODEL = 'llama-3.3-70b-versatile'   # Free & powerful
