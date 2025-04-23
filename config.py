import os

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'default_secret_key')
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'sqlite:///users.db')  
    SQLALCHEMY_TRACK_MODIFICATIONS = False  # Disable warning messages

    MAIL_SERVER = os.getenv("MAIL_SERVER")
    MAIL_PORT = int(os.getenv("MAIL_PORT"))
    MAIL_USE_TLS = os.getenv("MAIL_USE_TLS") == "True"
    MAIL_USERNAME = os.getenv("MAIL_USERNAME")
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD")
    MAIL_DEFAULT_SENDER = os.getenv("MAIL_DEFAULT_SENDER")


# IMPORTANT

# ✅ MAIL_USERNAME
# This is the email address used to log in to the SMTP server (Gmail in your case).

# It is used behind the scenes to authenticate and send emails through Gmail's servers.

# Think of it like:
# 🔐 "Who is sending this email via SMTP (server authentication)?"

# ✅ MAIL_DEFAULT_SENDER
# This is the "From" address that appears in the email seen by the receiver.

# If not explicitly set in the Message(...), this will be used as the sender address.

# Think of it like:
# ✉️ "Who does the receiver see this email is coming from?"
