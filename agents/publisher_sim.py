import sqlite3
import os
import logging
import json
import jwt
import re
import argparse
import requests
import time
import uuid
import shutil
from datetime import datetime
from typing import Dict, Tuple, List

# Logging setup for Agent J (Platform Publisher)
USER_ID = 'agent_j_publisher'
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
SCHEDULED_POSTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'scheduled_posts'))
DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'scheduler_db', 'scheduled_posts.db'))
SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key')

def get_content_file(content_id: str, content_type: str, lang: str, platform: str) -> str:
    """Find the content file with precise pattern matching."""
    lang_dir = os.path.join(CONTENT_DIR, lang)
    try:
        files = os.listdir(lang_dir)
        pattern = re.compile(rf'^{content_type}_{content_id}_{platform}_[0-9a-f]+\.json$')
        for filename in files:
            if pattern.match(filename):
                logger.info(f"Matched content file: {filename} for content_id={content_id}, content_type={content_type}, platform={platform}, lang={lang}")
                return os.path.join(lang_dir, filename)
        logger.error(f"No content file matched in {lang_dir} for content_id={content_id}, content_type={content_type}, platform={platform}")
    except FileNotFoundError:
        logger.warning(f"Content directory {lang_dir} not found")
    return ''

def get_audio_file(content_id: str, lang: str, platform: str) -> str:
    """Find the audio file for a given content ID, language, and platform."""
    lang_dir = os.path.join(CONTENT_DIR, lang)
    try:
        for filename in os.listdir(lang_dir):
            if filename.startswith(f"voice_{content_id}_{platform}_") and filename.endswith('.mp3'):
                full_path = os.path.join(lang_dir, filename)
                logger.info(f"Found audio file: {full_path}")
                return full_path
        logger.warning(f"No audio file found in {lang_dir} for content_id={content_id}, platform={platform}")
    except FileNotFoundError:
        logger.warning(f"Content directory {lang_dir} not found")
    return ''

def generate_jwt_token() -> str:
    """Generate a JWT token for authentication."""
    try:
        payload = {
            'sub': 'publisher',
            'iat': int(datetime.now().timestamp()),
            'exp': int(datetime.now().timestamp()) + 3600
        }
        token = jwt.encode(payload, SECRET_KEY, algorithm='HS256')
        logger.info("Generated JWT token")
        return token
    except Exception as e:
        logger.error(f"Failed to generate JWT token: {str(e)}")
        raise

def format_content(content: Dict, content_type: str, platform: str, audio_file: str, lang: str) -> Dict:
    """Format content for platform-specific posting."""
    content_id = content.get('id', 'unknown')
    content_text = content.get(content_type if content_type != 'voice' else 'voice_script', '')
    sentiment = content.get('sentiment')  # Remove default 'neutral' to ensure we use the content file's value
    if sentiment is None:
        logger.error(f"No sentiment field found in content for ID {content_id}, platform {platform}, lang {lang}")
        sentiment = 'neutral'  # Fallback only if the field is missing

    logger.info(f"Read sentiment '{sentiment}' for content ID {content_id}, platform {platform}, lang {lang}")

    post_data = {
        'post_id': str(uuid.uuid4()),
        'content_id': content_id,
        'platform': platform,
        'language': lang,
        'sentiment': sentiment,
        'publish_time': datetime.now().isoformat(),
        'status': 'pending'
    }

    if platform == 'instagram':
        post_data['content'] = f"{content_text}\n#Inspiration #Motivation"
        post_data['audio_thumbnail'] = audio_file if content_type == 'voice' else ''
        post_data['format'] = 'text + audio thumbnail'
    elif platform == 'twitter':
        post_data['content'] = content_text[:280] if content_type == 'tweet' else content_text
        post_data['audio_snippet'] = audio_file if content_type == 'voice' else ''
        post_data['format'] = 'short text + TTS snippet'
    elif platform == 'linkedin':
        post_data['content'] = {
            'title': f"Insight {content_id}",
            'summary': content_text
        }
        post_data['audio'] = audio_file if content_type == 'voice' else ''
        post_data['format'] = 'title + summary + TTS'
    elif platform == 'sanatan':
        post_data['content'] = content_text
        post_data['audio'] = audio_file if content_type == 'voice' else ''
        post_data['format'] = 'voice script + audio'

    return post_data

def publish_to_platform(platform: str, content: Dict, content_type: str, audio_file: str, token: str, preview_mode: bool, lang: str) -> bool:
    """Simulate publishing content to a platform."""
    try:
        post_data = format_content(content, content_type, platform, audio_file, lang)
        content_id = content.get('id', 'unknown')
        content_text = post_data['content'] if isinstance(post_data['content'], str) else json.dumps(post_data['content'])

        if not preview_mode:
            endpoint = f'http://localhost:5000/{platform}/post'
            headers = {'Authorization': f'Bearer {token}'}
            payload = {'contentId': content_id}
            
            simulated_response = {'status_code': 200, 'text': 'Success'} if platform in ['twitter', 'instagram', 'linkedin', 'sanatan'] else {'status_code': 500, 'text': 'Failed'}

            if simulated_response['status_code'] == 200:
                logger.info(f"Simulated POST to {platform} for content ID {content_id}: {content_text[:50]}...")
                post_data['status'] = 'success'
            else:
                logger.error(f"Failed POST to {platform} for content ID {content_id}: {simulated_response['text']}")
                post_data['status'] = 'failed'
                return False
        else:
            logger.info(f"Preview mode: Generated post for {platform} (ID {content_id}): {content_text[:50]}...")
            post_data['status'] = 'preview'

        os.makedirs(SCHEDULED_POSTS_DIR, exist_ok=True)
        output_path = os.path.join(SCHEDULED_POSTS_DIR, f"post_{content_id}_{platform}_{post_data['post_id']}.json")
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(post_data, f, ensure_ascii=False, indent=2)
        logger.info(f"Saved post to {output_path}")

        return True
    except Exception as e:
        logger.error(f"Failed to publish {content_type} to {platform}: {str(e)}")
        return False

def update_status(content_id: str, platform: str, lang: str, status: str) -> None:
    """Update the status of a scheduled post."""
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
    """Fetch posts that are due for publishing."""
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    due_posts = []
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        query = "SELECT content_id, platform, content_type, lang FROM scheduled_posts WHERE status = ? AND scheduled_time <= ?"
        params = ('pending', now)
        if selected_language != 'all':
            query += " AND lang = ?"
            params += (selected_language,)
        c.execute(query, params)
        due_posts = c.fetchall()
        conn.close()
    except Exception as e:
        logger.error(f"Failed to fetch due posts: {str(e)}")
    return due_posts

def publish_content(content_id: str, platform: str, content_type: str, token: str, lang: str, preview_mode: bool) -> bool:
    """Publish content to the specified platform."""
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
        if publish_to_platform(platform, content, content_type, audio_file, token, preview_mode, lang):
            update_status(content_id, platform, lang, 'published' if not preview_mode else 'preview')
            return True
        else:
            update_status(content_id, platform, lang, 'failed')
            return False
    except Exception as e:
        logger.error(f"Failed to load content file {content_file}: {str(e)}")
        update_status(content_id, platform, lang, 'failed')
        return False

def run_publisher_sim(selected_language: str, preview_mode: bool = False, max_attempts: int = 3) -> None:
    """Run Agent J: Platform Publisher."""
    logger.info(f"Starting Agent J: Platform Publisher for language: {selected_language} (preview_mode: {preview_mode})")
    
    # Clear the scheduled_posts directory
    if os.path.exists(SCHEDULED_POSTS_DIR):
        shutil.rmtree(SCHEDULED_POSTS_DIR)
        logger.info(f"Cleared scheduled_posts directory: {SCHEDULED_POSTS_DIR}")
    os.makedirs(SCHEDULED_POSTS_DIR, exist_ok=True)

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
            success = publish_content(content_id, platform, content_type, token, lang, preview_mode)
            status = 'published' if success and not preview_mode else 'preview' if success else 'failed'
            processed_posts.append(f"ID {content_id} ({platform}, {content_type}, {status}, lang: {lang})")

        logger.info(f"Attempt {attempt}/{max_attempts}: Processed {len(due_posts)} posts: {', '.join(processed_posts)}")
        break

    if not processed_posts:
        logger.warning(f"No posts processed after {max_attempts} attempts for language {selected_language}")

def main() -> None:
    """Main function to run the publisher simulator."""
    parser = argparse.ArgumentParser(description="Run Agent J: Platform Publisher")
    parser.add_argument('language', choices=['en', 'hi', 'sa', 'all'], help="Language to process (en, hi, sa, all)")
    parser.add_argument('--preview', action='store_true', help="Run in preview mode (generate JSON without POST)")
    args = parser.parse_args()

    run_publisher_sim(args.language, args.preview)

if __name__ == "__main__":
    main()