# config.py
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def get_required_env(key, display_name=None):
    """Get a required env var, raise clear error if missing or placeholder."""
    value = os.environ.get(key)
    name = display_name or key

    if not value:
        raise ValueError(f"{name} is not set! Copy .env.example to .env and fill in your values.")

    # Check for common placeholder patterns
    placeholder_patterns = [
        "your_", "replace_", "change_this", "xxx", "XXXX",
        "your_username", "your_password", "your_cluster"
    ]
    for pattern in placeholder_patterns:
        if pattern in value.lower():
            raise ValueError(f"{name} has a placeholder value! Copy .env.example to .env and fill in your actual values.")

    return value

# ─── AI API Keys ───
# GROQ_API_KEY = get_required_env("GROQ_API_KEY", "GROQ_API_KEY")
# GROQ_MODEL = "llama-3.1-8b-instant"

OPENAI_API_KEY = get_required_env("OPENAI_API_KEY", "OPENAI_API_KEY")
OLLAMA_MODEL = "gemma4:31b-cloud"

# ─── Database ───
MONGO_URI = get_required_env("MONGO_URI", "MONGO_URI")

# ─── JWT ───
JWT_SECRET_KEY = get_required_env("JWT_SECRET_KEY", "JWT_SECRET_KEY")

# ─── Google OAuth ───
GOOGLE_CLIENT_ID = get_required_env("GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = get_required_env("GOOGLE_CLIENT_SECRET", "GOOGLE_CLIENT_SECRET")

# ─── URLs ───
FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:5173")
