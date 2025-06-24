import argparse
import json
import os
import logging
from datetime import datetime, timezone
import time
import glob
from tenacity import retry, stop_after_attempt, wait_fixed
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
USER_ID = 'agent_p_personalizer'
logs_dir = r'E:\projects\vaani-sentinel-x\logs'
os.makedirs(logs_dir, exist_ok=True)
log_file = os.path.join(logs_dir, 'personalization_agent.txt')

class UserContextFilter(logging.Filter):
    def filter(self, record):
        record.user = USER_ID
        return True

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - User: %(user)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)
logger.addFilter(UserContextFilter())
logger.info("Initializing personalization_agent.py")

# Constants
CONFIG_DIR = os.path.join(os.path.dirname(__file__), '..', 'config')
USER_PROFILE_FILE = os.path.join(CONFIG_DIR, 'user_profile.json')
VOICE_CONFIG_FILE = os.path.join(CONFIG_DIR, 'language_voice_map.json')
OUTPUT_BASE_DIR = os.path.join(os.path.dirname(__file__), '..', 'content', 'content_ready')

# Cache for configurations
_voice_config_cache = None
_user_profile_cache = None

def load_json(file_path: str):
    """Load JSON file."""
    logger.debug(f"Loading JSON: {file_path}")
    if not os.path.exists(file_path):
        logger.error(f"File not found: {file_path}")
        raise FileNotFoundError(f"File not found: {file_path}")
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            logger.debug(f"Loaded JSON content: {data}")
            return data
    except Exception as e:
        logger.error(f"Failed to load {file_path}: {str(e)}")
        raise

def load_voice_config(config_path: str):
    """Load and cache voice configuration from JSON file."""
    global _voice_config_cache
    if _voice_config_cache is None:
        try:
            _voice_config_cache = load_json(config_path)
            logger.info(f"Loaded voice configuration from {config_path}")
        except FileNotFoundError:
            logger.error(f"Voice config {config_path} not found. Using default mappings.")
            _voice_config_cache = {
                "default_voices_by_language": {},
                "tone_voice_mapping": {},
                "fallback_voice_for_language": "english_female_1"
            }
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON in {config_path}. Using default mappings.")
            _voice_config_cache = {
                "default_voices_by_language": {},
                "tone_voice_mapping": {},
                "fallback_voice_for_language": "english_female_1"
            }
    return _voice_config_cache

def load_user_profiles(profile_path: str):
    """Load and cache user profiles from JSON file."""
    global _user_profile_cache
    if _user_profile_cache is None:
        try:
            _user_profile_cache = load_json(profile_path)
            logger.info(f"Loaded user profiles from {profile_path}")
        except FileNotFoundError:
            logger.error(f"User profile {profile_path} not found. Using default profile.")
            _user_profile_cache = {
                "profiles": [{
                    "user_id": "default",
                    "preferred_languages": ["en", "hi", "sa", "mr", "ta", "te", "kn", "ml", "bn", "gu", "pa", "es", "fr", "de", "zh", "ja", "ru", "ar", "pt", "it"],
                    "preferred_tone": {
                        "twitter": "neutral",
                        "instagram": "casual",
                        "linkedin": "formal",
                        "sanatan": "devotional"
                    }
                }]
            }
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON in {profile_path}. Using default profile.")
            _user_profile_cache = {
                "profiles": [{
                    "user_id": "default",
                    "preferred_languages": ["en", "hi", "sa", "mr", "ta", "te", "kn", "ml", "bn", "gu", "pa", "es", "fr", "de", "zh", "ja", "ru", "ar", "pt", "it"],
                    "preferred_tone": {
                        "twitter": "neutral",
                        "instagram": "casual",
                        "linkedin": "formal",
                        "sanatan": "devotional"
                    }
                }]
            }
    return _user_profile_cache

def get_voice_tag(language: str, tone: str, platform: str, config_path: str, input_voice_tag: str):
    """Retrieve voice tag for a language, tone, and platform, respecting input voice_tag."""
    config = load_voice_config(config_path)
    tone_mapping = config.get('tone_voice_mapping', {}).get(language, {})
    voice = tone_mapping.get(tone, config['default_voices_by_language'].get(language, input_voice_tag))
    logger.debug(f"Assigned voice_tag {voice} for language {language}, tone {tone}, platform {platform} (input voice_tag: {input_voice_tag})")
    return voice

def clear_existing_content(content_id: str, platform: str, user_id: str):
    """Clear existing personalized content files for the given content_id, platform, and user_id."""
    try:
        pattern = os.path.join(OUTPUT_BASE_DIR, '*', f'personalized_{content_id}_{platform}_{user_id}.json')
        files_to_delete = glob.glob(pattern, recursive=True)
        for file_path in files_to_delete:
            try:
                os.remove(file_path)
                logger.info(f"Deleted existing file: {file_path}")
            except Exception as e:
                logger.error(f"Failed to delete {file_path}: {str(e)}")
        if not files_to_delete:
            logger.debug(f"No existing files found for content_id {content_id}, platform {platform}, user_id {user_id}")
    except Exception as e:
        logger.error(f"Error while clearing existing content: {str(e)}")

# Configure Gemini API
api_key = os.getenv('GOOGLE_GEMINI_API_KEY')
if not api_key:
    logger.error("GOOGLE_GEMINI_API_KEY environment variable not set.")
    model = None
else:
    logger.info("GOOGLE_GEMINI_API_KEY loaded successfully.")
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
    except Exception as e:
        logger.error(f"Failed to configure Gemini API: {str(e)}")
        model = None

@retry(stop=stop_after_attempt(3), wait=wait_fixed(60))
def call_gemini_api(text: str, language: str, tone: str):
    """Call Google Gemini API to personalize text, returning a single text string."""
    if model is None:
        logger.error("Gemini API not configured. Returning original text.")
        return text
    try:
        logger.debug(f"Making API call for text: {text}, language: {language}, tone: {tone}")
        prompt = (
            f"Personalize the following text in {language} with a {tone} tone. "
            f"Return a single text string that is concise, natural, and suitable for text-to-speech. "
            f"Do not provide multiple options or explanations. Text: {text}"
        )
        response = model.generate_content(prompt)
        personalized_text = response.text.strip()
        time.sleep(4)  # Respect free tier rate limit
        return personalized_text
    except Exception as e:
        logger.error(f"Failed to personalize text for {language}, tone {tone}: {str(e)}")
        return text

def get_output_path(content_id: str, platform: str, pipeline: str, language: str, user_id: str):
    """Generate output file path based on pipeline, language, and user."""
    return os.path.join(
        OUTPUT_BASE_DIR,
        pipeline,
        language,
        f"personalized_{content_id}_{platform}_{user_id}.json"
    )

def personalize_content(content_id: str, translations_file: str, config_path: str, profile_path: str, user_id: str, languages: list = None):
    """Personalize content for specified content ID and user, saving to pipeline/language directories."""
    # Clear existing content for this content_id, platform, and user_id
    platform = os.path.basename(translations_file).split('_')[-1].replace('.json', '')
    clear_existing_content(content_id, platform, user_id)

    try:
        translations = load_json(translations_file)
    except Exception as e:
        logger.error(f"Failed to load translations: {str(e)}")
        return

    content_translations = [t for t in translations if t['content_id'] == content_id]
    if not content_translations:
        logger.warning(f"No translations found for content ID {content_id}")
        return

    user_profiles = load_user_profiles(profile_path)
    user_profile = next((p for p in user_profiles['profiles'] if p['user_id'] == user_id), None)
    if not user_profile:
        logger.error(f"No profile found for user {user_id}. Aborting.")
        return

    preferred_languages = user_profile['preferred_languages']
    preferred_tone = user_profile['preferred_tone'].get(platform, 'neutral')

    for translation in content_translations:
        language = translation['language']
        if languages and language not in languages:
            logger.debug(f"Skipping language {language} (not in specified languages)")
            continue
        if language not in preferred_languages:
            logger.debug(f"Skipping language {language} (not in user {user_id}'s preferred languages)")
            continue

        translated_text = translation['translated_text']
        input_voice_tag = translation['voice_tag']
        source_language = translation['source_language']
        pipeline = translation['pipeline']
        sentiment = translation['sentiment']

        output_file = get_output_path(content_id, platform, pipeline, language, user_id)
        try:
            personalized_text = call_gemini_api(translated_text, language, preferred_tone)
            voice_tag = get_voice_tag(language, preferred_tone, platform, config_path, input_voice_tag)
            entry = {
                'content_id': content_id,
                'platform': platform,
                'language': language,
                'user_id': user_id,
                'translated_text': translated_text,
                'personalized_text': personalized_text,
                'tone': preferred_tone,
                'voice_tag': voice_tag,
                'confidence_score': translation['confidence_score'],
                'source_language': source_language,
                'sentiment': sentiment,
                'preferred_tone': preferred_tone,
                'pipeline': pipeline,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            os.makedirs(os.path.dirname(output_file), exist_ok=True)
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(entry, f, ensure_ascii=False, indent=2)
            logger.info(f"Saved personalized content to {output_file}")
        except Exception as e:
            logger.error(f"Failed to personalize for user {user_id}, lang {language}, tone {preferred_tone}: {str(e)}")
            entry = {
                'content_id': content_id,
                'platform': platform,
                'language': language,
                'user_id': user_id,
                'translated_text': translated_text,
                'personalized_text': translated_text,
                'tone': preferred_tone,
                'voice_tag': get_voice_tag(language, preferred_tone, platform, config_path, input_voice_tag),
                'confidence_score': translation['confidence_score'],
                'source_language': source_language,
                'sentiment': sentiment,
                'preferred_tone': preferred_tone,
                'pipeline': pipeline,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            os.makedirs(os.path.dirname(output_file), exist_ok=True)
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(entry, f, ensure_ascii=False, indent=2)
            logger.info(f"Saved personalized (fallback) content to {output_file}")

def main():
    """Parse arguments and run personalization agent."""
    parser = argparse.ArgumentParser(description='Vaani Sentinel X: Personalization Agent')
    parser.add_argument('--content_id', required=True, help='Content ID to personalize')
    parser.add_argument('--translations_file', required=True, help='Path to translations JSON file')
    parser.add_argument('--user_id', required=True, help='User ID for personalization')
    parser.add_argument('--languages', help='Comma-separated list of languages to process (e.g., en,hi,ta)')
    args = parser.parse_args()

    languages = args.languages.split(',') if args.languages else None
    personalize_content(
        content_id=args.content_id,
        translations_file=args.translations_file,
        config_path=VOICE_CONFIG_FILE,
        profile_path=USER_PROFILE_FILE,
        user_id=args.user_id,
        languages=languages
    )

if __name__ == '__main__':
    main()