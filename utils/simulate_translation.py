import os
import json
import logging
from typing import Dict, List

# Logging setup
LOG_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'logs'))
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, 'simulate_translation.txt')

logger = logging.getLogger('simulate_translation')
logger.setLevel(logging.INFO)
handler = logging.FileHandler(LOG_FILE, encoding='utf-8')
handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logger.addHandler(handler)
logger.info("Initializing simulate_translation.py")

# File paths
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
CONFIG_DIR = os.path.join(BASE_DIR, 'config')
METADATA_DIR = os.path.join(BASE_DIR, 'content', 'structured', 'metadata')
PREVIEW_DIR = os.path.join(BASE_DIR, 'content', 'translation_previews')
LANGUAGE_MAP_FILE = os.path.join(CONFIG_DIR, 'language_voice_map.json')

# Language display names for dummy translations
LANGUAGE_NAMES = {
    'en': 'English', 'hi': 'Hindi', 'mr': 'Marathi', 'ta': 'Tamil', 'te': 'Telugu',
    'kn': 'Kannada', 'ml': 'Malayalam', 'bn': 'Bengali', 'gu': 'Gujarati', 'pa': 'Punjabi',
    'as': 'Assamese', 'es': 'Spanish', 'fr': 'French', 'de': 'German', 'ja': 'Japanese',
    'zh': 'Chinese', 'ru': 'Russian', 'ar': 'Arabic', 'pt': 'Portuguese', 'it': 'Italian'
}

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

def generate_dummy_translation(text: str, lang_code: str) -> str:
    """Generate a dummy translation by prefixing the original text with language name."""
    lang_name = LANGUAGE_NAMES.get(lang_code, lang_code)
    dummy_text = f"[{lang_name}]: {text}"
    logger.debug(f"Generated dummy translation for {lang_code}: {dummy_text}")
    return dummy_text

def create_translation_preview(content: Dict, lang_code: str, voice_map: Dict) -> Dict:
    """Create a translation preview for a specific language."""
    original_text = content.get('original_text', '')
    platform = content.get('platform', 'unknown')
    content_id = content.get('content_id', 'unknown')
    
    # Generate dummy translation
    translated_text = generate_dummy_translation(original_text, lang_code)
    
    # Get voice tag
    voice_tag = voice_map['languages'].get(lang_code, voice_map['fallback_voice'])
    
    # Preview structure
    preview = {
        'content_id': content_id,
        'platform': platform,
        'language': lang_code,
        'translated_text': translated_text,
        'voice_tag': voice_tag,
        'sentiment': content.get('sentiment', 'uplifting'),
        'tone': content.get('tone', 'formal')
    }
    logger.info(f"Created preview for {lang_code}: {content_id} on {platform}")
    return preview

def save_preview(preview: Dict, output_dir: str = PREVIEW_DIR) -> None:
    """Save translation preview to JSON file."""
    logger.debug(f"Saving preview to {output_dir}")
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, f"preview_{preview['content_id']}_{preview['language']}.json")
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(preview, f, ensure_ascii=False, indent=2)
        logger.info(f"Saved preview to {output_file}")
    except Exception as e:
        logger.error(f"Failed to save preview to {output_file}: {str(e)}")
        raise

def simulate_translations(content_id: str, platform: str) -> List[Dict]:
    """Simulate translations for all 20 languages for a given content ID and platform."""
    logger.info(f"Simulating translations for content_id: {content_id}, platform: {platform}")
    
    # Load voice map
    voice_map = load_config(LANGUAGE_MAP_FILE)
    supported_languages = list(voice_map['languages'].keys())
    
    # Load metadata from language_mapper output
    metadata_file = os.path.join(METADATA_DIR, f"metadata_{content_id}_{platform}.json")
    if not os.path.exists(metadata_file):
        logger.error(f"Metadata file not found: {metadata_file}")
        raise FileNotFoundError(f"Metadata file not found: {metadata_file}")
    
    content = load_config(metadata_file)
    
    # Generate previews for all supported languages
    previews = []
    for lang_code in supported_languages:
        preview = create_translation_preview(content, lang_code, voice_map)
        save_preview(preview)
        previews.append(preview)
    
    logger.info(f"Generated {len(previews)} translation previews for content_id: {content_id}")
    return previews

def main():
    """Main function for testing simulate_translation."""
    logger.info("Starting main function")
    print("Starting simulate_translation.py")
    try:
        # Test with sample content and platform
        previews = simulate_translations(
            content_id="1",
            platform="instagram"
        )
        print(f"Generated {len(previews)} Translation Previews:")
        for preview in previews[:5]:  # Show first 5 for brevity
            print(json.dumps(preview, ensure_ascii=False, indent=2))
    except Exception as e:
        logger.error(f"Error in main: {str(e)}")
        print(f"Error: {str(e)}")
    logger.info("Completed main function")

if __name__ == "__main__":
    main()
