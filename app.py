# app.py
import os
from flask import Flask, render_template, request, session, redirect, url_for
from flask_socketio import SocketIO, emit, join_room, leave_room
import redis
from dotenv import load_dotenv
import logging # Add logging

logging.basicConfig(level=logging.INFO) # Basic logging config
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'a_very_secret_key_dev')

REDIS_HOST = os.environ.get('REDIS_HOST', 'localhost')
REDIS_PORT = int(os.environ.get('REDIS_PORT', 6379))
redis_url = f"redis://{REDIS_HOST}:{REDIS_PORT}/0" # For SocketIO message queue
socketio = SocketIO(app, async_mode='eventlet', message_queue=redis_url)

# Use separate Redis DB for app data
try:
    redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=1, decode_responses=True)
    redis_client.ping()
    logging.info("Connected to Redis successfully!")
except redis.exceptions.ConnectionError as e:
    logging.error(f"Could not connect to Redis: {e}")
    redis_client = None

# --- Constants ---
GENERAL_ROOM = "general_chat"
MESSAGE_HISTORY_KEY = f"room:{GENERAL_ROOM}:messages"
SID_NICKNAME_MAP_KEY = "sid_nickname_map" # Hash mapping session ID to nickname
MAX_MESSAGES = 50

# --- Helper Functions ---
def add_message(nickname, msg):
    if redis_client:
        message_data = f"{nickname}: {msg}"
        redis_client.lpush(MESSAGE_HISTORY_KEY, message_data)
        redis_client.ltrim(MESSAGE_HISTORY_KEY, 0, MAX_MESSAGES - 1)

def get_message_history():
    if redis_client:
        return redis_client.lrange(MESSAGE_HISTORY_KEY, 0, MAX_MESSAGES - 1)
    return []

# Add user SID and Nickname to the mapping
def add_online_user(sid, nickname):
    if redis_client and nickname and sid:
        redis_client.hset(SID_NICKNAME_MAP_KEY, sid, nickname)
        logging.info(f"Mapped SID {sid} to nickname {nickname}")

# Remove user by SID and return the nickname found
def remove_online_user(sid):
     if redis_client and sid:
        nickname = redis_client.hget(SID_NICKNAME_MAP_KEY, sid)
        if nickname:
            redis_client.hdel(SID_NICKNAME_MAP_KEY, sid) # Remove mapping
            logging.info(f"Removed SID {sid} (nickname {nickname}) from map")
            return nickname
        else:
            logging.warning(f"Tried to remove SID {sid}, but not found in map.")
            return None
     return None

# Get online users by retrieving all nicknames from the SID map
def get_online_users():
     if redis_client:
        # Get all nicknames (values) from the SID->Nickname hash map
        users = redis_client.hvals(SID_NICKNAME_MAP_KEY)
        # Get unique names and sort them for display
        unique_users = sorted(list(set(users)))
        logging.info(f"Current online users (from SID map): {unique_users}")
        return unique_users
     return []

# Helper to get nickname associated with a specific connection ID
def get_nickname_from_sid(sid):
    if redis_client and sid:
        return redis_client.hget(SID_NICKNAME_MAP_KEY, sid)
    return None

# --- HTTP Routes ---
@app.route('/', methods=['GET'])
def index():
    """Serves the nickname entry page."""
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def enter_chat():
    """Stores nickname temporary in session JUST for redirect, allows duplicates."""
    nickname = request.form.get('nickname')
    # Allow login even if nickname is taken, just ensure it's not empty
    if not nickname:
         logging.warning("Enter chat attempt with no nickname.")
         # TODO: Add user feedback here (e.g., flash message)
         return redirect(url_for('index'))

    # Store in session just to pass it to the chat template on redirect
    session['nickname'] = nickname
    logging.info(f"Nickname '{nickname}' submitted, redirecting to chat.")
    return redirect(url_for('chat'))

@app.route('/chat', methods=['GET'])
def chat():
    """Serves the main chat page, passing nickname for initial JS use."""
    nickname = session.get('nickname')
    if not nickname:
        # If session lost somehow before reaching chat, redirect back
        return redirect(url_for('index'))
    # Pass nickname to template; JS will use this to emit the 'join' event
    return render_template('chat.html', nickname=nickname)

# --- SocketIO Event Handlers ---
@socketio.on('connect')
def handle_connect():
    """Client connected, wait for 'join' event with nickname."""
    logging.info(f'Client connected: {request.sid}. Waiting for join event.')
    # Send message history immediately
    history = get_message_history()
    history.reverse() # Show oldest first
    for msg_data in history:
        parts = msg_data.split(":", 1)
        hist_nick = parts[0]
        hist_msg = parts[1].strip() if len(parts) > 1 else ""
        emit('chat_message', {'nickname': hist_nick, 'msg': hist_msg}, room=request.sid)

@socketio.on('disconnect')
def handle_disconnect():
    """Client disconnected, remove SID mapping and notify others."""
    nickname = remove_online_user(request.sid) # Remove user by SID from map
    if nickname:
        leave_room(GENERAL_ROOM)
        logging.info(f'Client disconnected: {nickname} ({request.sid})')
        # Notify room that user left
        emit('status', {'msg': f'{nickname} has left the chat.'}, to=GENERAL_ROOM)
        # Broadcast updated user list
        emit('user_list_update', get_online_users(), broadcast=True)
    else:
        logging.info(f'Unmapped client disconnected: {request.sid}')

@socketio.on('join') # Client explicitly joins with nickname after connecting
def handle_join(data):
    """Handles client sending its nickname after connection."""
    nickname = data.get('nickname')
    sid = request.sid
    if not nickname:
        logging.warning(f"Join attempt with no nickname from {sid}")
        return

    join_room(GENERAL_ROOM)
    add_online_user(sid, nickname) # Add SID -> nickname mapping
    logging.info(f"Client joined room: {nickname} ({sid})")
    # Notify room that user joined
    emit('status', {'msg': f'{nickname} has entered the chat.'}, to=GENERAL_ROOM)
     # Broadcast updated user list
    emit('user_list_update', get_online_users(), broadcast=True)

@socketio.on('new_message')
def handle_new_message(data):
    """Handles receiving a new message, uses SID map to find sender."""
    sid = request.sid
    # Get nickname reliably from SID map
    nickname = get_nickname_from_sid(sid)
    msg = data.get('msg', '')

    if msg and nickname: # Only process if message exists and sender is known
        logging.info(f'Message from {nickname} ({sid}): {msg}')
        add_message(nickname, msg)
        # Broadcast message to everyone in the room
        emit('chat_message', {'nickname': nickname, 'msg': msg}, to=GENERAL_ROOM)
    elif not msg:
         logging.warning(f"Empty message received from {nickname or 'unknown user'} ({sid})")
    else: # Nickname lookup failed
         logging.warning(f"Message received from SID {sid} with no mapped nickname: {msg}")

# --- Main Execution ---
if __name__ == '__main__':
    logging.info("Starting Flask-SocketIO server with eventlet...")
    # Turn off Flask debug mode when using eventlet/gunicorn in production/docker
    socketio.run(app, host='0.0.0.0', port=5000, debug=False)