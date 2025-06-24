import os
import json
import logging
import argparse
from typing import Dict, List, Optional

# Logging setup
USER_ID = 'language_mapper_user'
LOG_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'logs'))
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, 'language_mapper.txt')

logger = logging.getLogger('language_mapper')
logger.setLevel(logging.INFO)
handler = logging.FileHandler(LOG_FILE, encoding='utf-8')
handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - User: %(user)s - %(message)s'))
handler.addFilter(lambda record: setattr(record, 'user', USER_ID) or True)
logger.handlers = [handler]
logger.info("Initializing language_mapper.py")

# File paths
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
CONFIG_DIR = os.path.join(BASE_DIR, 'config')
CONTENT_DIR = os.path.join(BASE_DIR, 'content', 'multilingual_ready')
STRUCTURED_DIR = os.path.join(BASE_DIR, 'content', 'structured')
LANGUAGE_MAP_FILE = os.path.join(CONFIG_DIR, 'language_voice_map.json')
USER_PROFILES_FILE = os.path.join(CONFIG_DIR, 'user_profile.json')
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
    for profile in profiles.get('profiles', []):
        if profile['user_id'] == user_id:
            logger.info(f"Found user profile for {user_id}")
            return profile
    logger.warning(f"No profile found for user_id: {user_id}")
    return None

def select_content_language(user_prefs: Dict, content_lang: str, available_langs: List[str]) -> str:
    """Select the best language from user preferences and available content languages."""
    logger.debug(f"User preferences: {user_prefs['preferred_languages']}, Content language: {content_lang}, Available languages: {available_langs}")
    if content_lang in user_prefs['preferred_languages'] and content_lang in available_langs:
        logger.info(f"Selected content language: {content_lang}")
        return content_lang
    for lang in user_prefs['preferred_languages']:
        if lang in available_langs:
            logger.info(f"Selected fallback language: {lang}")
            return lang
    default_lang = user_prefs['preferred_languages'][0] if user_prefs['preferred_languages'] else 'en'
    logger.info(f"No matching language found, using default: {default_lang}")
    return default_lang

def get_voice_tag(language: str, tone: str, voice_map: Dict) -> str:
    """Map language and tone to TTS voice tag, with fallback."""
    logger.debug(f"Mapping voice for language: {language}, tone: {tone}")
    tone_mapping = voice_map['tone_voice_mapping'].get(language, {})
    voice_tag = tone_mapping.get(tone, voice_map['default_voices_by_language'].get(language, voice_map['fallback_voice_for_language']))
    if voice_tag == voice_map['fallback_voice_for_language'] and tone != voice_map['fallback_voice_for_tone']:
        # Fallback to neutral tone for the language if tone-specific voice is unavailable
        voice_tag = tone_mapping.get(voice_map['fallback_voice_for_tone'], voice_map['default_voices_by_language'].get(language, voice_map['fallback_voice_for_language']))
    logger.info(f"Assigned voice tag: {voice_tag} for language: {language}, tone: {tone}")
    return voice_tag

def find_content_file(content_id: str, platform: str, content_dir: str = CONTENT_DIR) -> Optional[str]:
    """Search for content file in multilingual_ready/<pipeline>/<content_id>_<platform>.json."""
    logger.debug(f"Searching for content_id: {content_id}, platform: {platform} in {content_dir}")
    for pipeline in os.listdir(content_dir):
        pipeline_path = os.path.join(content_dir, pipeline)
        if os.path.isdir(pipeline_path):
            content_file = os.path.join(pipeline_path, f"{content_id}_{platform}.json")
            if os.path.exists(content_file):
                logger.info(f"Found content file: {content_file}")
                return content_file
    logger.error(f"Content file for ID {content_id}, platform {platform} not found in {content_dir}")
    return None

def enhance_metadata(content: Dict, user_id: str, platform: str, voice_map: Dict, user_prefs: Dict) -> Dict:
    """Enhance content metadata with language and voice tags."""
    logger.info(f"Enhancing metadata for content_id: {content['content_id']}, user_id: {user_id}, platform: {platform}")
    content_language = content.get('content_language', content.get('source_language', 'en'))
    preferred_tone = content.get('preferred_tone', 'neutral')
    
    # Available content languages (from pipeline directories)
    content_langs = [content.get('content_language')]  # Use provided content language
    logger.debug(f"Available content languages: {content_langs}")
    
    # Select content language
    selected_language = select_content_language(user_prefs, content_language, content_langs)
    
    # Get voice tag based on language and tone
    voice_tag = get_voice_tag(selected_language, preferred_tone, voice_map)
    
    # Enhanced metadata
    enhanced_metadata = {
        'content_id': content['content_id'],
        'platform': platform,
        'content_language': selected_language,
        'preferred_languages': user_prefs['preferred_languages'],
        'voice_tag': voice_tag,
        'original_text': content.get('post', ''),
        'sentiment': content.get('sentiment', 'uplifting'),
        'preferred_tone': preferred_tone,
        'bias_status': content.get('bias_status', 'neutral'),
        'type': content.get('type', 'fact'),
        'pipeline': content.get('pipeline', 'latin_pipeline'),
        'processed_at': content.get('processed_at', '')
    }
    logger.info(f"Generated metadata: {enhanced_metadata}")
    return enhanced_metadata

def save_metadata(metadata: Dict, output_dir: str = METADATA_OUTPUT_DIR) -> None:
    """Save enhanced metadata to JSON file."""
    logger.debug(f"Saving metadata to {output_dir}")
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, f"metadata_{metadata['content_id']}_{metadata['platform']}_mapped.json")
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
    content_file = find_content_file(content_id, platform)
    if not content_file:
        logger.error(f"Content ID {content_id} for platform {platform} not found")
        raise FileNotFoundError(f"Content ID {content_id} for platform {platform} not found")

    # Load content
    content = load_config(content_file)

    # Load configurations
    voice_map = load_config(LANGUAGE_MAP_FILE)
    user_profiles = load_config(USER_PROFILES_FILE)

    # Get user preferences
    user_prefs = get_user_preferences(user_id, user_profiles)
    if not user_prefs:
        logger.error(f"User {user_id} not found")
        raise ValueError(f"User {user_id} not found")

    # Enhance metadata
    metadata = enhance_metadata(content, user_id, platform, voice_map, user_prefs)

    # Save metadata
    save_metadata(metadata)

    return metadata

def main():
    """Main function for running language mapper."""
    parser = argparse.ArgumentParser(description="Vaani Sentinel X: Language Mapper")
    parser.add_argument('--content_id', required=True, help="Content ID to process")
    parser.add_argument('--user_id', default='default', help="User ID for preferences")
    parser.add_argument('--platform', default='instagram', choices=PLATFORMS, help="Platform")
    args = parser.parse_args()
    
    logger.info("Starting language_mapper.py")
    try:
        metadata = process_content(args.content_id, args.user_id, args.platform)
        print("Enhanced Metadata:")
        print(json.dumps(metadata, ensure_ascii=False, indent=2))
    except Exception as e:
        logger.error(f"Error in main: {str(e)}")
        print(f"Error: {str(e)}")
    logger.info("Completed language_mapper.py")

if __name__ == "__main__":
    main()