
import os
from dotenv import load_dotenv
def load_environment(ENV_FILE_PATH: str):
    """
    Load environment variables from a .env file if not running inside Docker.

    Args:
        ENV_FILE_PATH (str): Path to the .env file (e.g., "data/.env")
    """

    app_dir = os.path.dirname(os.path.abspath(__file__))

    # ✅ construct absolute path to .env.webapp
    env_path = os.path.join(app_dir, ENV_FILE_PATH) #"../data/.env.webapp")

    # ✅ normalize to absolute path
    env_path = os.path.abspath(env_path)
    # Check if running inside Docker
    is_docker = os.path.exists("/.dockerenv")

    if not is_docker:
        # Running locally → manually load env file
        if os.path.exists(env_path):
            load_dotenv(dotenv_path=env_path)
            print(f"✅ Loaded environment variables from {ENV_FILE_PATH}")
        else:
            print(f"⚠️ Warning: {ENV_FILE_PATH} not found. Using system environment vars.")
    else:
        print("🐳 Running inside Docker — relying on Docker environment variables.")
