import os
from cryptography.fernet import Fernet
from dotenv import load_dotenv

# Load environment variables from .env file
#load_dotenv()

class CryptoManager:
    """
    A helper class to handle encryption and decryption of sensitive strings
    (like passwords, API keys, etc.) using Fernet symmetric encryption.
    """

    def __init__(self, secret_key: str = None):
        """
        Initialize CryptoManager with a secret key.
        If not provided, tries to load from environment variable SECRET_KEY.
        """
        self.secret_key = secret_key or os.getenv("SECRET_KEY")
        if not self.secret_key:
            raise ValueError("SECRET_KEY not found. Please generate and set it in .env file.")
        self.fernet = Fernet(self.secret_key.encode())

    # -------------------------------------------------------------------------
    def generate_key(self) -> str:
        """
        Generates a new secret key for encryption/decryption.
        Use this only once, and store the result in your .env file as SECRET_KEY.
        """
        key = Fernet.generate_key()
        print("\n✅ Your new SECRET_KEY (copy this to your .env file):")
        print(key.decode())
        print("\nExample to add in .env file:")
        print(f'SECRET_KEY="{key.decode()}"')
        return key.decode()

    # -------------------------------------------------------------------------
    def encrypt(self, plain_text: str) -> str:
        """
        Encrypts plain text (e.g., Gmail password) and returns the encrypted string.
        This encrypted value can safely be stored in your .env or DB.
        """
        if not plain_text:
            raise ValueError("Cannot encrypt empty string.")
        encrypted = self.fernet.encrypt(plain_text.encode())
        return encrypted.decode()

    # -------------------------------------------------------------------------
    def decrypt(self, encrypted_text: str) -> str:
        """
        Decrypts an encrypted string (produced by encrypt()) and returns the original plain text.
        """
        if not encrypted_text:
            raise ValueError("Cannot decrypt empty string.")
        decrypted = self.fernet.decrypt(encrypted_text.encode())
        return decrypted.decode()



# Initialize using SECRET_KEY from .env
crypto = CryptoManager()

# ----------------------- Generate Key (first time only) -----------------------
# print("Your new secret key:", crypto.generate_key())

# ----------------------- Encrypt a string -----------------------
#encrypted_pass = crypto.encrypt("your_gmail_app_password")
#encrypted_pass = crypto.encrypt("admin:1qaz!QAZ")
#print("Encrypted password:", encrypted_pass)

# ----------------------- Decrypt it back -----------------------
#os.getenv("RTSP_CREDENTIALS")
#decrypted_pass = crypto.decrypt(os.getenv("RTSP_CREDENTIALS"))
#print("Decrypted password:", decrypted_pass)


