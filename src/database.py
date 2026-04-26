import sqlite3
from pathlib import Path

# Use the data directory we defined earlier
BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "processed_emails.db"


def init_db():
    """Creates the database and table if they don't exist"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS processed_emails (
            message_id TEXT PRIMARY KEY,
            classification TEXT,
            processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """
    )
    conn.commit()
    conn.close()


def is_processed(message_id):
    """Checks if an email has already been handled"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM processed_emails WHERE message_id = ?", (message_id, ))
    result = cursor.fetchone()
    conn.close()
    return result is not None


def mark_as_processed(message_id, classification):
    """Logs the message ID and its classification"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO processed_emails (message_id, classification) VALUES (?, ?)",
            (message_id, classification, ),
        )
        conn.commit()
    except sqlite3.IntegrityError:
        pass  # Already exists
    finally:
        conn.close()
