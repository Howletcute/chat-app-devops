# app/main.py
import logging # Added logging import just in case
from flask import Blueprint, render_template, redirect, url_for, flash, session
# Import login utilities required for protecting routes and getting user info
from flask_login import login_required, current_user

# Create Blueprint instance named 'main'
main = Blueprint('main', __name__)

@main.route('/')
@main.route('/index') # Allow access via / or /index
def index():
    """Serves landing page. Content depends on login status (handled in template)."""
    # Renders templates/index.html
    return render_template('index.html', title='Welcome')

@main.route('/chat')
@login_required # User MUST be logged in to access this route
def chat():
    """Serves the main chat page for authenticated users."""
    # The @login_required decorator ensures current_user is populated.

    # --- ADDED THIS LINE ---
    # Fetch the user's saved color from the DB user object, default to black if None
    current_color = current_user.nickname_color or '#000000'
    logging.debug(f"Loading chat for {current_user.username}, color: {current_color}") # Optional debug log

    # Pass username AND current_color to the template
    return render_template('chat.html',
                           nickname=current_user.username,
                           current_color=current_color) # <-- Pass color here
@main.route('/settings', methods=['GET']) # Only GET needed for now
@login_required
def settings():
    """Displays user settings page."""
    # Fetch current color to display in the picker
    current_color = current_user.nickname_color or '#000000'
    return render_template('settings.html',
                           title='User Settings',
                           current_color=current_color)

# Note: The previous POST route for '/chat' (which handled the old nickname form)
# is no longer needed because login/authentication now handles user identity.