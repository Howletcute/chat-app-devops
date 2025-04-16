# wsgi.py
from app import app, socketio
import eventlet

eventlet.wsgi.server(eventlet.listen(('', 5000)), app)