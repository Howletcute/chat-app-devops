# app.py
import os
from flask import Flask, render_template, request, session, redirect, url_for
from flask_socketio import SocketIO, emit, join_room, leave_room
import redis
from dotenv import load_dotenv

load_dotenv() # Load environment variables from .env file for local dev

app = Flask(__name__)
# Use environment variable for secret key or fallback for dev
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'a_very_secret_key_dev')

# Redis connection details from environment variables
REDIS_HOST = os.environ.get('REDIS_HOST', 'localhost')
REDIS_PORT = int(os.environ.get('REDIS_PORT', 6379))
# REDIS_PASSWORD = os.environ.get('REDIS_PASSWORD', None) # Add if your Redis needs a password

# Initialize Flask-SocketIO - use 'eventlet' for async mode
# Connect to Redis for message queue (optional but good for scaling)
redis_url = f"redis://{REDIS_HOST}:{REDIS_PORT}/0"
# If password needed: redis_url = f"redis://:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}/0"
socketio = SocketIO(app, async_mode='eventlet', message_queue=redis_url)

# Connect to Redis for storing messages and users
try:
    redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=1, decode_responses=True) # Use DB 1 for app data
    redis_client.ping()
    print("Connected to Redis successfully!")
except redis.exceptions.ConnectionError as e:
    print(f"Could not connect to Redis: {e}")
    redis_client = None # Handle gracefully if Redis isn't available

# --- Constants ---
GENERAL_ROOM = "general_chat"
MESSAGE_HISTORY_KEY = f"room:{GENERAL_ROOM}:messages" # Redis list key
ONLINE_USERS_KEY = "online_users" # Redis set key
MAX_MESSAGES = 50 # Max message history to keep

# --- Helper Functions ---
def add_message(nickname, msg):
    if redis_client:
        message_data = f"{nickname}: {msg}"
        # Add message to the start of the list
        redis_client.lpush(MESSAGE_HISTORY_KEY, message_data)
        # Trim the list to keep only the last MAX_MESSAGES
        redis_client.ltrim(MESSAGE_HISTORY_KEY, 0, MAX_MESSAGES - 1)

def get_message_history():
    if redis_client:
        # Get the last MAX_MESSAGES (they are stored newest first)
        return redis_client.lrange(MESSAGE_HISTORY_KEY, 0, MAX_MESSAGES - 1)
    return []

def add_online_user(nickname):
    if redis_client and nickname:
        redis_client.sadd(ONLINE_USERS_KEY, nickname)

def remove_online_user(nickname):
     if redis_client and nickname:
        redis_client.srem(ONLINE_USERS_KEY, nickname)

def get_online_users():
     if redis_client:
        users = list(redis_client.smembers(ONLINE_USERS_KEY))
        return sorted(users) # Sort for consistent display
     return []

# --- HTTP Routes ---
@app.route('/', methods=['GET'])
def index():
    """Serves the nickname entry page."""
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def enter_chat():
    """Stores nickname in session and redirects to chat page."""
    nickname = request.form.get('nickname')
    if not nickname:
        return redirect(url_for('index')) # Redirect back if no nickname
    session['nickname'] = nickname # Store nickname in user's session
    return redirect(url_for('chat'))

@app.route('/chat', methods=['GET'])
def chat():
    """Serves the main chat page."""
    nickname = session.get('nickname')
    if not nickname:
        return redirect(url_for('index')) # Redirect if no nickname in session
    return render_template('chat.html', nickname=nickname)

# --- SocketIO Event Handlers ---
@socketio.on('connect')
def handle_connect():
    """Handles a new client connection."""
    nickname = session.get('nickname') # Get nickname from session
    if nickname:
        join_room(GENERAL_ROOM) # Add user to the chat room
        add_online_user(nickname)
        print(f'Client connected: {nickname} ({request.sid})')
        # Send status message to room
        emit('status', {'msg': f'{nickname} has entered the chat.'}, to=GENERAL_ROOM)
        # Send current user list to everyone
        emit('user_list_update', get_online_users(), broadcast=True)
        # Send message history to the connecting client ONLY
        history = get_message_history()
        history.reverse() # Reverse to show oldest first
        for msg_data in history:
             # Parse nickname and message (simple split)
             parts = msg_data.split(":", 1)
             hist_nick = parts[0]
             hist_msg = parts[1].strip() if len(parts) > 1 else ""
             emit('chat_message', {'nickname': hist_nick, 'msg': hist_msg}, room=request.sid)
    else:
        print(f'Anonymous client connected ({request.sid}), nickname needed.')
        # Could potentially disconnect or handle differently

@socketio.on('disconnect')
def handle_disconnect():
    """Handles a client disconnection."""
    nickname = session.get('nickname') # Get nickname from session
    if nickname:
        leave_room(GENERAL_ROOM) # Remove user from room
        remove_online_user(nickname)
        print(f'Client disconnected: {nickname} ({request.sid})')
        # Send status message
        emit('status', {'msg': f'{nickname} has left the chat.'}, to=GENERAL_ROOM, skip_sid=request.sid) # Don't send to disconnected user
        # Send updated user list
        emit('user_list_update', get_online_users(), broadcast=True)
    else:
         print(f'Anonymous client disconnected ({request.sid})')

@socketio.on('new_message')
def handle_new_message(data):
    """Handles receiving a new message from a client."""
    nickname = data.get('nickname', 'Anonymous')
    msg = data.get('msg', '')
    if msg:
        print(f'Message from {nickname}: {msg}')
        add_message(nickname, msg)
        # Broadcast message to everyone in the room including sender
        emit('chat_message', {'nickname': nickname, 'msg': msg}, to=GENERAL_ROOM)

# --- Main Execution ---
if __name__ == '__main__':
    print("Starting Flask-SocketIO server with eventlet...")
    # Run with eventlet server for WebSocket support
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)