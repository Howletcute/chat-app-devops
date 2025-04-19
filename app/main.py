# app/main.py
from flask import Blueprint, render_template, redirect, url_for, flash, session
# Import login utilities required for protecting routes and getting user info
from flask_login import login_required, current_user

# Create Blueprint instance named 'main'
main = Blueprint('main', __name__)

@main.route('/')
@main.route('/index') # Allow access via / or /index
def index():
    """Serves landing page. Content depends on login status (handled in template)."""
    return render_template('index.html', title='Welcome')

@main.route('/chat')
@login_required # User MUST be logged in to access this route
def chat():
    """Serves the main chat page for authenticated users."""
    # The @login_required decorator ensures current_user is populated.
    # We pass the username to the template for display purposes.
    return render_template('chat.html', nickname=current_user.username)

# Note: The previous POST route for '/chat' (which handled the old nickname form)
# is no longer needed because login/authentication now handles user identity.