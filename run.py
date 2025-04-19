# run.py
import eventlet
eventlet.monkey_patch() # Apply patches immediately
import os
import logging
# Import the factory function and socketio instance from our app package
# '.' is not used here because run.py is outside the 'app' package
from app import create_app, socketio

# Get config name from environment variable or use default ('dev')
config_name = os.getenv('FLASK_CONFIG') or 'default'
# Create the Flask app instance using the factory
app = create_app(config_name)

# Run the application using SocketIO's development server (with Eventlet)
if __name__ == '__main__':
    logging.info(f"Starting application using configuration: {config_name}")
    # Get host/port/debug settings from app config if available, else use defaults
    host = os.environ.get('FLASK_RUN_HOST', '0.0.0.0')
    port = int(os.environ.get('FLASK_RUN_PORT', '5001'))
    debug = app.config.get('DEBUG', False) # Get DEBUG from loaded Flask config

    # Use socketio.run to handle WebSocket server correctly
    # Note: debug=True with socketio.run might enable Werkzeug reloader,
    # which can cause issues with some setups. Set to False for Gunicorn/production.
    socketio.run(app, host=host, port=port, debug=debug)