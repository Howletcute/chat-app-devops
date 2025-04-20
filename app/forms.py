# app/forms.py
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, BooleanField, EmailField 
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError
# We no longer need to import User model here

class RegistrationForm(FlaskForm):
    """Form for user registration."""
    username = StringField('Username',
                           validators=[DataRequired(), Length(min=2, max=80)])
    email = StringField('Email',
                        validators=[DataRequired(), Email(), Length(max=120)])
    password = PasswordField('Password',
                             validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirm Password',
                                     validators=[DataRequired(), EqualTo('password', message='Passwords must match.')])
    submit = SubmitField('Sign Up')
    # Uniqueness validation for username/email will be done in the /register route.

class LoginForm(FlaskForm):
    """Form for user login."""
    # Users can log in with their username
    username = StringField('Username',
                           validators=[DataRequired(), Length(min=2, max=80)])
    password = PasswordField('Password',
                             validators=[DataRequired()])
    remember_me = BooleanField('Remember Me') # Option for persistent session
    submit = SubmitField('Login')
class RegistrationForm(FlaskForm):
    """Form for user registration."""
    username = StringField('Username',
                           validators=[DataRequired(), Length(min=2, max=80)])
    email = StringField('Email',
                        validators=[DataRequired(), Email(), Length(max=120)])
    password = PasswordField('Password',
                             validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirm Password',
                                     validators=[DataRequired(), EqualTo('password', message='Passwords must match.')])
    submit = SubmitField('Sign Up')

class LoginForm(FlaskForm):
    """Form for user login."""
    username = StringField('Username',
                           validators=[DataRequired(), Length(min=2, max=80)])
    password = PasswordField('Password',
                             validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Login')


# --- NEW FORMS for Password Reset ---

class ForgotPasswordForm(FlaskForm):
    """Form for requesting a password reset email."""
    email = EmailField('Your Email Address', 
                       validators=[DataRequired(), Email(), Length(max=120)])
    submit = SubmitField('Request Password Reset')


class ResetPasswordForm(FlaskForm):
    """Form for entering a new password after clicking reset link."""
    password = PasswordField('New Password',
                             validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirm New Password',
                                     validators=[DataRequired(), EqualTo('password', message='Passwords must match.')])
    submit = SubmitField('Reset Password') 