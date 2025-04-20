# app/__init__.py
import os
import logging
import redis
import datetime # Ensure datetime is imported if used elsewhere (like in auth.py)
import sys # Added for fallback import path manipulation
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
# Create extension instances without passing app object yet
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
# Point login_view to the login route *within the auth blueprint*
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'info' # For flashing messages
# SocketIO instance created globally
socketio = SocketIO()
# Global placeholder for app-specific Redis client (connected inside factory)
redis_client = None
# Mail instance created globally
mail = Mail()


# --- Application Factory ---
def create_app(config_name=None):
    """Creates and configures the Flask application instance."""
    if config_name is None:
        # Use environment variable or default to 'dev' (DevelopmentConfig)
        config_name = os.getenv('FLASK_CONFIG', 'default') 

    # Need to tell Flask where templates/static are relative to the app package path
    # Go up one level from app/ to the project root
    app = Flask(__name__,
                template_folder='../templates',
                static_folder='../static')
    app.config.from_object(config_by_name[config_name]) # Load chosen config

    # Initialize extensions with the created app instance
    db.init_app(app)
    migrate.init_app(app, db) # Migrate needs both app and db
    login_manager.init_app(app)
    mail.init_app(app) # Initialize Mail

    # Initialize SocketIO, getting Redis URL from app config
    # Pass manage_session=False because Flask-Login handles user sessions
    socketio_redis_url = app.config.get('REDIS_URL')
    socketio.init_app(app,
                      async_mode='eventlet',
                      message_queue=socketio_redis_url,
                      manage_session=False)

    # --- Initialize App Redis Client (using different DB index) ---
    # Initialize inside factory to ensure config is loaded
    global redis_client
    try:
        # Use REDIS_APP_DB_URL if defined, otherwise fall back to REDIS_URL but change DB index
        redis_app_url = app.config.get('REDIS_APP_DB_URL', app.config.get('REDIS_URL'))
        if redis_app_url:
             # Ensure we use DB index 1 if not specified or if base URL uses 0
             if redis_app_url.endswith('/0'):
                  redis_app_url_db1 = redis_app_url[:-1] + '1'
             # Handle case like redis://host:port without a DB index
             elif '/' not in redis_app_url.split('://')[-1].split(':')[-1]: 
                  redis_app_url_db1 = redis_app_url + '/1'
             # Check if a specific DB index other than 0 is already set
             elif '/' in redis_app_url.split('://')[-1] and not redis_app_url.endswith('/0'):
                 redis_app_url_db1 = redis_app_url # Assume it's already correct (e.g., /1)
             else: # Default case if URL structure is unexpected, try adding /1
                 redis_app_url_db1 = redis_app_url + '/1'


             redis_client = redis.Redis.from_url(redis_app_url_db1, decode_responses=True)
             redis_client.ping() # Check connection
             logging.info(f"Connected to App Redis DB ({redis_app_url_db1}) successfully!")
        else:
             logging.error("REDIS_URL or REDIS_APP_DB_URL not found in config.")
             redis_client = None
    except redis.exceptions.ConnectionError as e:
        logging.error(f"Could not connect to App Redis DB: {e}")
        redis_client = None
    except Exception as e: # Catch other potential redis init errors
        logging.error(f"Error initializing App Redis client: {e}")
        redis_client = None


    # --- Register Blueprints ---
    # ***** Import Blueprints *AFTER* extensions are initialized *****
    
    from .auth import auth as auth_blueprint # Import the auth blueprint instance HERE
    app.register_blueprint(auth_blueprint, url_prefix='/auth') # All auth routes under /auth/

    from .main import main as main_blueprint # Import the main blueprint instance HERE
    app.register_blueprint(main_blueprint, url_prefix='/') # Main routes at root


    # --- Import SocketIO event handlers ---
    # This ensures the @socketio.on decorators are registered. Import AFTER blueprints.
    from . import events 

    # Return the configured app instance
    return app

# --- User Loader Callback for Flask-Login ---
# Needs to be defined after login_manager is created, and import User model
from .models import User # Import User model defined in models.py

@login_manager.user_loader
def load_user(user_id):
    """Loads user object from ID stored in session cookie."""
    try:
        # Use SQLAlchemy's recommended get method for primary key lookup
        return db.session.get(User, int(user_id))
    except Exception as e:
        logging.error(f"Error loading user {user_id}: {e}")
        return None # Return None if user not found or error occurs