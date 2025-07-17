import os
from dotenv import load_dotenv

# Load environment variables once at module import time
# Load .env first (defaults), then .env.local (overrides)
load_dotenv('.env')
load_dotenv('.env.local', override=True)

def load_env(KEY_NAME):
    """
    Load a value from environment variables.
    .env contains default values, .env.local contains overrides.
    Environment files are loaded once when this module is imported.
    """
    value = os.getenv(KEY_NAME)
    
    if not value:
        raise ValueError(f"Environment variable '{KEY_NAME}' not found in .env or .env.local files.")
    
    return value
