# app/auth.py
import logging # Import logging if not already done globally
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash
# Import necessary components from the app package
# The '.' means import from the current package ('app')
from . import db
from .models import User
from .forms import LoginForm, RegistrationForm

# Create Blueprint instance named 'auth'
auth = Blueprint('auth', __name__)

@auth.route('/register', methods=['GET', 'POST'])
def register():
    """Handles user registration."""
    if current_user.is_authenticated:
        return redirect(url_for('main.chat')) # Redirect to main chat view if already logged in
    form = RegistrationForm()
    if form.validate_on_submit(): # Checks CSRF token and basic field validation
        try:
            # Check if username or email already exists in DB (moved from form validator)
            existing_user = db.session.scalar(db.select(User).where(
                (User.username == form.username.data) | (User.email == form.email.data)
            ))
            if existing_user:
                 if existing_user.username == form.username.data:
                      flash('Username already exists. Please choose another.', 'warning')
                 else: # Must be email
                      flash('Email already registered. Please use a different one.', 'warning')
                 # Re-render form with validation errors (if any) or flash message
                 return render_template('register.html', title='Register', form=form)

            # Create new user if checks pass
            user = User(username=form.username.data, email=form.email.data)
            user.set_password(form.password.data) # Hashes password via method in User model
            db.session.add(user)
            db.session.commit()
            flash('Your account has been created! You can now log in.', 'success')
            # Redirect to the login route within THIS blueprint ('auth.login')
            return redirect(url_for('auth.login'))
        except Exception as e:
            db.session.rollback() # Rollback DB changes on error
            logging.error(f"Error during registration commit for {form.username.data}: {e}")
            flash('An error occurred during registration, please try again.', 'danger')
            # Fall through to render template again if commit fails
    # Render template on GET request or if form validation fails
    return render_template('register.html', title='Register', form=form)

@auth.route('/login', methods=['GET', 'POST'])
def login():
    """Handles user login."""
    if current_user.is_authenticated:
        return redirect(url_for('main.chat')) # Redirect to main chat view

    form = LoginForm()
    if form.validate_on_submit():
        user = db.session.scalar(db.select(User).where(User.username == form.username.data))
        # Check if user exists and password matches hash
        if user and user.check_password(form.password.data):
            # Log the user in using Flask-Login
            login_user(user, remember=form.remember_me.data)
            flash('Login successful!', 'success')
            # Redirect to the page user was trying to access before being sent to login,
            # or default to the main chat page.
            next_page = request.args.get('next')
            # Basic check to prevent redirecting to external sites
            if next_page and next_page.startswith('/'):
                return redirect(next_page)
            else:
                # Redirect to the chat route within the 'main' blueprint
                return redirect(url_for('main.chat'))
        else:
            flash('Login unsuccessful. Please check username and password.', 'danger')
            # Fall through to re-render login form
    # Render login template (make sure templates/login.html exists)
    return render_template('login.html', title='Login', form=form)

@auth.route('/logout')
@login_required # User must be logged in to log out
def logout():
    """Logs the user out."""
    username = current_user.username # Get username before session is cleared
    logout_user() # Clears the user session managed by Flask-Login
    flash(f'User {username} has been logged out.', 'info')
    # Redirect to the index route within the 'main' blueprint
    return redirect(url_for('main.index'))