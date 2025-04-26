import sqlite3
import json
import os
from datetime import datetime, timedelta
import logging

# Custom filter to add user field to log records
class UserFilter(logging.Filter):
    def __init__(self, user_id):
        super().__init__()
        self.user_id = user_id

    def filter(self, record):
        record.user = self.user_id
        return True

# Configure logging
USER_ID = "agent_d_scheduler"
logger = logging.getLogger('scheduler')
logger.setLevel(logging.INFO)

# Create file handler
os.makedirs('logs', exist_ok=True)
file_handler = logging.FileHandler("logs/log.txt")
file_handler.setLevel(logging.INFO)

# Create formatter with the custom format
formatter = logging.Formatter('%(asctime)s - %(levelname)s - User: %(user)s - %(message)s')
file_handler.setFormatter(formatter)

# Add the custom filter to inject the user field
file_handler.addFilter(UserFilter(USER_ID))

# Add a stream handler for console output
stream_handler = logging.StreamHandler()
stream_handler.setLevel(logging.INFO)
stream_handler.setFormatter(formatter)
stream_handler.addFilter(UserFilter(USER_ID))

# Add handlers to the logger
logger.handlers = []
logger.addHandler(file_handler)
logger.addHandler(stream_handler)

# Database setup
DB_PATH = "scheduler_db/scheduled_posts.db"
CONTENT_READY_DIR = "content/content_ready"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS scheduled_posts (
            content_id INTEGER,
            platform TEXT,
            content_type TEXT,
            scheduled_time TEXT,
            status TEXT
        )
    ''')
    conn.commit()
    conn.close()
    logger.info(f"Initialized database at {DB_PATH}")

def schedule_content():
    logger.info("Starting scheduler")
    
    # Load content files from content_ready
    content_files = []
    for filename in os.listdir(CONTENT_READY_DIR):
        if filename.endswith('.json') and "encrypted" not in filename:
            parts = filename.split('_')
            if len(parts) != 4:  # e.g., tweet_1_20250423_000047.json
                continue
            content_type = parts[0]  # tweet, post, voice
            content_id = int(parts[1])  # 1, 3, etc.
            content_files.append((filename, content_type, content_id))
    
    # Process MP3 files (voice audio) separately to avoid duplicates
    voice_audio_files = []
    for filename in os.listdir(CONTENT_READY_DIR):
        if filename.endswith('.mp3'):
            parts = filename.split('_')
            if len(parts) != 4:
                continue
            content_type = parts[0]
            content_id = int(parts[1])
            if content_type == "voice":
                voice_audio_files.append((filename, content_type, content_id))
    
    if not content_files and not voice_audio_files:
        logger.warning(f"No content files found in {CONTENT_READY_DIR}")
        return

    # Get current time and set scheduled time to now (or slightly in the past)
    now = datetime.now()
    scheduled_time = now.strftime('%Y-%m-%d %H:%M:%S')  # Current time

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Clear existing scheduled posts to avoid duplicates
    c.execute("DELETE FROM scheduled_posts")
    conn.commit()

    # Schedule JSON content (posts, tweets, voice scripts)
    for _, content_type, content_id in content_files:
        platform = 'Instagram' if content_type == 'post' else 'Twitter' if content_type == 'tweet' else 'Spotify'
        
        c.execute(
            "INSERT INTO scheduled_posts (content_id, platform, content_type, scheduled_time, status) VALUES (?, ?, ?, ?, ?)",
            (content_id, platform, content_type, scheduled_time, 'pending')
        )
        logger.info(f"Scheduled {content_type} ID {content_id} for {platform} at {scheduled_time}")
    
    # Schedule MP3 content (voice audio), avoiding duplicates with voice scripts
    processed_voice_ids = set(item[2] for item in content_files if item[1] == "voice")
    for _, content_type, content_id in voice_audio_files:
        if content_id in processed_voice_ids:
            continue
        platform = 'Spotify'
        
        c.execute(
            "INSERT INTO scheduled_posts (content_id, platform, content_type, scheduled_time, status) VALUES (?, ?, ?, ?, ?)",
            (content_id, platform, content_type, scheduled_time, 'pending')
        )
        logger.info(f"Scheduled {content_type} ID {content_id} for {platform} at {scheduled_time}")
    
    conn.commit()
    conn.close()
    logger.info(f"Scheduler completed at {datetime.now()}")

if __name__ == "__main__":
    init_db()
    schedule_content()