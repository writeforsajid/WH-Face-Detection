from cryptography.fernet import Fernet

def generate_secret_key():
    """
    Generates a secure random Fernet key and prints it.
    Copy this key and store it in your .env file as SECRET_KEY.
    """
    key = Fernet.generate_key()
    print("\n✅ Your new SECRET_KEY (copy this to your .env file):")
    print(key.decode())
    print("\nExample to add in .env file:")
    print(f'SECRET_KEY="{key.decode()}"')

if __name__ == "__main__":
    generate_secret_key()
