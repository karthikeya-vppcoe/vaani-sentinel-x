import sqlite3
import requests
import re
from datetime import datetime, timedelta
import logging
import json
from pathlib import Path
import time
import os
import glob
from textblob import TextBlob

# Custom filter to add user field to log records
class UserFilter(logging.Filter):
    def __init__(self, user_id):
        super().__init__()
        self.user_id = user_id

    def filter(self, record):
        record.user = self.user_id
        return True

# Configure logging
USER_ID = "agent_d_publisher"
logger = logging.getLogger('publisher_sim')
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

# Reduce verbosity of external libraries
logging.getLogger('requests').setLevel(logging.WARNING)
logging.getLogger('urllib3').setLevel(logging.WARNING)

# Database setup
DB_PATH = "scheduler_db/scheduled_posts.db"

# Controversial terms for ethics scoring
CONTROVERSIAL_TERMS = re.compile(
    r'\b(religion|religious|politics|political|bias|offensive|racist|sexist|controversial)\b',
    re.IGNORECASE
)

def get_pending_posts(grace_period_seconds=10):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    now = datetime.now()
    cutoff_time = (now + timedelta(seconds=grace_period_seconds)).strftime('%Y-%m-%d %H:%M:%S')
    c.execute("SELECT * FROM scheduled_posts WHERE status = 'pending' AND scheduled_time <= ?", (cutoff_time,))
    posts = c.fetchall()
    conn.close()
    return posts

def load_content(file_path):
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logger.error(f"Failed to load {file_path}: {str(e)}")
        return None

def calculate_scores(content, content_type):
    """Calculate ethics, virality, and neutrality scores."""
    text = content.get(content_type if content_type != 'voice' else 'voice_script', '')

    # Ethics: Lower score if controversial terms are present
    ethics = 0.9
    if CONTROVERSIAL_TERMS.search(text):
        ethics = 0.3
        logger.info(f"Lowered ethics score for {content_type} due to controversial terms")

    # Virality: Based on length and keyword density
    words = text.split()
    word_count = len(words)
    keyword_density = sum(1 for word in words if word.lower() in ['new', 'exciting', 'breaking', 'exclusive']) / max(word_count, 1)
    virality = min(0.7, 0.4 + (word_count / 100) + keyword_density)

    # Neutrality: Based on sentiment analysis
    blob = TextBlob(text)
    polarity = blob.sentiment.polarity
    neutrality = 1.0 - abs(polarity)  # Closer to 0 is more neutral

    return {'ethics': round(ethics, 2), 'virality': round(virality, 2), 'neutrality': round(neutrality, 2)}

def get_auth_token():
    """Authenticate and get JWT token."""
    login_url = "http://localhost:5000/api/login"
    credentials = {"email": "test@vaani.com", "password": "password123"}
    try:
        response = requests.post(login_url, json=credentials)
        response.raise_for_status()
        token = response.json().get("token")
        logger.info(f"Obtained JWT token")
        return token
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to obtain JWT token: {e}")
        return None

def publish_content(content_id, platform, content_type, token):
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    data = {"contentId": str(content_id), "type": content_type}

    if platform == 'Instagram':
        url = 'http://localhost:5000/instagram/post'
    elif platform == 'Twitter':
        url = 'http://localhost:5000/twitter/post'
    elif platform == 'Spotify':
        url = 'http://localhost:5000/spotify/upload'
    else:
        raise ValueError(f"Unsupported platform: {platform}")

    try:
        response = requests.post(url, json=data, headers=headers)
        response.raise_for_status()
        logger.info(f"Successfully published content ID {content_id} to {platform}")
        return True
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to publish content ID {content_id} to {platform}: {str(e)}")
        return False

def update_status(content_id, platform, content_type, status):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "UPDATE scheduled_posts SET status = ? WHERE content_id = ? AND platform = ? AND content_type = ? AND status = 'pending'",
        (status, content_id, platform, content_type)
    )
    conn.commit()
    conn.close()
    logger.info(f"Updated status to '{status}' for content ID {content_id}")

def run_publisher(max_attempts=3, wait_seconds=5):
    logger.info("Starting publisher simulator")

    token = get_auth_token()
    if not token:
        logger.error("No valid JWT token, aborting publish")
        return

    for attempt in range(max_attempts):
        posts = get_pending_posts(grace_period_seconds=10)
        if posts:
            break
        logger.info(f"Attempt {attempt + 1}/{max_attempts}: No posts due for publishing at {datetime.now().isoformat()}")
        if attempt < max_attempts - 1:
            time.sleep(wait_seconds)

    if not posts:
        logger.warning(f"No posts found to publish after {max_attempts} attempts")
        return

    # Aggregate scores by content_id
    score_map = {}

    # Process scheduled posts
    for post in posts:
        content_id, platform, content_type, _, _ = post
        content_path = f"content/content_ready/{content_type}_{content_id}_*.json"
        content_files = glob.glob(content_path)
        if not content_files:
            logger.warning(f"No content file found for ID {content_id}, type {content_type}")
            continue

        content = load_content(content_files[0])
        if not content:
            continue

        scores = calculate_scores(content, content_type)
        if content_id in score_map:
            # Aggregate scores (average)
            existing = score_map[content_id]
            count = existing.get('count', 1) + 1
            existing['ethics'] = (existing['ethics'] * (count - 1) + scores['ethics']) / count
            existing['virality'] = (existing['virality'] * (count - 1) + scores['virality']) / count
            existing['neutrality'] = (existing['neutrality'] * (count - 1) + scores['neutrality']) / count
            existing['count'] = count
        else:
            score_map[content_id] = {**scores, 'count': 1}

        success = publish_content(content_id, platform, content_type, token)
        status = 'published' if success else 'failed'
        update_status(content_id, platform, content_type, status)

    # Convert score_map to list, removing count
    scores = [
        {
            "id": content_id,
            "ethics": round(score['ethics'], 2),
            "virality": round(score['virality'], 2),
            "neutrality": round(score['neutrality'], 2)
        }
        for content_id, score in score_map.items()
    ]

    # Save scores to content/scores.json
    scores_file = Path("content/scores.json")
    scores_file.parent.mkdir(parents=True, exist_ok=True)
    with open(scores_file, "w", encoding="utf-8") as f:
        json.dump(scores, f, indent=2)
    logger.info(f"Saved scores to {scores_file}")

    logger.info(f"Publisher simulator completed at {datetime.now()}")

if __name__ == "__main__":
    run_publisher()