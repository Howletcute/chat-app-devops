# app/events.py
import logging
from flask import request
from flask_login import current_user # Need this to check auth status
from flask_socketio import emit, join_room, leave_room
# Import the socketio instance and redis_client created in app/__init__.py
# The '.' means import from the current package ('app')
from . import socketio, redis_client

# === Constants (Moved from app.py) ===
GENERAL_ROOM = "general_chat"
MESSAGE_HISTORY_KEY = f"room:{GENERAL_ROOM}:messages" # Redis list key
SID_NICKNAME_MAP_KEY = "sid_nickname_map" # Redis Hash mapping session ID to nickname
MAX_MESSAGES = 50

# === Helper Functions (Moved from app.py, now use imported redis_client) ===
# (Includes basic error handling for Redis operations)
def add_message(nickname, msg):
    if redis_client:
        try:
            message_data = f"{nickname}: {msg}"
            redis_client.lpush(MESSAGE_HISTORY_KEY, message_data)
            redis_client.ltrim(MESSAGE_HISTORY_KEY, 0, MAX_MESSAGES - 1)
        except Exception as e:
            logging.error(f"Redis error adding message: {e}")
    else:
        logging.warning("Redis client not available, message not stored.")

def get_message_history():
    if redis_client:
        try:
            return redis_client.lrange(MESSAGE_HISTORY_KEY, 0, MAX_MESSAGES - 1)
        except Exception as e:
            logging.error(f"Redis error getting message history: {e}")
    return [] # Return empty list if no Redis or error

def add_online_user(sid, nickname):
    if redis_client and nickname and sid:
        try:
            redis_client.hset(SID_NICKNAME_MAP_KEY, sid, nickname)
            logging.info(f"Mapped SID {sid} to nickname {nickname}")
        except Exception as e:
            logging.error(f"Redis error adding online user {nickname}: {e}")
    # Silently ignore if no redis or missing data

def remove_online_user(sid):
     if redis_client and sid:
        try:
            nickname = redis_client.hget(SID_NICKNAME_MAP_KEY, sid)
            if nickname:
                redis_client.hdel(SID_NICKNAME_MAP_KEY, sid)
                logging.info(f"Removed SID {sid} (nickname {nickname}) from map")
                return nickname # Return nickname that left
            # else: SID wasn't in map
        except Exception as e:
            logging.error(f"Redis error removing online user (SID: {sid}): {e}")
     return None # Return None if not found or error or no redis

def get_online_users():
     if redis_client:
        try:
            # Get unique nicknames from the values in the SID map
            users = redis_client.hvals(SID_NICKNAME_MAP_KEY)
            unique_users = sorted(list(set(users)))
            # logging.info(f"Current online users (from SID map): {unique_users}") # Maybe too verbose
            return unique_users
        except Exception as e:
            logging.error(f"Redis error getting online users: {e}")
     return [] # Return empty list if no Redis or error

def get_nickname_from_sid(sid):
    if redis_client and sid:
        try:
            return redis_client.hget(SID_NICKNAME_MAP_KEY, sid)
        except Exception as e:
            logging.error(f"Redis error getting nickname from SID {sid}: {e}")
    return None


# === SocketIO Event Handlers ===
# These handlers use the '@socketio.on' decorator, using the
# 'socketio' instance imported from app/__init__.py

@socketio.on('connect')
def handle_connect():
    # Check if user is logged in via Flask-Login session before allowing connection
    if not current_user.is_authenticated:
        logging.warning(f"Unauthenticated SocketIO connection attempt denied: {request.sid}")
        return False # Reject connection by returning False

    # User is authenticated, get their details
    nickname = current_user.username
    sid = request.sid
    logging.info(f'Authenticated client connected: {nickname} ({sid})')

    # Add to room, track user, notify others
    join_room(GENERAL_ROOM)
    add_online_user(sid, nickname) # Add to our Redis SID->Nickname map
    emit('status', {'msg': f'{nickname} has joined the chat.'}, to=GENERAL_ROOM)
    emit('user_list_update', get_online_users(), broadcast=True)

    # Send message history only to the newly connected client
    history = get_message_history()
    history.reverse() # Show oldest first
    for msg_data in history:
        try:
            parts = msg_data.split(":", 1) # Simple split, assumes ':' isn't in nickname
            hist_nick = parts[0]
            hist_msg = parts[1].strip() if len(parts) > 1 else ""
            emit('chat_message', {'nickname': hist_nick, 'msg': hist_msg}, room=sid)
        except Exception as e:
            logging.error(f"Error processing history message '{msg_data}': {e}")


@socketio.on('disconnect')
def handle_disconnect():
    # Find out who disconnected using the SID map (current_user might be gone)
    sid = request.sid
    nickname = remove_online_user(sid) # Remove user by SID from Redis map
    if nickname:
        # If we found the user, leave room and notify others
        leave_room(GENERAL_ROOM)
        logging.info(f'Client disconnected: {nickname} ({sid})')
        emit('status', {'msg': f'{nickname} has left the chat.'}, to=GENERAL_ROOM)
        emit('user_list_update', get_online_users(), broadcast=True) # Send updated list
    else:
        # This might happen if disconnect occurs before successful connect/join
        logging.info(f'Unmapped client disconnected: {sid}')


@socketio.on('new_message')
def handle_new_message(data):
    # Ensure user is authenticated via Flask-Login before processing message
    if not current_user.is_authenticated:
        logging.warning(f"Message received from unauthenticated SID: {request.sid}")
        return # Ignore message

    # Get username from the verified logged-in user session
    nickname = current_user.username
    sid = request.sid
    msg = data.get('msg', '') # Get message content sent by client

    if msg and nickname: # Process only if message is not empty and user is known
        logging.info(f'Message from {nickname} ({sid}): {msg}')
        add_message(nickname, msg) # Store message (using Redis helper)
        # Broadcast message to everyone in the general room
        emit('chat_message', {'nickname': nickname, 'msg': msg}, to=GENERAL_ROOM)
    elif not msg:
         logging.warning(f"Empty message received from {nickname} ({sid})")
    # No 'else' needed as nickname should always be present if authenticated