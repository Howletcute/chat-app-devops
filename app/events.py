# app/events.py
import logging
from flask import request
from flask_login import current_user
from flask_socketio import emit, join_room, leave_room
# Import necessary components from the app package (__init__)
from . import socketio, redis_client, db
# Needs the User model for database operations
from .models import User

# === Constants ===
GENERAL_ROOM = "general_chat"
MESSAGE_HISTORY_KEY = f"room:{GENERAL_ROOM}:messages" # Redis list key
SID_NICKNAME_MAP_KEY = "sid_nickname_map" # Redis Hash mapping session ID to nickname
MAX_MESSAGES = 50

# === Helper Functions ===
# (Includes basic error handling for Redis operations)

def add_message(nickname, msg, color): # Added color parameter
    """Adds message WITH color to Redis history list."""
    if redis_client:
        try:
            separator = "|||" # Define separator
            # Store data as "nickname|||#RRGGBB|||message content"
            message_data = f"{nickname}{separator}{color}{separator}{msg}"
            redis_client.lpush(MESSAGE_HISTORY_KEY, message_data)
            redis_client.ltrim(MESSAGE_HISTORY_KEY, 0, MAX_MESSAGES - 1)
        except Exception as e:
            logging.error(f"Redis error adding message: {e}")
    else:
        logging.warning("Redis client not available, message not stored.")

def get_message_history():
    """Retrieves message history strings from Redis."""
    if redis_client:
        try:
            return redis_client.lrange(MESSAGE_HISTORY_KEY, 0, MAX_MESSAGES - 1)
        except Exception as e:
            logging.error(f"Redis error getting message history: {e}")
    return [] # Return empty list if no Redis or error

def add_online_user(sid, nickname):
    """Maps a SocketIO SID to a nickname in Redis."""
    if redis_client and nickname and sid:
        try:
            redis_client.hset(SID_NICKNAME_MAP_KEY, sid, nickname)
            logging.info(f"Mapped SID {sid} to nickname {nickname}")
        except Exception as e:
            logging.error(f"Redis error adding online user {nickname}: {e}")
    # Silently ignore if no redis or missing data

def remove_online_user(sid):
    """Removes SID mapping from Redis and returns the associated nickname."""
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
    """Gets a unique, sorted list of online nicknames from Redis."""
    if redis_client:
        try:
            # Get unique nicknames from the values in the SID map
            users = redis_client.hvals(SID_NICKNAME_MAP_KEY)
            unique_users = sorted(list(set(users)))
            # logging.info(f"Current online users (from SID map): {unique_users}") # Verbose
            return unique_users
        except Exception as e:
            logging.error(f"Redis error getting online users: {e}")
    return [] # Return empty list if no Redis or error

# get_nickname_from_sid not currently used by handlers, but keep for potential future use
def get_nickname_from_sid(sid):
    """Gets nickname associated with a specific SID from Redis."""
    if redis_client and sid:
        try:
            return redis_client.hget(SID_NICKNAME_MAP_KEY, sid)
        except Exception as e:
            logging.error(f"Redis error getting nickname from SID {sid}: {e}")
    return None


# === SocketIO Event Handlers ===

@socketio.on('connect')
def handle_connect():
    """Handles new client connections after user is authenticated."""
    if not current_user.is_authenticated:
        logging.warning(f"Unauthenticated SocketIO connection attempt denied: {request.sid}")
        return False # Reject connection

    nickname = current_user.username
    sid = request.sid
    logging.info(f'Authenticated client connected: {nickname} ({sid})')

    # Add user to room and Redis map
    join_room(GENERAL_ROOM)
    add_online_user(sid, nickname)

    # Notify room members of the new user
    emit('status', {'msg': f'{nickname} has joined the chat.'}, to=GENERAL_ROOM)
    # Broadcast updated user list to everyone
    emit('user_list_update', get_online_users(), broadcast=True)

    # Send message history only to the newly connected client
    history = get_message_history()
    history.reverse() # Show oldest messages first
    for msg_data in history:
        try:
            separator = "|||"
            parts = msg_data.split(separator, 2)
            hist_nick = "Error"
            hist_color = '#888888' # Default error color
            hist_msg = "(message format error)"

            if len(parts) == 3:
                hist_nick, hist_color, hist_msg = parts
                if not hist_color.startswith('#') or len(hist_color) != 7:
                    hist_color = '#000000' # Default color if format invalid
            elif len(parts) == 1: # Handle potential old format "nickname: msg"
                legacy_parts = msg_data.split(":", 1)
                hist_nick = legacy_parts[0]
                hist_msg = legacy_parts[1].strip() if len(legacy_parts) > 1 else ""
                hist_color = '#000000' # Default color for old format

            # Emit historical message with color to the connecting client only
            emit('chat_message', {'nickname': hist_nick, 'msg': hist_msg, 'color': hist_color}, room=sid)
        except Exception as e:
            logging.error(f"Error processing history message '{msg_data}': {e}")


@socketio.on('disconnect')
def handle_disconnect():
    """Handles client disconnections."""
    sid = request.sid
    # Remove user from Redis map, get their nickname if found
    nickname = remove_online_user(sid)
    if nickname:
        # If user was mapped, leave room and notify others
        leave_room(GENERAL_ROOM)
        logging.info(f'Client disconnected: {nickname} ({sid})')
        emit('status', {'msg': f'{nickname} has left the chat.'}, to=GENERAL_ROOM)
        emit('user_list_update', get_online_users(), broadcast=True) # Update user list for all
    else:
        # Might be unauthenticated user or already cleaned up
        logging.info(f'Unmapped client disconnected: {sid}')


@socketio.on('set_color')
def handle_set_color(data):
    """Handles client sending a new nickname color preference."""
    if not current_user.is_authenticated:
        logging.warning(f"Unauthenticated set_color attempt ignored from {request.sid}")
        return

    new_color = data.get('color')
    # Basic hex color validation
    if not new_color or not isinstance(new_color, str) or \
       not new_color.startswith('#') or len(new_color) != 7:
        logging.warning(f"Invalid color format '{new_color}' from {current_user.username}")
        emit('error', {'msg': 'Invalid color format (#RRGGBB required).'}, room=request.sid)
        return

    try:
        # Use db.session.get for safe primary key lookup
        user = db.session.get(User, current_user.id)
        if user:
            user.nickname_color = new_color
            db.session.commit() # Save change to Postgres
            logging.info(f"User {user.username} updated nickname color to {new_color}")
            # emit('status', {'msg': f'Color updated to {new_color}'}, room=request.sid) # Optional confirmation
        else:
             logging.error(f"Could not find user {current_user.id} in DB to update color.")
    except Exception as e:
        db.session.rollback()
        logging.error(f"Database error updating color for user {current_user.username}: {e}")
        emit('error', {'msg': 'Server error saving color preference.'}, room=request.sid)


@socketio.on('new_message')
def handle_new_message(data):
    """Handles receiving and broadcasting new chat messages."""
    if not current_user.is_authenticated:
        logging.warning(f"Message received from unauthenticated SID: {request.sid}")
        return

    nickname = current_user.username
    # Fetch current color from the authenticated user object
    user_color = current_user.nickname_color or '#000000' # Default to black
    sid = request.sid
    msg = data.get('msg', '')

    if msg.strip() and nickname: # Process only if message not empty/whitespace
        msg = msg.strip() # Trim whitespace
        logging.info(f'Message from {nickname} ({sid}) color {user_color}: {msg}')
        # Add message with color to Redis history
        add_message(nickname, msg, user_color)
        # Broadcast message, including sender's color, to the general room
        emit('chat_message',
             {'nickname': nickname, 'msg': msg, 'color': user_color},
             to=GENERAL_ROOM) # Use to=GENERAL_ROOM to send to everyone
    elif nickname: # Message was empty or just whitespace
         logging.warning(f"Empty message received from {nickname} ({sid})")
    # No need for else, shouldn't happen if authenticated