import os
from dotenv import load_dotenv

class Config:
    def __init__(self):
        load_dotenv()
        self.DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
        self.SUPABASE_URL = os.getenv("SUPABASE_URL")
        self.SUPABASE_KEY = os.getenv("SUPABASE_KEY")
        self.GROQ_API_KEY = os.getenv("GROQ_API_KEY")

config = Config()