# app.py
import os
import psycopg2
from flask import Flask, request, redirect, url_for, render_template_string
import time # Import time for retry logic

app = Flask(__name__)

# --- Database Configuration ---
# Get DB details from environment variables, with defaults for local use
# We'll use 'postgres' as the default host, assuming Docker networking later.
DB_HOST = os.environ.get('DB_HOST', 'postgres')
DB_PORT = os.environ.get('DB_PORT', '5432')
DB_NAME = os.environ.get('DB_NAME', 'todos')
DB_USER = os.environ.get('DB_USER', 'user') # Example user
DB_PASS = os.environ.get('DB_PASS', 'password') # Example password

def get_db_connection():
    """Establishes connection to the PostgreSQL database with retries."""
    retries = 5
    delay = 1 # seconds
    while retries > 0:
        try:
            conn = psycopg2.connect(
                host=DB_HOST,
                port=DB_PORT,
                dbname=DB_NAME,
                user=DB_USER,
                password=DB_PASS,
                connect_timeout=3 # Add a connection timeout
            )
            print("Database connection successful.")
            return conn
        except psycopg2.OperationalError as e:
            retries -= 1
            print(f"Database connection failed: {e}. Retrying in {delay}s... ({retries} retries left)")
            if retries == 0:
                print("Max retries reached. Could not connect to database.")
                return None
            time.sleep(delay)
            delay *= 2 # Exponential backoff (optional)

def init_db():
    """Initializes the database table if it doesn't exist."""
    conn = get_db_connection()
    if conn is None:
        print("Skipping DB initialization due to connection error.")
        return
    try:
        with conn.cursor() as cur:
            # Create table only if it doesn't exist
            cur.execute("""
                CREATE TABLE IF NOT EXISTS todos (
                    id SERIAL PRIMARY KEY,
                    task TEXT NOT NULL,
                    added_on TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
        conn.commit() # Make sure changes are saved
        print("Database table 'todos' checked/created successfully.")
    except psycopg2.Error as e:
        print(f"Error initializing database table: {e}")
        conn.rollback() # Roll back changes on error
    finally:
        if conn:
            conn.close() # Always close the connection

# --- Simple HTML Template ---
# (For a real app, use Flask's template engine with separate HTML files)
HTML_TEMPLATE = """
<!doctype html>
<html>
<head><title>Simple TODO App</title></head>
<body>
    <h1>TODO List</h1>
    <ul>
        {% for todo in todos %}
            <li>{{ todo[1] }} (ID: {{ todo[0] }})</li> {# Accessing tuple elements #}
        {% else %}
            <li>No tasks yet! Add one below.</li>
        {% endfor %}
    </ul>
    <h2>Add New Task</h2>
    <form action="/add" method="post">
        <input type="text" name="task" placeholder="Enter new task description" required>
        <button type="submit">Add Task</button>
    </form>
</body>
</html>
"""

# --- Flask Routes ---
@app.route('/')
def index():
    """Displays the list of TODO items."""
    todos_list = []
    conn = get_db_connection()
    if conn:
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT id, task FROM todos ORDER BY added_on DESC;")
                todos_list = cur.fetchall() # Fetch all rows
        except psycopg2.Error as e:
            print(f"Error fetching todos: {e}")
            # Render template even if DB fetch fails, showing empty list or error
        finally:
            if conn:
                conn.close()

    # Render the HTML template, passing the list of todos
    return render_template_string(HTML_TEMPLATE, todos=todos_list)

@app.route('/add', methods=['POST'])
def add_todo():
    """Adds a new TODO item."""
    new_task = request.form.get('task') # Get task from form data
    if new_task: # Basic validation: check if task is not empty
        conn = get_db_connection()
        if conn:
            try:
                with conn.cursor() as cur:
                    # Use parameterized query to prevent SQL injection
                    cur.execute("INSERT INTO todos (task) VALUES (%s);", (new_task,))
                conn.commit() # Save the changes
                print(f"Added task: {new_task}")
            except psycopg2.Error as e:
                print(f"Error adding task: {e}")
                conn.rollback() # Roll back on error
            finally:
                if conn:
                    conn.close()
    else:
        print("Attempted to add an empty task.")

    # Redirect back to the index page to show the updated list
    return redirect(url_for('index'))

# --- Main Execution ---
if __name__ == "__main__":
    print("Attempting to initialize database...")
    init_db() # Try to create the table if it doesn't exist on startup
    print("Starting Flask development server...")
    # Run the app, listening on all interfaces (0.0.0.0) on port 5000.
    # debug=True enables auto-reloading and provides detailed error pages (disable in production)
    app.run(host="0.0.0.0", port=5000, debug=True)