# app/models.py
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
# Import the db instance created in app/__init__.py
# The '.' means import from the current package ('app')
from . import db

class User(UserMixin, db.Model):
    """User model for storing login credentials."""
    __tablename__ = 'users' # Optional: explicitly name the table

    id = db.Column(db.Integer, primary_key=True)
    # Index=True makes lookups by username/email faster
    username = db.Column(db.String(80), index=True, unique=True, nullable=False)
    email = db.Column(db.String(120), index=True, unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False) # Store hash, not password
    nickname_color = db.Column(db.String(7), nullable=True, default='#000000') # Stores #RRGGBB hex color

    # email_confirmed = db.Column(db.Boolean, default=False, nullable=False) # Add later if doing email confirmation

    # Method to store hashed password
    def set_password(self, password):
        # Use a robust hashing method with sufficient salt length
        self.password_hash = generate_password_hash(password, method='pbkdf2:sha256', salt_length=16)

    # Method to verify password
    def check_password(self, password):
        if not self.password_hash:
             return False # Should not happen if password is required on registration
        return check_password_hash(self.password_hash, password)

    # How the object prints out (useful for debugging)
    def __repr__(self):
        return f'<User {self.username}>'

# NOTE: The @login_manager.user_loader function should stay in app/__init__.py
#       (or eventually move to an auth blueprint) because it needs the
#       login_manager instance. We just need to make sure IT imports the User model.