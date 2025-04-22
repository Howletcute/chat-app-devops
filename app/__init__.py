# app/__init__.py
import os
import logging
import redis
import datetime # Ensure datetime is imported if used elsewhere (like in auth.py)
import sys # Added for fallback import path manipulation

# --- ADD THESE IMPORTS ---
from pythonjsonlogger import jsonlogger
# --- END ADD ---

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_socketio import SocketIO
from flask_mail import Mail

# Assuming config.py is in the parent directory (project root)
try:
    from config import config_by_name
except ImportError:
    # Fallback if run directly in a way that messes up relative path
    sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
    from config import config_by_name


# --- Initialize Extensions Globally ---
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'info' # For flashing messages
socketio = SocketIO()
redis_client = None # Global placeholder
mail = Mail()


# --- Application Factory ---
def create_app(config_name=None):
    """Creates and configures the Flask application instance."""
    if config_name is None:
        config_name = os.getenv('FLASK_CONFIG', 'default')

    app = Flask(__name__,
                template_folder='../templates',
                static_folder='../static')
    app.config.from_object(config_by_name[config_name]) # Load chosen config

    # --- REPLACE Existing Logging Config with this ---
    log_level = app.config.get('LOGGING_LEVEL', logging.INFO)

    # Get the root logger
    logger = logging.getLogger()
    logger.setLevel(log_level)

    # Remove existing handlers from the root logger to avoid duplicate messages
    # Important if running with Flask's default config or Werkzeug adds handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    # Configure JSON logging handler to stdout
    logHandler = logging.StreamHandler(sys.stdout)
    formatter = jsonlogger.JsonFormatter(
        fmt='%(asctime)s %(levelname)s %(name)s %(message)s %(pathname)s %(lineno)d',
        datefmt='%Y-%m-%dT%H:%M:%S%z' # ISO 8601 format
    )
    logHandler.setFormatter(formatter)

    # Add the JSON handler to the root logger
    logger.addHandler(logHandler)

    # Set Flask app's logger level too (it will use the root handlers by default)
    app.logger.setLevel(log_level)
    # Optional: uncomment below if you DON'T want app.logger messages showing up
    # app.logger.propagate = False

    logger.info("Root logger configured for JSON output.") # Log confirmation
    # --- END LOGGING CONFIGURATION ---


    # --- Initialize Extensions ---
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    mail.init_app(app)
    socketio_redis_url = app.config.get('REDIS_URL')
    socketio.init_app(app,
                      async_mode='eventlet',
                      message_queue=socketio_redis_url,
                      manage_session=False)

    # --- Initialize App Redis Client ---
    global redis_client
    try:
        redis_app_url = app.config.get('REDIS_APP_DB_URL', app.config.get('REDIS_URL'))
        if redis_app_url:
             if redis_app_url.endswith('/0'):
                  redis_app_url_db1 = redis_app_url[:-1] + '1'
             elif '/' not in redis_app_url.split('://')[-1].split(':')[-1]:
                  redis_app_url_db1 = redis_app_url + '/1'
             elif '/' in redis_app_url.split('://')[-1] and not redis_app_url.endswith('/0'):
                 redis_app_url_db1 = redis_app_url
             else:
                 redis_app_url_db1 = redis_app_url + '/1'

             redis_client = redis.Redis.from_url(redis_app_url_db1, decode_responses=True)
             redis_client.ping()
             logging.info(f"Connected to App Redis DB ({redis_app_url_db1}) successfully!") # Will use root logger now
        else:
             logging.error("REDIS_URL or REDIS_APP_DB_URL not found in config.") # Will use root logger now
             redis_client = None
    except redis.exceptions.ConnectionError as e:
        logging.error(f"Could not connect to App Redis DB: {e}") # Will use root logger now
        redis_client = None
    except Exception as e:
        logging.error(f"Error initializing App Redis client: {e}") # Will use root logger now
        redis_client = None


    # --- Register Blueprints (AFTER extension init) ---
    from .auth import auth as auth_blueprint
    app.register_blueprint(auth_blueprint, url_prefix='/auth')

    from .main import main as main_blueprint
    app.register_blueprint(main_blueprint, url_prefix='/')


    # --- Import SocketIO event handlers (AFTER socketio init) ---
    from . import events

    # --- Return App Instance ---
    return app

# --- User Loader Callback ---
from .models import User # Import User model

@login_manager.user_loader
def load_user(user_id):
    """Loads user object from ID stored in session cookie."""
    try:
        return db.session.get(User, int(user_id))
    except Exception as e:
        logging.error(f"Error loading user {user_id}: {e}") # Will use root logger now
        return None