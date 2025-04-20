# app/auth.py
import logging
import datetime # <-- Added import
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from itsdangerous import URLSafeTimedSerializer # <-- Added import
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash
# Import necessary components from the app package
from . import db, mail # <-- Added mail import
from .models import User
from .forms import LoginForm, RegistrationForm
# Import Message from Flask-Mail for sending later
from flask_mail import Message # <-- Added import

# Create Blueprint instance named 'auth'
auth = Blueprint('auth', __name__)


# --- HELPER FUNCTIONS (for Token Generation/Confirmation) ---
def generate_confirmation_token(email):
    serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    # Use a salt to distinguish this token type (important!)
    return serializer.dumps(email, salt='email-confirmation-salt')

def confirm_token(token, expiration=3600): # expiration in seconds (1 hour default)
    serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    try:
        email = serializer.loads(
            token,
            salt='email-confirmation-salt', # Must match the salt used in generation
            max_age=expiration
        )
    # SignatureExpired and BadSignature inherit from Exception, 
    # but catching them specifically can be useful for logging/debugging
    except Exception as e: 
        logging.warning(f"Confirm token failed: {e}")
        return False
    return email
# --- END HELPER FUNCTIONS ---


@auth.route('/register', methods=['GET', 'POST'])
def register():
    """Handles user registration."""
    if current_user.is_authenticated:
        # Redirect to main chat view if already logged in
        return redirect(url_for('main.chat')) 
    form = RegistrationForm()
    if form.validate_on_submit():
        try:
            # Check if username or email already exists
            existing_user = db.session.scalar(db.select(User).where(
                (User.username == form.username.data) | (User.email == form.email.data)
            ))
            if existing_user:
                 if existing_user.username == form.username.data:
                    flash('Username already exists. Please choose another.', 'warning')
                 else: # Must be email
                    flash('Email already registered. Please use a different one or login.', 'warning')
                 # Re-render form with validation errors or flash message
                 return render_template('register.html', title='Register', form=form)

            # Create new user instance (email_confirmed defaults to False from model)
            user = User(username=form.username.data, email=form.email.data)
            user.set_password(form.password.data) # Hashes password
            
            db.session.add(user)
            db.session.commit() # Commit user to DB first

             #  --- Generate Token & Send Email ---
            token = generate_confirmation_token(user.email)
            confirm_url = url_for('auth.confirm_email', token=token, _external=True)
            
            # Prepare email content using template
            html_body = render_template('auth/confirm_email_template.html', confirm_url=confirm_url) 
            text_body = f"Please click the following link to confirm your email address: {confirm_url}" 
            subject = "Please confirm your email address"

            # --- UNCOMMENT THIS BLOCK (and remove the old print line) ---
            try:
                msg = Message(
                    subject,
                    # Sender address comes from MAIL_DEFAULT_SENDER config
                    sender=current_app.config.get('MAIL_DEFAULT_SENDER'), 
                    recipients=[user.email], # Send to the newly registered user's email
                    body=text_body,          # Plain text version
                    html=html_body           # HTML version from template
                )
                mail.send(msg) # <--- Make sure this line is now active
                flash('A confirmation email has been sent. Please check your inbox.', 'success')
            except Exception as e:
                # Optional: Add the temporary print statement back here if needed for debugging
                # print(f"!!! Error during mail.send: {e}") 
                logging.error(f"Error sending confirmation email to {user.email}: {e}")
                flash('Registration successful, but could not send confirmation email. Please contact support.', 'warning') 
            # --- END EMAIL SENDING BLOCK ---

            # Redirect to login after attempting to send email
            return redirect(url_for('auth.login'))
        
        
        except Exception as e:
            db.session.rollback() # Rollback DB changes on any error during registration/token generation
            logging.error(f"Error during registration for {form.username.data}: {e}")
            flash('An error occurred during registration, please try again.', 'danger')
            # Fall through to render template again if commit fails or other error occurs

    # Render template on GET request or if form validation fails
    return render_template('register.html', title='Register', form=form)


@auth.route('/login', methods=['GET', 'POST'])
def login():
    """Handles user login."""
    if current_user.is_authenticated:
        return redirect(url_for('main.chat'))

    form = LoginForm()
    if form.validate_on_submit():
        user = db.session.scalar(db.select(User).where(User.username == form.username.data))

        # Check if user exists and password matches hash
        if user and user.check_password(form.password.data):

            # --- ADD THIS CHECK ---
            if user.email_confirmed:
                # Email is confirmed, proceed with login
                login_user(user, remember=form.remember_me.data)
                flash('Login successful!', 'success')
                
                next_page = request.args.get('next')
                if next_page and next_page.startswith('/'):
                    return redirect(next_page)
                else:
                    return redirect(url_for('main.chat'))
            else:
                # Email not confirmed
                flash('Your email address has not been confirmed. Please check your inbox for the confirmation link.', 'warning')
                # No login_user() call here, redirect back to login page or another relevant page
                return redirect(url_for('auth.login')) 
            # --- END ADDED CHECK ---

        else: # User not found or password incorrect
            flash('Login unsuccessful. Please check username and password.', 'danger')
            # Fall through to re-render login form
            
    # Render login template
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


@auth.route('/confirm/<token>')
def confirm_email(token):
    """Handles the email confirmation link."""
    try:
        email = confirm_token(token) # Verify token validity and expiration
        if not email:
            flash('The confirmation link is invalid or has expired.', 'danger')
            # Redirect to a relevant page, maybe index or registration
            return redirect(url_for('main.index')) 

        user = db.session.scalar(db.select(User).where(User.email == email))

        if not user:
             # This shouldn't happen if token is valid, but check anyway
             flash('User associated with this token not found.', 'warning')
             return redirect(url_for('main.index'))

        if user.email_confirmed:
            flash('Account already confirmed. Please login.', 'success')
        else:
            # Update user status
            user.email_confirmed = True
            user.email_confirmed_on = datetime.datetime.now() # Record confirmation time
            db.session.commit()
            flash('You have confirmed your account. Thanks!', 'success')
            # Optional: Log the user in automatically after confirmation
            # login_user(user) 
            # return redirect(url_for('main.chat'))

    except Exception as e: # Catch potential DB errors during commit
        db.session.rollback()
        logging.error(f"Error during email confirmation commit for token {token}: {e}")
        flash('An error occurred during confirmation. Please try again later.', 'danger')
        return redirect(url_for('main.index'))
        
    # Redirect to login page after successful confirmation or if already confirmed
    return redirect(url_for('auth.login'))