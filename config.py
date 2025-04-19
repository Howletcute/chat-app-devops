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