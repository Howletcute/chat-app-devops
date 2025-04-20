# config.py
import os
import logging
from dotenv import load_dotenv

# Load .env file variables into environment
basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))

class Config:
    """Base configuration."""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-should-really-set-a-secret-key'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    LOGGING_LEVEL = logging.INFO # Default logging level

    # Redis Config (can be overridden)
    REDIS_HOST = os.environ.get('REDIS_HOST', 'localhost')
    REDIS_PORT = int(os.environ.get('REDIS_PORT', 6379))
    REDIS_URL = f"redis://{REDIS_HOST}:{REDIS_PORT}/0" # For SocketIO queue
    REDIS_APP_DB_URL = f"redis://{REDIS_HOST}:{REDIS_PORT}/1" # For App data (e.g., online users)

    # Database Config (can be overridden)
    DB_USER = os.environ.get('DB_USER', 'postgres')
    DB_PASS = os.environ.get('DB_PASS', 'postgres')
    DB_HOST = os.environ.get('DB_HOST', 'localhost')
    DB_NAME = os.environ.get('DB_NAME', 'chat_db')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}/{DB_NAME}"
    
    # --- NEW: Flask-Mail Configuration for SendGrid ---
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.sendgrid.net')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() in ['true', 'on', '1']
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME', 'apikey') # SendGrid uses 'apikey' literally
    MAIL_PASSWORD = os.environ.get('SENDGRID_API_KEY') # Use a specific env var name
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER', 'noreply@yourdomain.com') # IMPORTANT: Use an email address from a domain you configure/verify in SendGrid

class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    LOGGING_LEVEL = logging.DEBUG

class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False
    # SECRET_KEY should DEFINITELY be set via environment variable in production
    # SQLALCHEMY_DATABASE_URI should also come from environment vars/secrets

# Dictionary to easily access configs by name
config_by_name = dict(
    dev=DevelopmentConfig,
    prod=ProductionConfig,
    default=DevelopmentConfig
)

# Helper to get the secret key
key = Config.SECRET_KEY