
import os
from dotenv import load_dotenv
def load_environment(ENV_FILE_PATH: str):
    """
    Load environment variables from a .env file if not running inside Docker.

    Args:
        ENV_FILE_PATH (str): Path to the .env file (e.g., "data/.env")
    """
    # Check if running inside Docker
    is_docker = os.path.exists("/.dockerenv")

    if not is_docker:
        # Running locally → manually load env file
        if os.path.exists(ENV_FILE_PATH):
            load_dotenv(dotenv_path=ENV_FILE_PATH)
            print(f"✅ Loaded environment variables from {ENV_FILE_PATH}")
        else:
            print(f"⚠️ Warning: {ENV_FILE_PATH} not found. Using system environment vars.")
    else:
        print("🐳 Running inside Docker — relying on Docker environment variables.")
