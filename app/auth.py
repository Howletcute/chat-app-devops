# app/auth.py
import logging
import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from itsdangerous import URLSafeTimedSerializer
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash
from . import db, mail
from .models import User
# Import ALL needed forms, including the new ResendConfirmationForm
from .forms import (LoginForm, RegistrationForm, 
                    ForgotPasswordForm, ResetPasswordForm, 
                    ResendConfirmationForm)
from flask_mail import Message

# Create Blueprint instance named 'auth'
auth = Blueprint('auth', __name__)


# --- HELPER FUNCTIONS (Tokens) ---

def generate_confirmation_token(email):
    serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    return serializer.dumps(email, salt='email-confirmation-salt')

def confirm_token(token, expiration=3600): # 1 hour default
    serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    try:
        email = serializer.loads(token, salt='email-confirmation-salt', max_age=expiration)
    except Exception as e:
        logging.warning(f"Confirm token failed: {e}")
        return False
    return email

def generate_password_reset_token(email):
    serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    return serializer.dumps(email, salt='password-reset-salt') # Different salt

def confirm_password_reset_token(token, expiration=3600): # 1 hour default
    serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    try:
        email = serializer.loads(token, salt='password-reset-salt', max_age=expiration)
    except Exception as e:
        logging.warning(f"Password reset token failed: {e}")
        return False
    return email

# --- ROUTES ---

@auth.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.chat'))
    form = RegistrationForm()
    if form.validate_on_submit():
        try:
            existing_user = db.session.scalar(db.select(User).where(
                (User.username == form.username.data) | (User.email == form.email.data)
            ))
            if existing_user:
                 flash('Username or email already exists.', 'warning')
                 # Use 'auth/' prefix for template path
                 return render_template('auth/register.html', title='Register', form=form)

            user = User(username=form.username.data, email=form.email.data)
            user.set_password(form.password.data)
            db.session.add(user)
            db.session.commit()

            # Send confirmation email
            try:
                token = generate_confirmation_token(user.email)
                confirm_url = url_for('auth.confirm_email', token=token, _external=True)
                # Use 'auth/' prefix for email template path
                html_body = render_template('auth/confirm_email_template.html', confirm_url=confirm_url)
                text_body = f"Please click the link to confirm your email: {confirm_url}"
                subject = "Please confirm your email address"
                msg = Message(subject, sender=current_app.config.get('MAIL_DEFAULT_SENDER'),
                              recipients=[user.email], body=text_body, html=html_body)
                mail.send(msg)
                flash('A confirmation email has been sent. Please check your inbox.', 'success')
            except Exception as e:
                logging.error(f"Error sending confirmation email to {user.email}: {e}")
                flash('Registration successful, but could not send confirmation email.', 'warning')

            return redirect(url_for('auth.login'))
        except Exception as e:
            db.session.rollback()
            logging.error(f"Error during registration for {form.username.data}: {e}")
            flash('An error occurred during registration.', 'danger')

    # Use 'auth/' prefix for template path
    return render_template('auth/register.html', title='Register', form=form)


@auth.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.chat'))
    form = LoginForm()
    if form.validate_on_submit():
        user = db.session.scalar(db.select(User).where(User.username == form.username.data))
        if user and user.check_password(form.password.data):
            if user.email_confirmed:
                login_user(user, remember=form.remember_me.data)
                flash('Login successful!', 'success')
                next_page = request.args.get('next')
                return redirect(next_page) if next_page and next_page.startswith('/') else redirect(url_for('main.chat'))
            else:
                # Email not confirmed - flash message and redirect back to login
                # The 'Resend' link is now permanently on the login template
                flash('Your email address has not been confirmed. Please check your inbox or use the link below to resend the confirmation email.', 'warning')
                return redirect(url_for('auth.login'))
        else:
            flash('Login unsuccessful. Please check username and password.', 'danger')

    # Use 'auth/' prefix for template path
    return render_template('auth/login.html', title='Login', form=form)


@auth.route('/logout')
@login_required
def logout():
    username = current_user.username
    logout_user()
    flash(f'User {username} has been logged out.', 'info')
    return redirect(url_for('main.index'))


@auth.route('/confirm/<token>')
def confirm_email(token):
    # Prevent already logged-in and confirmed users from accessing unnecessarily
    if current_user.is_authenticated and current_user.email_confirmed:
         return redirect(url_for('main.index'))
         
    try:
        email = confirm_token(token)
        if not email:
            flash('The confirmation link is invalid or has expired.', 'danger')
            # Redirect to dedicated resend request page
            return redirect(url_for('auth.resend_confirmation_request'))

        user = db.session.scalar(db.select(User).where(User.email == email))
        if not user:
             flash('User associated with this token not found.', 'warning')
             # Redirect to dedicated resend request page (or login?)
             return redirect(url_for('auth.resend_confirmation_request'))

        if user.email_confirmed:
            flash('Account already confirmed. Please login.', 'success')
        else:
            user.email_confirmed = True
            user.email_confirmed_on = datetime.datetime.now()
            db.session.commit()
            flash('You have confirmed your account. Thanks!', 'success')

    except Exception as e:
        db.session.rollback()
        logging.error(f"Error during email confirmation commit: {e}")
        flash('An error occurred during confirmation.', 'danger')
        # Redirect to login on error
        return redirect(url_for('auth.login'))

    # Redirect to login after confirmation attempt (success or already confirmed)
    return redirect(url_for('auth.login'))


@auth.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    form = ForgotPasswordForm()
    if form.validate_on_submit():
        try:
            user = db.session.scalar(db.select(User).where(User.email == form.email.data))
            if user:
                # Send email only if user exists
                token = generate_password_reset_token(user.email)
                reset_url = url_for('auth.reset_password', token=token, _external=True)
                # Use 'auth/' prefix for email template path
                html_body = render_template('auth/reset_password_email_template.html', reset_url=reset_url)
                text_body = f"Click to reset password: {reset_url}"
                subject = "Password Reset Request"
                msg = Message(subject, sender=current_app.config.get('MAIL_DEFAULT_SENDER'),
                              recipients=[user.email], body=text_body, html=html_body)
                mail.send(msg)

            flash('If an account with that email exists, a password reset link has been sent.', 'info')
            return redirect(url_for('auth.login'))
        except Exception as e:
            logging.error(f"Error during forgot password for {form.email.data}: {e}")
            flash('An error occurred. Please try again later.', 'danger')

    # Use 'auth/' prefix for template path
    return render_template('auth/forgot_password.html', title='Forgot Password', form=form)


@auth.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    email = confirm_password_reset_token(token)
    if not email:
        flash('The password reset link is invalid or has expired.', 'danger')
        return redirect(url_for('auth.forgot_password'))

    user = db.session.scalar(db.select(User).where(User.email == email))
    if not user:
        flash('User not found.', 'danger')
        return redirect(url_for('auth.forgot_password'))

    form = ResetPasswordForm()
    if form.validate_on_submit():
        try:
            # Re-verify token before setting password
            if not confirm_password_reset_token(token):
                 flash('The password reset link is invalid or has expired.', 'danger')
                 return redirect(url_for('auth.forgot_password'))

            user.set_password(form.password.data)
            # Decide if password reset should affect confirmation status (currently doesn't)
            # user.email_confirmed = False # Uncomment if re-confirmation is desired
            db.session.commit()
            flash('Your password has been successfully reset. Please log in.', 'success')
            return redirect(url_for('auth.login'))
        except Exception as e:
            db.session.rollback()
            logging.error(f"Error resetting password for {email}: {e}")
            flash('An error occurred while resetting your password.', 'danger')
            # Re-render form if commit fails, use 'auth/' prefix for template path
            return render_template('auth/reset_password.html', title='Reset Password', form=form, token=token)

    # Use 'auth/' prefix for template path
    return render_template('auth/reset_password.html', title='Reset Password', form=form, token=token)


# --- New Route for Resending Confirmation ---
@auth.route('/resend_confirmation_request', methods=['GET', 'POST'])
def resend_confirmation_request():
    """Displays form and handles request to resend confirmation email."""
    if current_user.is_authenticated and current_user.email_confirmed:
         return redirect(url_for('main.index')) # No need if logged in & confirmed

    form = ResendConfirmationForm() # Uses the new form
    if form.validate_on_submit():
        user = db.session.scalar(db.select(User).where(User.email == form.email.data))

        if user and not user.email_confirmed:
            # User exists and is NOT confirmed, resend email
            try:
                token = generate_confirmation_token(user.email) # Use confirmation token helper
                confirm_url = url_for('auth.confirm_email', token=token, _external=True)
                # Use 'auth/' prefix for email template path
                html_body = render_template('auth/confirm_email_template.html', confirm_url=confirm_url)
                text_body = f"Please click the link to confirm your email: {confirm_url}"
                subject = "Please confirm your email address (Resent)"
                msg = Message(subject, sender=current_app.config.get('MAIL_DEFAULT_SENDER'),
                              recipients=[user.email], body=text_body, html=html_body)
                mail.send(msg)
                flash('A new confirmation email has been sent. Please check your inbox.', 'success')
            except Exception as e:
                logging.error(f"Error resending confirmation email to {user.email}: {e}")
                flash('An error occurred while trying to resend the confirmation email.', 'danger')
        elif user and user.email_confirmed:
             flash('Your email address is already confirmed. You can log in.', 'info')
        else:
             # User not found - show generic message anyway to prevent enumeration
             flash('If an account with that email exists and requires confirmation, a new link has been sent.', 'info')

        return redirect(url_for('auth.login')) # Redirect to login after processing

    # Use 'auth/' prefix for template path
    return render_template('auth/resend_confirmation_request.html',
                           title='Resend Confirmation',
                           form=form)