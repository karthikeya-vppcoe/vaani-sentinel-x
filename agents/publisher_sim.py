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
logger.handlers = [file_handler, logging.StreamHandler()]
logger.info("Initializing publisher_sim.py")

# Constants
CONTENT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'content', 'content_final'))
TRANSLATED_CONTENT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data', 'translated_content.json'))
TTS_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data', 'tts_simulation_output.json'))
SCHEDULED_POSTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'scheduled_posts'))
DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'scheduler_db', 'scheduled_posts.db'))
SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key')

def load_json(file_path: str) -> Dict:
    """Load JSON file."""
    logger.debug(f"Loading JSON: {file_path}")
    if not os.path.exists(file_path):
        logger.warning(f"File not found: {file_path}")
        return {}
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load {file_path}: {str(e)}")
        return {}

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

def get_audio_file(content_id: str, lang: str, platform: str, tts_data: List[Dict]) -> str:
    """Find the audio file or dummy_audio_path for a given content ID, language, and platform."""
    for item in tts_data:
        if item.get('content_id') == content_id and item.get('language') == lang and item.get('platform') == platform:
            audio_path = item.get('dummy_audio_path', '')
            if audio_path:
                logger.info(f"Found dummy_audio_path in TTS data: {audio_path}")
                return audio_path
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

def load_translated_content(content_id: str, lang: str) -> Dict:
    """Load translated content for a given content ID and language."""
    try:
        translated_data = load_json(TRANSLATED_CONTENT)
        if not translated_data:
            logger.warning(f"No translated content available, falling back to original content for content_id={content_id}, lang={lang}")
            return {}
        for item in translated_data:
            if item.get('content_id') == content_id and item.get('language') == lang:
                logger.info(f"Found translated content for content_id={content_id}, lang={lang}")
                return item
        logger.warning(f"No translated content found for content_id={content_id}, lang={lang}")
        return {}
    except Exception as e:
        logger.warning(f"Failed to load translated content: {str(e)}, falling back to original content")
        return {}

def load_tts_content() -> List[Dict]:
    """Load TTS content from tts_simulation_output.json."""
    try:
        tts_data = load_json(TTS_FILE)
        if not isinstance(tts_data, list):
            logger.error(f"Invalid format in {TTS_FILE}: expected list, got {type(tts_data)}")
            return []
        logger.info(f"Loaded {len(tts_data)} items from {TTS_FILE}")
        return tts_data
    except Exception as e:
        logger.warning(f"Failed to load TTS content from {TTS_FILE}: {str(e)}")
        return []

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

def format_content(content: Dict, content_type: str, platform: str, audio_file: str, lang: str, translation: Dict = None, tts_item: Dict = None) -> Dict:
    """Format content for platform-specific posting, using translation and TTS data."""
    content_id = content.get('content_id', content.get('id', 'unknown'))
    content_text = translation.get('translated_text', content.get(content_type if content_type != 'voice_script' else 'voice_script', '')) if translation else content.get(content_type if content_type != 'voice_script' else 'voice_script', '')
    tone = translation.get('sentiment', content.get('sentiment', 'neutral')) if translation else content.get('sentiment', 'neutral')
    voice_tag = tts_item.get('voice_tag', '') if tts_item else content.get('voice_tag', '')
    dummy_audio_path = tts_item.get('dummy_audio_path', audio_file) if tts_item else audio_file
    preferred_languages = translation.get('preferred_languages', content.get('preferred_languages', [])) if translation else content.get('preferred_languages', [])

    logger.info(f"Formatting content ID {content_id}, platform: {platform}, lang: {lang}, tone: {tone}, voice_tag: {voice_tag}")

    post_data = {
        'post_id': str(uuid.uuid4()),
        'content_id': content_id,
        'platform': platform,
        'language': lang,
        'tone': tone,
        'voice_tag': voice_tag,
        'dummy_audio_path': dummy_audio_path,
        'preferred_languages': preferred_languages,
        'publish_time': datetime.now().isoformat(),
        'status': 'pending'
    }

    if platform == 'instagram':
        post_data['content'] = f"{content_text}\n#Inspiration #Multilingual"
        post_data['audio_thumbnail'] = dummy_audio_path if content_type == 'voice_script' else ''
        post_data['format'] = 'multilingual text + audio thumbnail'
    elif platform == 'twitter':
        post_data['content'] = content_text[:280] if content_type == 'tweet' else content_text
        post_data['audio_snippet'] = dummy_audio_path if content_type == 'voice_script' else ''
        post_data['format'] = 'multilingual short text + TTS snippet'
    elif platform == 'linkedin':
        post_data['content'] = {
            'title': f"Multilingual Insight {content_id}",
            'summary': content_text
        }
        post_data['audio'] = dummy_audio_path if content_type == 'voice_script' else ''
        post_data['format'] = 'multilingual title + summary + TTS'
    elif platform == 'sanatan':
        post_data['content'] = content_text
        post_data['audio'] = dummy_audio_path if content_type == 'voice_script' else ''
        post_data['format'] = 'multilingual voice script + audio'

    return post_data

def publish_to_platform(platform: str, content: Dict, content_type: str, audio_file: str, token: str, preview_mode: bool, lang: str, translation: Dict = None, tts_item: Dict = None) -> bool:
    """Simulate publishing content to a platform, using translation and TTS data."""
    try:
        post_data = format_content(content, content_type, platform, audio_file, lang, translation, tts_item)
        content_id = content.get('content_id', content.get('id', 'unknown'))
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
        logger.info(f"Fetched {len(due_posts)} due posts for language {selected_language}: {due_posts}")
    except Exception as e:
        logger.error(f"Failed to fetch due posts: {str(e)}")
    return due_posts

def publish_content(content_id: str, platform: str, content_type: str, token: str, lang: str, preview_mode: bool, tts_data: List[Dict]) -> bool:
    """Publish content to the specified platform."""
    content_file = get_content_file(content_id, content_type, lang, platform)
    if not content_file:
        logger.error(f"No content file found for content ID {content_id} on {platform} (lang: {lang})")
        update_status(content_id, platform, lang, 'failed')
        return False
    try:
        content = load_json(content_file)
        translation = load_translated_content(content_id, lang)
        tts_item = next((item for item in tts_data if item.get('content_id') == content_id and item.get('language') == lang and item.get('platform') == platform), None)
        
        audio_file = get_audio_file(content_id, lang, platform, tts_data) if content_type == 'voice_script' else ''
        if content_type == 'voice_script' and platform == 'sanatan' and not audio_file:
            logger.error(f"No audio file found for voice_script content ID {content_id} on {platform} (lang: {lang})")
            update_status(content_id, platform, lang, 'failed')
            return False
        
        if publish_to_platform(platform, content, content_type, audio_file, token, preview_mode, lang, translation, tts_item):
            update_status(content_id, platform, lang, 'published' if not preview_mode else 'preview')
            return True
        else:
            update_status(content_id, platform, lang, 'failed')
            return False
    except Exception as e:
        logger.error(f"Failed to load content file {content_file}: {str(e)}")
        update_status(content_id, platform, lang, 'failed')
        return False

def generate_multilingual_previews(content_id: str, content_type: str = 'post') -> List[Dict]:
    """Generate 5 multilingual post previews for different languages and platforms."""
    logger.info(f"Generating multilingual previews for content_id: {content_id}")
    token = generate_jwt_token()
    tts_data = load_tts_content()
    
    preview_configs = [
        {'lang': 'en', 'platform': 'instagram', 'content_type': 'post'},
        {'lang': 'hi', 'platform': 'linkedin', 'content_type': 'post'},
        {'lang': 'sa', 'platform': 'sanatan', 'content_type': 'voice_script'},
        {'lang': 'mr', 'platform': 'instagram', 'content_type': 'post'},
        {'lang': 'ta', 'platform': 'linkedin', 'content_type': 'post'}
    ]
    
    previews = []
    for config in preview_configs:
        lang = config['lang']
        platform = config['platform']
        content_type = config['content_type']
        
        content_file = get_content_file(content_id, content_type, lang, platform)
        if not content_file:
            logger.warning(f"No content file for preview: content_id={content_id}, lang={lang}, platform={platform}")
            continue
        
        content = load_json(content_file)
        translation = load_translated_content(content_id, lang)
        tts_item = next((item for item in tts_data if item.get('content_id') == content_id and item.get('language') == lang and item.get('platform') == platform), None)
        
        audio_file = get_audio_file(content_id, lang, platform, tts_data) if content_type == 'voice_script' else ''
        
        success = publish_to_platform(platform, content, content_type, audio_file, token, preview_mode=True, lang=lang, translation=translation, tts_item=tts_item)
        if success:
            for filename in os.listdir(SCHEDULED_POSTS_DIR):
                if filename.startswith(f"post_{content_id}_{platform}_") and filename.endswith('.json'):
                    post_file = os.path.join(SCHEDULED_POSTS_DIR, filename)
                    post_data = load_json(post_file)
                    previews.append(post_data)
                    logger.info(f"Added preview for {lang} on {platform}")
                    break
    
    logger.info(f"Generated {len(previews)} multilingual previews for content_id: {content_id}")
    return previews

def run_publisher_sim(selected_language: str, preview_mode: bool = False, max_attempts: int = 3) -> None:
    """Run Agent J: Platform Publisher."""
    logger.info(f"Starting Agent J: Platform Publisher for language: {selected_language} (preview_mode: {preview_mode})")
    
    if os.path.exists(SCHEDULED_POSTS_DIR):
        shutil.rmtree(SCHEDULED_POSTS_DIR)
        logger.info(f"Cleared scheduled_posts directory: {SCHEDULED_POSTS_DIR}")
    os.makedirs(SCHEDULED_POSTS_DIR, exist_ok=True)

    token = generate_jwt_token()
    tts_data = load_tts_content()

    processed_posts = []
    for attempt in range(1, max_attempts + 1):
        due_posts = fetch_due_posts(selected_language)
        if not due_posts:
            logger.info(f"Attempt {attempt}/{max_attempts}: No posts due for language {selected_language}")
            if attempt < max_attempts:
                time.sleep(5)
            continue

        for content_id, platform, content_type, lang in due_posts:
            success = publish_content(content_id, platform, content_type, token, lang, preview_mode, tts_data)
            status = 'published' if success and not preview_mode else 'preview' if success else 'failed'
            processed_posts.append(f"ID {content_id} ({platform}, {content_type}, {status}, lang: {lang})")

        logger.info(f"Attempt {attempt}/{max_attempts}: Processed {len(due_posts)} posts: {', '.join(processed_posts)}")
        break

    if not processed_posts:
        logger.warning(f"No posts processed after {max_attempts} attempts for language {selected_language}")

def main() -> None:
    """Main function to run the publisher simulator."""
    parser = argparse.ArgumentParser(description="Run Agent J: Platform Publisher")
    parser.add_argument('language', nargs='?', choices=['en', 'hi', 'sa', 'all'], default=None, help="Language to process (en, hi, sa, all)")
    parser.add_argument('--preview', action='store_true', help="Run in preview mode (generate JSON without POST)")
    parser.add_argument('--multilingual-preview', action='store_true', help="Generate 5 multilingual post previews")
    parser.add_argument('--content-id', default='1b4239cf-7c8f-40c1-b265-757111149621', help="Content ID for multilingual previews")
    args = parser.parse_args()

    if args.multilingual_preview:
        if args.language is None:
            generate_multilingual_previews(args.content_id)
        else:
            print("Error: --multilingual-preview does not require a language argument")
            return
    else:
        if args.language is None:
            print("Error: language argument is required when not using --multilingual-preview")
            parser.print_help()
            return
        run_publisher_sim(args.language, args.preview)

if __name__ == "__main__":
    main()