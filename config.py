import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")
    DEBUG = os.getenv("DEBUG", "false").lower() == "true"
    LANGCHAIN_TRACING_V2 = os.getenv("LANGCHAIN_TRACING_V2", "false")
    LANGCHAIN_API_KEY = os.getenv("LANGCHAIN_API_KEY")
    LANGCHAIN_PROJECT = os.getenv("LANGCHAIN_PROJECT", "Synapse-X")
    
    SCHEDULER_ALPHA = float(os.getenv("SCHEDULER_ALPHA", "0.4"))
    SCHEDULER_BETA = float(os.getenv("SCHEDULER_BETA", "0.3"))
    SCHEDULER_GAMMA = float(os.getenv("SCHEDULER_GAMMA", "0.2"))
    SCHEDULER_DELTA = float(os.getenv("SCHEDULER_DELTA", "0.1"))
    DEFAULT_MAX_COST = float(os.getenv("DEFAULT_MAX_COST", "1.0"))
    DEFAULT_MAX_RUNTIME = float(os.getenv("DEFAULT_MAX_RUNTIME", "120"))
    DEFAULT_MAX_LLM_CALLS = int(os.getenv("DEFAULT_MAX_LLM_CALLS", "20"))
    
config = Config()
