import os
import json
import logging
from typing import Dict, List, Optional

# Logging setup
LOG_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'logs'))
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, 'language_mapper.txt')

logger = logging.getLogger('language_mapper')
logger.setLevel(logging.INFO)
handler = logging.FileHandler(LOG_FILE, encoding='utf-8')
handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logger.addHandler(handler)

# Log initialization
logger.info("Initializing language_mapper.py")

# File paths
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
CONFIG_DIR = os.path.join(BASE_DIR, 'config')
CONTENT_DIR = os.path.join(BASE_DIR, 'content', 'multilingual_ready')
STRUCTURED_DIR = os.path.join(BASE_DIR, 'content', 'structured')
LANGUAGE_MAP_FILE = os.path.join(CONFIG_DIR, 'language_voice_map.json')
USER_PROFILES_FILE = os.path.join(CONFIG_DIR, 'user_profiles.json')
METADATA_OUTPUT_DIR = os.path.join(STRUCTURED_DIR, 'metadata')

# Supported platforms
PLATFORMS = ['instagram', 'linkedin', 'twitter', 'sanatan']

def load_config(file_path: str) -> Dict:
    """Load JSON configuration file."""
    logger.debug(f"Attempting to load config: {file_path}")
    if not os.path.exists(file_path):
        logger.error(f"Config file not found: {file_path}")
        raise FileNotFoundError(f"Config file not found: {file_path}")
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        logger.info(f"Successfully loaded config: {file_path}")
        return data
    except Exception as e:
        logger.error(f"Failed to load {file_path}: {str(e)}")
        raise

def get_user_preferences(user_id: str, profiles: List[Dict]) -> Optional[Dict]:
    """Retrieve user language preferences by user_id."""
    logger.debug(f"Searching for user_id: {user_id}")
    for profile in profiles:
        if profile['user_id'] == user_id:
            logger.info(f"Found user profile for {user_id}")
            return profile
    logger.warning(f"No profile found for user_id: {user_id}")
    return None

def select_content_language(user_prefs: Dict, content_langs: List[str]) -> str:
    """Select the best language from user preferences and available content languages."""
    logger.debug(f"User preferences: {user_prefs['preferred_languages']}, Available languages: {content_langs}")
    for lang in user_prefs['preferred_languages']:
        if lang in content_langs:
            logger.info(f"Selected language: {lang}")
            return lang
    default_lang = user_prefs['default_language']
    logger.info(f"No matching language found, using default: {default_lang}")
    return default_lang

def get_voice_tag(language: str, voice_map: Dict) -> str:
    """Map language to TTS voice tag, with fallback."""
    logger.debug(f"Mapping voice for language: {language}")
    voices = voice_map['languages']
    voice_tag = voices.get(language, voice_map['fallback_voice'])
    logger.info(f"Assigned voice tag: {voice_tag} for language: {language}")
    return voice_tag

def find_content_file(content_id: str, content_dir: str = CONTENT_DIR) -> Optional[str]:
    """Search for content file in multilingual_ready/{lang}/block_{content_id}.json."""
    logger.debug(f"Searching for content_id: {content_id} in {content_dir}")
    for lang_dir in os.listdir(content_dir):
        lang_path = os.path.join(content_dir, lang_dir)
        if os.path.isdir(lang_path):
            content_file = os.path.join(lang_path, f"block_{content_id}.json")
            if os.path.exists(content_file):
                logger.info(f"Found content file: {content_file}")
                return content_file
    logger.error(f"Content file for ID {content_id} not found in {content_dir}")
    return None

def enhance_metadata(content: Dict, user_id: str, platform: str) -> Dict:
    """Enhance content metadata with language and voice tags."""
    logger.info(f"Enhancing metadata for content_id: {content['id']}, user_id: {user_id}, platform: {platform}")
    # Load configurations
    voice_map = load_config(LANGUAGE_MAP_FILE)
    user_profiles = load_config(USER_PROFILES_FILE)

    # Get user preferences
    user_prefs = get_user_preferences(user_id, user_profiles)
    if not user_prefs:
        logger.error(f"User {user_id} not found")
        raise ValueError(f"User {user_id} not found")

    # Available content languages (from directory structure)
    content_langs = [d for d in os.listdir(CONTENT_DIR) if os.path.isdir(os.path.join(CONTENT_DIR, d))]
    logger.debug(f"Available content languages: {content_langs}")

    # Select content language
    content_language = select_content_language(user_prefs, content_langs)

    # Get voice tag
    voice_tag = get_voice_tag(content_language, voice_map)

    # Enhanced metadata
    enhanced_metadata = {
        'content_id': content['id'],
        'platform': platform,
        'content_language': content_language,
        'preferred_languages': user_prefs['preferred_languages'],
        'voice_tag': voice_tag,
        'original_text': content.get('text', content.get('post', '')),
        'sentiment': content.get('sentiment', 'uplifting'),
        'tone': content.get('tone', 'formal'),
        'version': content.get('version', 1)
    }
    logger.info(f"Generated metadata: {enhanced_metadata}")
    return enhanced_metadata

def save_metadata(metadata: Dict, output_dir: str = METADATA_OUTPUT_DIR) -> None:
    """Save enhanced metadata to JSON file."""
    logger.debug(f"Saving metadata to {output_dir}")
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, f"metadata_{metadata['content_id']}_{metadata['platform']}.json")
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
        logger.info(f"Saved metadata to {output_file}")
    except Exception as e:
        logger.error(f"Failed to save metadata to {output_file}: {str(e)}")
        raise

def process_content(content_id: str, user_id: str, platform: str) -> Dict:
    """Process content to enhance metadata for a user and platform."""
    logger.info(f"Processing content_id: {content_id}, user_id: {user_id}, platform: {platform}")
    # Find content file
    content_file = find_content_file(content_id)
    if not content_file:
        logger.error(f"Content ID {content_id} not found")
        raise FileNotFoundError(f"Content ID {content_id} not found")

    # Load content
    content = load_config(content_file)

    # Enhance metadata
    metadata = enhance_metadata(content, user_id, platform)

    # Save metadata
    save_metadata(metadata)

    return metadata

def main():
    """Main function for testing language_mapper."""
    logger.info("Starting main function")
    print("Starting language_mapper.py")
    try:
        # Test with sample content and user
        metadata = process_content(
            content_id="1",
            user_id="user_001",
            platform="instagram"
        )
        print("Enhanced Metadata:")
        print(json.dumps(metadata, ensure_ascii=False, indent=2))
    except Exception as e:
        logger.error(f"Error in main: {str(e)}")
        print(f"Error: {str(e)}")
    logger.info("Completed main function")

if __name__ == "__main__":
    main()
