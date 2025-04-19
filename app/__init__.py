# app/__init__.py
import os
import logging
import redis
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_socketio import SocketIO

# Assuming config.py is in the parent directory (project root)
# If run.py is also at root, this relative import might need adjustment later
# depending on how the app is run. For now, assume standard package structure.
try:
    from config import config_by_name
except ImportError:
    # Fallback if run directly in a way that messes up relative path
    import sys
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

# --- Application Factory ---
def create_app(config_name=None):
    """Creates and configures the Flask application instance."""
    if config_name is None:
        config_name = os.getenv('FLASK_CONFIG', 'default') # Use env var or 'default' (dev)

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
        redis_app_url = app.config.get('REDIS_APP_DB_URL', app.config.get('REDIS_URL'))
        if redis_app_url:
             # Ensure we use DB index 1 if not specified in REDIS_APP_DB_URL
             if redis_app_url.endswith('/0'):
                  redis_app_url_db1 = redis_app_url[:-1] + '1'
             elif '/' not in redis_app_url.split('://')[-1]: # Handle case like redis://host:port
                  redis_app_url_db1 = redis_app_url + '/1'
             else: # Assume URL already includes DB or is fine as is
                 redis_app_url_db1 = redis_app_url

             redis_client = redis.Redis.from_url(redis_app_url_db1, decode_responses=True)
             redis_client.ping()
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
    # Import Blueprints *inside* the factory to avoid circular imports
    from .auth import auth as auth_blueprint # Import the auth blueprint instance
    app.register_blueprint(auth_blueprint, url_prefix='/auth') # All auth routes under /auth/

    # Placeholder registration for main blueprint (index, chat routes)
    from .main import main as main_blueprint # We will create app/main.py next
    app.register_blueprint(main_blueprint, url_prefix='/') # Main routes at root


    # --- Import SocketIO event handlers ---
    # This ensures the @socketio.on decorators are registered
    from . import events # We will create app/events.py next

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