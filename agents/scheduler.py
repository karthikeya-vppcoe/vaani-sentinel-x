import json
import sqlite3
import os
import logging
import re
import argparse
from datetime import datetime, timedelta
from typing import List, Dict
import uuid

# === Logging Setup for Agent D (Scheduler) ===
USER_ID = 'agent_d_user'
logger = logging.getLogger('scheduler')
logger.setLevel(logging.INFO)

log_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'logs'))
os.makedirs(log_dir, exist_ok=True)
log_path = os.path.join(log_dir, 'scheduler.txt')
file_handler = logging.FileHandler(log_path, encoding='utf-8')
file_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - User: %(user)s - %(message)s')
file_handler.setFormatter(formatter)
file_handler.addFilter(lambda record: setattr(record, 'user', USER_ID) or True)
logger.handlers = [file_handler]

# === Function to Schedule Content ===
def schedule_content(content_files: List[str], platform: str, content_type: str, lang: str) -> List[Dict]:
    """Schedule content for a specific platform, content type, and language (Agent D: Task 2)."""
    scheduled = []
    try:
        db_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'scheduler_db'))
        os.makedirs(db_dir, exist_ok=True)
        db_path = os.path.join(db_dir, 'scheduled_posts.db')
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        # Ensure table exists with correct schema
        c.execute('''CREATE TABLE IF NOT EXISTS scheduled_posts
                     (content_id TEXT, platform TEXT, content_type TEXT, content TEXT,
                      scheduled_time TEXT, status TEXT, post_id TEXT PRIMARY KEY, lang TEXT)''')

        for content_file in content_files:
            try:
                with open(content_file, 'r', encoding='utf-8') as f:
                    content_data = json.load(f)

                content_id = content_data.get('id')
                file_platform = content_data.get('platform')
                content = content_data.get(content_type if content_type != 'voice' else 'voice_script', '')

                if not content_id or not file_platform:
                    logger.warning(f"Missing ID or platform in {content_file}, skipping")
                    continue

                # Skip if not intended platform
                if file_platform != platform:
                    logger.info(f"Skipping {content_file}: platform mismatch ({file_platform} != {platform})")
                    continue

                # Since we clear the database at the start, no need to check for duplicates
                post_id = str(uuid.uuid4())
                scheduled_time = (datetime.now() - timedelta(hours=1)).strftime('%Y-%m-%d %H:%M:%S')  # Backdated for testing

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

            except (json.JSONDecodeError, FileNotFoundError, UnicodeDecodeError) as e:
                logger.error(f"Failed to process {content_file}: {str(e)}")
                continue

        conn.commit()
    except sqlite3.Error as e:
        logger.error(f"Database error: {str(e)}")
        raise
    finally:
        conn.close()

    return scheduled

# === Function to Run Scheduler Across Specified Languages & Platforms ===
def run_scheduler(content_dirs: List[str], selected_language: str) -> None:
    """Run Agent D Scheduler for the specified language, clearing the database first."""
    logger.info(f"Starting Agent D: Scheduler for language: {selected_language}")
    logger.info(f"Python working directory: {os.getcwd()}")
    logger.info(f"Content directories to check: {content_dirs}")

    # Clear the database before scheduling
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
        logger.info("Cleared and recreated scheduled_posts database with lang column.")
    except sqlite3.Error as e:
        logger.error(f"Failed to clear database: {str(e)}")
        raise
    finally:
        conn.close()

    platforms = {
        'tweet': ['twitter'],
        'post': ['instagram', 'linkedin'],
        'voice': ['sanatan']
    }

    # Filter directories based on the selected language
    dirs_to_process = [d for d in content_dirs if selected_language == 'all' or os.path.basename(d) == selected_language]

    for content_dir in dirs_to_process:
        logger.info(f"Checking content directory: {content_dir}")
        if not os.path.exists(content_dir):
            logger.error(f"Content directory does not exist: {content_dir}")
            continue
        try:
            files_in_dir = os.listdir(content_dir)
            logger.info(f"Found {len(files_in_dir)} files in {content_dir}: {files_in_dir}")
        except Exception as e:
            logger.error(f"Error accessing directory {content_dir}: {str(e)}")
            continue
        # Extract language from directory path (e.g., 'en', 'hi', 'sa')
        lang = os.path.basename(content_dir)
        try:
            for content_type, platform_list in platforms.items():
                content_files = [
                    os.path.join(content_dir, f) for f in files_in_dir
                    if f.startswith(f"{content_type}_") and f.endswith(".json")
                ]
                logger.info(f"For content_type '{content_type}', found files: {content_files}")
                for platform in platform_list:
                    logger.info(f"Processing platform: {platform} for content_type: {content_type} (lang: {lang})")
                    if content_files:
                        scheduled = schedule_content(content_files, platform, content_type, lang)
                        logger.info(f"Scheduled {len(scheduled)} {content_type} posts for {platform} (lang: {lang})")
                    else:
                        logger.info(f"No {content_type} files found for {platform} in {content_dir} (lang: {lang})")
        except Exception as e:
            logger.error(f"Failed to process directory {content_dir}: {str(e)}")
            continue

    logger.info("Completed scheduling.")

# === Entry Point ===
def main() -> None:
    """Main function to run the scheduler with a language argument."""
    parser = argparse.ArgumentParser(description="Run Agent D: Scheduler")
    parser.add_argument('language', choices=['en', 'hi', 'sa', 'all'], help="Language to process (en, hi, sa, all)")
    args = parser.parse_args()

    logger.info("Agent D Scheduler script started.")
    content_dirs = [
        os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'content', 'content_ready', lang))
        for lang in ['en', 'hi', 'sa']
    ]
    for d in content_dirs:
        logger.info(f"Should check directory: {d} (exists: {os.path.exists(d)})")
    run_scheduler(content_dirs, args.language)
    logger.info("Agent D Scheduler script finished.")

if __name__ == "__main__":
    main()