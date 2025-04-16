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
redis_url = f"redis://{REDIS_HOST}:{REDIS_PORT}/0"
socketio = SocketIO(app, async_mode='eventlet', message_queue=redis_url)

# Use separate Redis DB for app data vs message queue
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
ONLINE_USERS_KEY = "online_users" # Set of nicknames
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

def add_online_user(sid, nickname):
    if redis_client and nickname and sid:
        redis_client.sadd(ONLINE_USERS_KEY, nickname)
        redis_client.hset(SID_NICKNAME_MAP_KEY, sid, nickname) # Map SID to nickname

def remove_online_user(sid):
     if redis_client and sid:
        nickname = redis_client.hget(SID_NICKNAME_MAP_KEY, sid) # Get nickname using SID
        if nickname:
            redis_client.srem(ONLINE_USERS_KEY, nickname)
            redis_client.hdel(SID_NICKNAME_MAP_KEY, sid) # Remove mapping
            return nickname # Return the nickname that was removed
        return None

def get_online_users():
     if redis_client:
        users = list(redis_client.smembers(ONLINE_USERS_KEY))
        return sorted(users)
     return []

def get_nickname_from_sid(sid):
    if redis_client and sid:
        return redis_client.hget(SID_NICKNAME_MAP_KEY, sid)
    return None

# --- HTTP Routes ---
@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def enter_chat():
    nickname = request.form.get('nickname')
    if not nickname or (redis_client and redis_client.sismember(ONLINE_USERS_KEY, nickname)):
         # Redirect back if nickname missing or already taken (basic check)
         logging.warning(f"Nickname '{nickname}' invalid or already taken.")
         return redirect(url_for('index')) # Ideally show an error message
    # Store nickname in session FOR THE HTTP redirect only. SocketIO will use its own mapping.
    session['nickname'] = nickname
    logging.info(f"Nickname '{nickname}' set in session, redirecting to chat.")
    return redirect(url_for('chat'))

@app.route('/chat', methods=['GET'])
def chat():
    nickname = session.get('nickname')
    if not nickname:
        return redirect(url_for('index'))
    # Pass nickname to template, JS will use it for initial join event
    return render_template('chat.html', nickname=nickname)

# --- SocketIO Event Handlers ---
@socketio.on('connect')
def handle_connect():
    # Don't rely on session here, wait for 'join' event from client
    logging.info(f'Client connected: {request.sid}')
    # Send message history to the connecting client ONLY
    history = get_message_history()
    history.reverse()
    for msg_data in history:
        parts = msg_data.split(":", 1)
        hist_nick = parts[0]
        hist_msg = parts[1].strip() if len(parts) > 1 else ""
        emit('chat_message', {'nickname': hist_nick, 'msg': hist_msg}, room=request.sid)


@socketio.on('disconnect')
def handle_disconnect():
    # Use SID map to find nickname reliably
    nickname = remove_online_user(request.sid)
    if nickname:
        leave_room(GENERAL_ROOM)
        logging.info(f'Client disconnected: {nickname} ({request.sid})')
        emit('status', {'msg': f'{nickname} has left the chat.'}, to=GENERAL_ROOM) # Broadcast leave message
        emit('user_list_update', get_online_users(), broadcast=True) # Broadcast updated user list
    else:
        logging.info(f'Client disconnected without known nickname: {request.sid}')

@socketio.on('join') # New event handler for client joining with nickname
def handle_join(data):
    nickname = data.get('nickname')
    sid = request.sid
    if not nickname:
        logging.warning(f"Join attempt with no nickname from {sid}")
        return

    # Check if nickname is already online (maybe redundant if checked in POST but good safety)
    if redis_client and redis_client.sismember(ONLINE_USERS_KEY, nickname):
        logging.warning(f"Nickname '{nickname}' tried to join but already exists.")
        # Optionally emit an error back to the client
        emit('error', {'msg': 'Nickname already taken.'}, room=sid)
        return

    join_room(GENERAL_ROOM)
    add_online_user(sid, nickname)
    logging.info(f"Client joined: {nickname} ({sid})")
    emit('status', {'msg': f'{nickname} has entered the chat.'}, to=GENERAL_ROOM)
    emit('user_list_update', get_online_users(), broadcast=True)


@socketio.on('new_message')
def handle_new_message(data):
    # Get nickname reliably from SID map, fallback to data from client as secondary
    sid = request.sid
    nickname = get_nickname_from_sid(sid) or data.get('nickname', 'Anonymous') # Prioritize server-side map
    msg = data.get('msg', '')

    if msg and nickname != 'Anonymous':
        logging.info(f'Message from {nickname} ({sid}): {msg}')
        add_message(nickname, msg)
        emit('chat_message', {'nickname': nickname, 'msg': msg}, to=GENERAL_ROOM)
    elif not msg:
         logging.warning(f"Empty message received from {nickname} ({sid})")
    else: # Nickname was Anonymous
         logging.warning(f"Message received from unknown user ({sid}): {msg}")


# --- Main Execution ---
if __name__ == '__main__':
    logging.info("Starting Flask-SocketIO server with eventlet...")
    socketio.run(app, host='0.0.0.0', port=5000, debug=False) # Turn debug off for production-like run