import sqlite3
import time
import os
import logging
import json
import jwt
import re
import argparse
from datetime import datetime
from typing import Dict, Tuple, List

# Logging setup for Agent D (Publisher Simulator)
USER_ID = 'agent_d_publisher'
logger = logging.getLogger('publisher_sim')
logger.setLevel(logging.INFO)

log_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'logs'))
os.makedirs(log_dir, exist_ok=True)
file_handler = logging.FileHandler(os.path.join(log_dir, 'publisher_sim.txt'), encoding='utf-8')
file_handler.setLevel(logging.INFO)

formatter = logging.Formatter('%(asctime)s - %(levelname)s - User: %(user)s - %(message)s')
file_handler.setFormatter(formatter)
file_handler.addFilter(lambda record: setattr(record, 'user', USER_ID) or True)

logger.handlers = [file_handler]

# Constants
CONTENT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'content', 'content_ready'))
DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'scheduler_db', 'scheduled_posts.db'))
SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key')

def get_content_file(content_id: str, content_type: str, lang: str, platform: str) -> str:
    """Find the content file for a given content ID, type, language, and platform with precise pattern matching."""
    lang_dir = os.path.join(CONTENT_DIR, lang)
    absolute_lang_dir = os.path.abspath(lang_dir)
    try:
        logger.info(f"Listing all files in {absolute_lang_dir} for content_id={content_id}, content_type={content_type}, platform={platform}")
        files = os.listdir(absolute_lang_dir)
        logger.info(f"Files found: {files}")
        # Pattern: {content_type}_{content_id}_{platform}_*.json
        pattern = re.compile(rf'^{content_type}_{content_id}_{platform}_[0-9a-f]+\.json$')
        for filename in files:
            logger.info(f"Checking file: {filename}")
            if pattern.match(filename):
                logger.info(f"Matched content file: {filename} for content_id={content_id}, content_type={content_type}, platform={platform}, lang={lang}")
                return os.path.join(absolute_lang_dir, filename)
            else:
                logger.info(f"File {filename} did not match pattern: {pattern.pattern}")
        logger.error(f"No content file matched in {absolute_lang_dir} for content_id={content_id}, content_type={content_type}, platform={platform}")
    except FileNotFoundError:
        logger.warning(f"Content directory {absolute_lang_dir} not found")
    return ''

def get_audio_file(content_id: str, lang: str, platform: str) -> str:
    """Find the audio file for a given content ID, language, and platform."""
    lang_dir = os.path.join(CONTENT_DIR, lang)
    absolute_lang_dir = os.path.abspath(lang_dir)
    try:
        for filename in os.listdir(absolute_lang_dir):
            if filename.startswith(f"voice_{content_id}_{platform}_") and filename.endswith('.mp3'):
                full_path = os.path.join(absolute_lang_dir, filename)
                logger.info(f"Found audio file: {full_path}")
                return full_path
        logger.warning(f"No audio file found in {absolute_lang_dir} for content_id={content_id}, platform={platform}")
    except FileNotFoundError:
        logger.warning(f"Content directory {absolute_lang_dir} not found")
    return ''

def generate_jwt_token() -> str:
    """Generate a JWT token for authentication."""
    try:
        payload = {
            'sub': 'publisher',
            'iat': int(time.time()),
            'exp': int(time.time()) + 3600
        }
        token = jwt.encode(payload, SECRET_KEY, algorithm='HS256')
        logger.info("Obtained JWT token")
        return token
    except Exception as e:
        logger.error(f"Failed to generate JWT token: {str(e)}")
        raise

def publish_to_platform(platform: str, content: Dict, content_type: str, audio_file: str, token: str) -> bool:
    """Simulate publishing content to a platform using the pre-tailored content."""
    try:
        content_text = content.get(content_type if content_type != 'voice' else 'voice_script', '')

        logger.info(f"Simulating publishing {content_type} ID {content.get('id', 'unknown')} to {platform}: {content_text[:50]}...")
        logger.info(f"Using JWT token for authentication: {token[:10]}...")
        if platform == 'sanatan' and content_type == 'voice':
            if not audio_file or not os.path.exists(audio_file):
                logger.error(f"Audio file missing for voice content ID {content.get('id', 'unknown')} on {platform}")
                return False
            logger.info(f"Simulated upload of audio file {audio_file} to {platform}")
        logger.info(f"Successfully simulated publishing {content_type} ID {content.get('id', 'unknown')} to {platform}")
        return True
    except Exception as e:
        logger.error(f"Failed to simulate publishing {content_type} to {platform}: {str(e)}")
        return False

def update_status(content_id: str, platform: str, lang: str, status: str) -> None:
    """Update the status of a scheduled post using the lang column."""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute(
            "UPDATE scheduled_posts SET status = ? WHERE content_id = ? AND platform = ? AND lang = ?",
            (status, content_id, platform, lang)
        )
        conn.commit()
        conn.close()
        logger.info(f"Updated status to {status} for content ID {content_id} on {platform} (lang: {lang})")
    except Exception as e:
        logger.error(f"Failed to update status for content ID {content_id} on {platform} (lang: {lang}): {str(e)}")

def fetch_due_posts(selected_language: str) -> List[Tuple[str, str, str, str]]:
    """Fetch posts that are due for publishing, filtered by language."""
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    due_posts = []
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        if selected_language == 'all':
            c.execute(
                "SELECT content_id, platform, content_type, lang FROM scheduled_posts WHERE status = ? AND scheduled_time <= ?",
                ('pending', now)
            )
        else:
            c.execute(
                "SELECT content_id, platform, content_type, lang FROM scheduled_posts WHERE status = ? AND scheduled_time <= ? AND lang = ?",
                ('pending', now, selected_language)
            )
        due_posts = c.fetchall()
        conn.close()
    except Exception as e:
        logger.error(f"Failed to fetch due posts: {str(e)}")
    return due_posts

def publish_content(content_id: str, platform: str, content_type: str, token: str, lang: str) -> bool:
    """Publish content to the specified platform."""
    success = False
    content_file = get_content_file(content_id, content_type, lang, platform)
    if not content_file:
        logger.error(f"No content file found for content ID {content_id} on {platform} (lang: {lang})")
        update_status(content_id, platform, lang, 'failed')
        return False
    try:
        with open(content_file, 'r', encoding='utf-8') as f:
            content = json.load(f)
        audio_file = get_audio_file(content_id, lang, platform) if content_type == 'voice' else ''
        if content_type == 'voice' and platform == 'sanatan' and not audio_file:
            logger.error(f"No audio file found for voice content ID {content_id} on {platform} (lang: {lang})")
            update_status(content_id, platform, lang, 'failed')
            return False
        if publish_to_platform(platform, content, content_type, audio_file, token):
            update_status(content_id, platform, lang, 'published')
            success = True
        else:
            update_status(content_id, platform, lang, 'failed')
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logger.error(f"Failed to load content file {content_file}: {str(e)}")
        update_status(content_id, platform, lang, 'failed')
    return success

def run_publisher_sim(selected_language: str, max_attempts: int = 3) -> None:
    """Run Agent D: Publisher Simulator for the specified language."""
    logger.info(f"Starting Agent D: Publisher Simulator for language: {selected_language}")
    token = generate_jwt_token()

    processed_posts = []
    for attempt in range(1, max_attempts + 1):
        due_posts = fetch_due_posts(selected_language)
        if not due_posts:
            logger.info(f"Attempt {attempt}/{max_attempts}: No posts due for language {selected_language}")
            if attempt < max_attempts:
                time.sleep(5)
            continue

        for content_id, platform, content_type, lang in due_posts:
            success = publish_content(content_id, platform, content_type, token, lang)
            status = 'published' if success else 'failed'
            processed_posts.append(f"ID {content_id} ({platform}, {content_type}, {status}, lang: {lang})")

        logger.info(f"Attempt {attempt}/{max_attempts}: Processed {len(due_posts)} posts: {', '.join(processed_posts)}")
        break

    if not processed_posts:
        logger.warning(f"No posts processed after {max_attempts} attempts for language {selected_language}")

def main() -> None:
    """Main function to run the publisher simulator with a language argument."""
    parser = argparse.ArgumentParser(description="Run Agent D: Publisher Simulator")
    parser.add_argument('language', choices=['en', 'hi', 'sa', 'all'], help="Language to process (en, hi, sa, all)")
    args = parser.parse_args()

    run_publisher_sim(args.language)

if __name__ == "__main__":
    main()