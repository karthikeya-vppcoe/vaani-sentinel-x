import json
import sqlite3
import os
import logging
import re
import argparse
from datetime import datetime, timedelta
from typing import List, Dict
import uuid
import glob

# === Logging Setup for Agent D (Scheduler) ===
USER_ID = 'agent_d_user'
logger = logging.getLogger('scheduler')
logger.setLevel(logging.DEBUG)

log_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'logs'))
os.makedirs(log_dir, exist_ok=True)
log_path = os.path.join(log_dir, 'scheduler.txt')
file_handler = logging.FileHandler(log_path, encoding='utf-8')
file_handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - User: %(user)s - %(message)s')
file_handler.setFormatter(formatter)
file_handler.addFilter(lambda record: setattr(record, 'user', USER_ID) or True)
logger.handlers = [file_handler, logging.StreamHandler()]

class Scheduler:
    def __init__(self):
        """Initialize the Scheduler with supported languages."""
        self.supported_languages = [
            'en', 'hi', 'sa', 'mr', 'ta', 'te', 'kn', 'ml', 'bn', 'gu', 'pa',
            'es', 'fr', 'de', 'zh', 'ja', 'ru', 'ar', 'pt', 'it'
        ]
        self.schedule_counter = 0  # For sequential scheduling
        logger.info("Scheduler initialized with supported languages: %s", self.supported_languages)

    def validate_content(self, content_data: Dict, content_file: str) -> bool:
        """Validate content JSON schema, adding platform and content_type for TTS."""
        required_fields = ['content_id', 'language']
        content_type = content_data.get('content_type', 'voice_script' if 'voice_script' in content_data else '')
        content_data['content_type'] = content_type
        content_data['platform'] = content_data.get('platform', 'sanatan' if content_type == 'voice_script' else '')
        content_field = 'voice_script' if content_type == 'voice_script' else content_type
        if content_field not in content_data:
            required_fields.append(content_field)
        missing_fields = [field for field in required_fields if field not in content_data]
        if missing_fields:
            logger.warning("Missing fields %s in %s", missing_fields, content_file)
            return False
        if content_data['platform'] not in ['twitter', 'instagram', 'linkedin', 'sanatan']:
            logger.warning("Invalid platform in %s: %s", content_file, content_data['platform'])
            return False
        if content_data['language'] not in self.supported_languages:
            logger.warning("Invalid language in %s: %s", content_file, content_data['language'])
            return False
        if content_type not in ['tweet', 'post', 'voice_script']:
            logger.warning("Invalid content_type in %s: %s", content_file, content_type)
            return False
        return True

    def load_content_file(self, content_file: str) -> Dict:
        """Load and return JSON content from a file."""
        try:
            with open(content_file, 'r', encoding='utf-8') as f:
                content_data = json.load(f)
            if not isinstance(content_data, dict):
                logger.error(f"Invalid JSON format in {content_file}: expected dict, got {type(content_data)}")
                return {}
            return content_data
        except (json.JSONDecodeError, FileNotFoundError, UnicodeDecodeError) as e:
            logger.error(f"Failed to load content from {content_file}: {str(e)}")
            return {}

    def schedule_content(self, content_data: List[Dict], platform: str, content_type: str, lang: str, source_file: str) -> List[Dict]:
        """Schedule content with sequential times."""
        scheduled = []
        try:
            db_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'scheduler_db'))
            os.makedirs(db_dir, exist_ok=True)
            db_path = os.path.join(db_dir, 'scheduled_posts.db')
            conn = sqlite3.connect(db_path)
            c = conn.cursor()
            c.execute('''CREATE TABLE IF NOT EXISTS scheduled_posts
                         (content_id TEXT, platform TEXT, content_type TEXT, content TEXT,
                          scheduled_time TEXT, status TEXT, post_id TEXT PRIMARY KEY, lang TEXT)''')

            for item in content_data:
                try:
                    if not self.validate_content(item, source_file):
                        continue

                    content_id = item.get('content_id')
                    file_platform = item.get('platform')
                    content = item.get(content_type if content_type != 'voice_script' else 'voice_script', '')

                    if file_platform != platform:
                        logger.info(f"Skipping {content_id}: platform mismatch ({file_platform} != {platform})")
                        continue

                    post_id = str(uuid.uuid4())
                    self.schedule_counter += 1
                    scheduled_time = (datetime.now() + timedelta(minutes=5 * self.schedule_counter)).strftime('%Y-%m-%d %H:%M:%S')

                    c.execute(
                        "INSERT INTO scheduled_posts (content_id, platform, content_type, content, scheduled_time, status, post_id, lang) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                        (content_id, platform, content_type, content, scheduled_time, 'pending', post_id, lang)
                    )
                    scheduled.append({
                        'content_id': content_id,
                        'platform': platform,
                        'content_type': content_type,
                        'post_id': post_id,
                        'scheduled_time': scheduled_time
                    })
                    logger.info(f"Scheduled {content_id} for {platform} {content_type} at {scheduled_time} (lang: {lang})")

                except Exception as e:
                    logger.error(f"Failed to schedule content from {source_file}: {str(e)}")
                    continue

            conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Database error: {str(e)}")
            raise
        finally:
            conn.close()

        return scheduled

    def load_tts_content(self, tts_file: str, lang: str) -> List[Dict]:
        """Load content from tts_simulation_output.json."""
        try:
            with open(tts_file, 'r', encoding='utf-8') as f:
                content_data = json.load(f)
            if not isinstance(content_data, list):
                logger.error(f"Invalid format in {tts_file}: expected list, got {type(content_data)}")
                return []
            filtered_content = [item for item in content_data if item.get('language') == lang]
            logger.info(f"Loaded {len(filtered_content)} items for language {lang} from {tts_file}")
            return filtered_content
        except Exception as e:
            logger.error(f"Failed to load TTS content from {tts_file}: {str(e)}")
            return []

    def run_scheduler(self, content_dir: str, tts_file: str, selected_language: str) -> None:
        """Run Agent D Scheduler."""
        logger.info(f"Starting Agent D: Scheduler for language: {selected_language}")
        logger.info(f"Content directory: {content_dir}, TTS file: {tts_file}")

        # Clear the database
        db_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'scheduler_db'))
        os.makedirs(db_dir, exist_ok=True)
        db_path = os.path.join(db_dir, 'scheduled_posts.db')
        try:
            conn = sqlite3.connect(db_path)
            c = conn.cursor()
            c.execute("DROP TABLE IF EXISTS scheduled_posts")
            c.execute('''CREATE TABLE scheduled_posts
                         (content_id TEXT, platform TEXT, content_type TEXT, content TEXT,
                          scheduled_time TEXT, status TEXT, post_id TEXT PRIMARY KEY, lang TEXT)''')
            conn.commit()
            logger.info("Cleared and recreated scheduled_posts database.")
        except sqlite3.Error as e:
            logger.error(f"Failed to clear database: {str(e)}")
            raise
        finally:
            conn.close()

        platforms = {
            'tweet': ['twitter'],
            'post': ['instagram', 'linkedin'],
            'voice_script': ['sanatan']
        }

        # Process content directories
        dirs_to_process = [
            os.path.join(content_dir, lang) for lang in self.supported_languages
            if selected_language == 'all' or lang == selected_language
        ]

        for lang_dir in dirs_to_process:
            lang = os.path.basename(lang_dir)
            logger.info(f"Processing directory: {lang_dir} (lang: {lang})")
            if not os.path.exists(lang_dir):
                logger.warning(f"Directory does not exist: {lang_dir}")
                continue

            try:
                files_in_dir = os.listdir(lang_dir)
                logger.debug(f"Found {len(files_in_dir)} files in {lang_dir}: {files_in_dir}")
            except Exception as e:
                logger.error(f"Error accessing directory {lang_dir}: {str(e)}")
                continue

            for content_type, platform_list in platforms.items():
                if content_type == 'voice_script' and platform_list[0] == 'sanatan':
                    tts_content = self.load_tts_content(tts_file, lang)
                    if tts_content:
                        scheduled = self.schedule_content(tts_content, 'sanatan', 'voice_script', lang, tts_file)
                        logger.info(f"Scheduled {len(scheduled)} voice_script posts for sanatan (lang: {lang})")
                    else:
                        logger.info(f"No voice_script content found for sanatan in {tts_file} (lang: {lang})")
                else:
                    content_files = [
                        os.path.join(lang_dir, f) for f in files_in_dir
                        if f.startswith(f"{content_type}_") and f.endswith(".json")
                    ]
                    logger.debug(f"For content_type '{content_type}', found files: {content_files}")
                    if content_files:
                        content_data = []
                        for content_file in content_files:
                            content = self.load_content_file(content_file)
                            if content:
                                content_data.append(content)
                        for platform in platform_list:
                            if content_data:
                                scheduled = self.schedule_content(content_data, platform, content_type, lang, lang_dir)
                                logger.info(f"Scheduled {len(scheduled)} {content_type} posts for {platform} (lang: {lang})")
                            else:
                                logger.info(f"No valid {content_type} content found for {platform} in {lang_dir} (lang: {lang})")
                    else:
                        for platform in platform_list:
                            logger.info(f"No {content_type} files found for {platform} in {lang_dir} (lang: {lang})")

        logger.info("Completed scheduling.")

def main() -> None:
    """Main function to run the scheduler."""
    parser = argparse.ArgumentParser(description="Run Agent D: Scheduler")
    parser.add_argument('--language', choices=['all'] + ['en', 'hi', 'sa', 'mr', 'ta', 'te', 'kn', 'ml', 'bn', 'gu', 'pa', 'es', 'fr', 'de', 'zh', 'ja', 'ru', 'ar', 'pt', 'it'], default='all', help="Language to process")
    parser.add_argument('--content_dir', default='E:\\projects\\vaani-sentinel-x\\content\\content_final', help="Path to content_final directory")
    parser.add_argument('--tts_file', default='E:\\projects\\vaani-sentinel-x\\data\\tts_simulation_output.json', help="Path to tts_simulation_output.json")
    args = parser.parse_args()

    logger.info("Agent D Scheduler script started.")
    scheduler = Scheduler()
    scheduler.run_scheduler(args.content_dir, args.tts_file, args.language)
    logger.info("Agent D Scheduler script finished.")

if __name__ == "__main__":
    main()