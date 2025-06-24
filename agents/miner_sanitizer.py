import os
import json
import logging
import argparse
import shutil
from datetime import datetime, timezone
from typing import List, Dict
from langdetect import detect, LangDetectException
import hashlib
import uuid
from better_profanity import profanity

# Logging setup
USER_ID = 'agent_a_user'
logger = logging.getLogger('miner_sanitizer')
logger.setLevel(logging.INFO)
log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'logs')
os.makedirs(log_dir, exist_ok=True)
log_path = os.path.join(log_dir, 'miner_sanitizer.txt')
file_handler = logging.FileHandler(log_path, encoding='utf-8')
file_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - User: %(user)s - %(message)s')
file_handler.setFormatter(formatter)
file_handler.addFilter(lambda record: setattr(record, 'user', USER_ID) or True)
logger.handlers = [file_handler]

# Supported languages and pipelines
SUPPORTED_LANGUAGES = {
    'en', 'hi', 'sa', 'mr', 'ta', 'te', 'kn', 'ml', 'bn', 'gu', 'pa',
    'es', 'fr', 'de', 'zh', 'ja', 'ru', 'ar', 'pt', 'it'
}
PIPELINES = {
    'hi': 'devanagari_pipeline',
    'sa': 'devanagari_pipeline',
    'mr': 'devanagari_pipeline',
    'bn': 'devanagari_pipeline',
    'gu': 'devanagari_pipeline',
    'pa': 'devanagari_pipeline',
    'ta': 'dravidian_pipeline',
    'te': 'dravidian_pipeline',
    'kn': 'dravidian_pipeline',
    'ml': 'dravidian_pipeline',
    'zh': 'cjk_pipeline',
    'ja': 'cjk_pipeline',
    'ar': 'arabic_pipeline',
    'en': 'latin_pipeline',
    'es': 'latin_pipeline',
    'fr': 'latin_pipeline',
    'de': 'latin_pipeline',
    'ru': 'latin_pipeline',
    'pt': 'latin_pipeline',
    'it': 'latin_pipeline'
}
PLATFORMS = ['twitter', 'instagram', 'linkedin', 'sanatan']
ALLOWED_SENTIMENTS = ['uplifting', 'neutral', 'devotional']
CONTROVERSIAL_KEYWORDS = ['politics', 'religion', 'war', 'controversy']
VALID_PIPELINES = {
    'latin_pipeline': {'range': (0x0000, 0x007F), 'description': 'ASCII characters'},
    'devanagari_pipeline': {'range': (0x0900, 0x097F), 'description': 'Devanagari script'},
    'cjk_pipeline': {'range': (0x4E00, 0x9FFF), 'description': 'CJK characters'},
    'dravidian_pipeline': {'range': (0x0B80, 0x0BFF), 'description': 'Dravidian scripts (Tamil, etc.)'},
    'arabic_pipeline': {'range': (0x0600, 0x06FF), 'description': 'Arabic script'}
}

def validate_pipelines() -> None:
    """Validate that all pipelines in PIPELINES are defined in VALID_PIPELINES."""
    for lang, pipeline in PIPELINES.items():
        if pipeline not in VALID_PIPELINES:
            logger.error(f"Invalid pipeline '{pipeline}' for language '{lang}'")
            raise ValueError(f"Pipeline '{pipeline}' not defined in VALID_PIPELINES")
    logger.info("All pipelines validated successfully")

def load_input_data(input_file: str) -> List[Dict]:
    """Load records from CSV or JSON."""
    try:
        if input_file.endswith('.csv'):
            import csv
            with open(input_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                records = [row for row in reader]
        elif input_file.endswith('.json'):
            with open(input_file, 'r', encoding='utf-8') as f:
                records = json.load(f)
                if not isinstance(records, list):
                    records = [records]
        else:
            raise ValueError("Unsupported file format. Use CSV or JSON.")
        logger.info(f"Loaded {len(records)} records from {input_file}")
        return records
    except Exception as e:
        logger.error(f"Failed to load {input_file}: {str(e)}")
        return []

def load_facts(facts_file: str) -> List[str]:
    """Load facts for sanitization."""
    try:
        with open(facts_file, 'r', encoding='utf-8') as f:
            facts = [line.strip() for line in f if line.strip()]
        logger.info(f"Loaded {len(facts)} facts")
        return facts
    except Exception as e:
        logger.error(f"Failed to load facts: {str(e)}")
        return []

def load_user_profiles(profile_file: str) -> List[Dict]:
    """Load user profiles, handling list or dict formats."""
    try:
        if not os.path.exists(profile_file):
            default_profile = {
                "profiles": [
                    {"user_id": "default", "preferred_languages": list(SUPPORTED_LANGUAGES), "preferred_tone": "neutral"}
                ]
            }
            os.makedirs(os.path.dirname(profile_file), exist_ok=True)
            with open(profile_file, 'w', encoding='utf-8') as f:
                json.dump(default_profile, f, indent=2)
            logger.info(f"Created default user_profile.json at {profile_file}")
            return default_profile["profiles"]
        
        with open(profile_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if isinstance(data, list):
            logger.warning(f"user_profile.json contains a list, expected dict with 'profiles' key.")
            profiles = data
        elif isinstance(data, dict):
            profiles = data.get('profiles', [])
        else:
            logger.error(f"Invalid user_profile.json format: {type(data)}. Returning default profile.")
            return [{"user_id": "default", "preferred_languages": list(SUPPORTED_LANGUAGES), "preferred_tone": "neutral"}]
        
        if not profiles:
            logger.warning("No profiles found in user_profile.json. Using default profile.")
            profiles = [{"user_id": "default", "preferred_languages": list(SUPPORTED_LANGUAGES), "preferred_tone": "neutral"}]
        
        logger.info(f"Loaded {len(profiles)} user profiles")
        return profiles
    except Exception as e:
        logger.error(f"Failed to load user profiles: {str(e)}. Returning default profile.")
        return [{"user_id": "default", "preferred_languages": list(SUPPORTED_LANGUAGES), "preferred_tone": "neutral"}]

def detect_language(text: str, provided_lang: str = None) -> str:
    """Detect language, prioritizing provided language from input data."""
    if provided_lang and provided_lang in SUPPORTED_LANGUAGES:
        logger.info(f"Using provided language: {provided_lang}")
        return provided_lang
    try:
        lang = detect(text)
        if lang == 'zh-cn':
            logger.info(f"Mapped zh-cn to zh")
            return 'zh'
        if lang not in SUPPORTED_LANGUAGES:
            logger.warning(f"Unsupported language '{lang}', skipping record")
            return None
        logger.info(f"Detected language: {lang}")
        return lang
    except LangDetectException:
        logger.warning("Language detection failed, skipping record")
        return None

def check_profanity(text: str) -> bool:
    """Check for profanity in text."""
    return profanity.contains_profanity(text)

def detect_bias(text: str) -> str:
    """Detect if content is neutral or biased."""
    text_lower = text.lower()
    for keyword in CONTROVERSIAL_KEYWORDS:
        if keyword in text_lower:
            logger.warning(f"Potential bias detected: {keyword}")
            return 'biased'
    return 'neutral'

def validate_against_facts(text: str, facts: List[str]) -> bool:
    """Validate text against truth-source facts."""
    return any(text.lower() in fact.lower() or fact.lower() in text.lower() for fact in facts)

def sanitize_text(text: str, pipeline: str) -> str:
    """Sanitize text based on pipeline."""
    try:
        sanitized = text.strip()
        pipeline_info = VALID_PIPELINES.get(pipeline, {})
        if not pipeline_info:
            logger.error(f"Unknown pipeline '{pipeline}', skipping sanitization")
            return text
        start, end = pipeline_info.get('range', (0, 0))
        sanitized = ''.join(c for c in sanitized if start <= ord(c) <= end or c.isspace())
        return sanitized or text
    except Exception as e:
        logger.error(f"Sanitization failed: {str(e)}")
        return text

def clear_output_directory(output_dir: str, metadata_dir: str) -> None:
    """Clear existing output files."""
    for file in os.listdir(output_dir):
        if file.startswith('content_blocks_') and file.endswith('.json'):
            os.remove(os.path.join(output_dir, file))
            logger.info(f"Deleted existing file: {os.path.join(output_dir, file)}")
    if os.path.exists(metadata_dir):
        shutil.rmtree(metadata_dir)
        logger.info(f"Deleted existing metadata directory: {metadata_dir}")
    os.makedirs(metadata_dir, exist_ok=True)

def save_metadata(block: Dict, metadata_dir: str) -> None:
    """Save metadata for all platforms."""
    content_id = block['content_id']
    for platform in PLATFORMS:
        metadata = {
            'content_id': content_id,
            'source_language': block['source_language'],
            'content_language': block['content_language'],
            'voice_tag': block['voice_tag'],
            'post': block['post'],
            'platform': platform,
            'preferred_tone': block['platform_tones'][platform],
            'processed_at': datetime.now(timezone.utc).isoformat(),
            'type': block['type']
        }
        metadata_file = os.path.join(metadata_dir, f"metadata_{content_id}_{platform}.json")
        try:
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)
            logger.info(f"Saved metadata to {metadata_file}")
        except Exception as e:
            logger.error(f"Failed to save metadata to {metadata_file}: {str(e)}")

def run_miner_sanitizer(input_file: str, languages: List[str], platforms: List[str], sentiment: str, user_id: str = "default") -> None:
    """Run Agent A/F: Knowledge Miner & Sanitizer."""
    logger.info(f"Starting Agent A/F: Knowledge Miner & Sanitizer (sentiment: {sentiment}, user: {user_id})")
    
    # Validate pipelines
    validate_pipelines()
    
    # File paths
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.join(script_dir, '..', 'content', 'structured')
    metadata_dir = os.path.join(output_dir, 'metadata')
    profile_file = os.path.join(script_dir, '..', 'config', 'user_profile.json')
    facts_file = os.path.join(script_dir, '..', 'content', 'raw', 'truth-source.csv')
    
    # Clear output directory
    clear_output_directory(output_dir, metadata_dir)
    
    # Load data
    records = load_input_data(input_file)
    facts = load_facts(facts_file)
    profiles = load_user_profiles(profile_file)
    
    # Find user profile
    user_profile = next((p for p in profiles if p['user_id'] == user_id), profiles[0])
    
    if not records:
        logger.error("No records loaded, exiting")
        return
    
    # Process records
    blocks = []
    for record in records:
        text = record.get('text', '')
        if not text:
            continue
        lang = detect_language(text, record.get('language'))
        if not lang or lang not in languages:
            logger.warning(f"Skipping record: Invalid or unsupported language ({lang})")
            continue
        pipeline = PIPELINES.get(lang, 'latin_pipeline')
        sanitized_text = sanitize_text(text, pipeline)
        
        # Verification
        if check_profanity(sanitized_text):
            logger.warning(f"Profanity detected in text: {sanitized_text}")
            continue
        bias_status = detect_bias(sanitized_text)
        if not validate_against_facts(sanitized_text, facts):
            logger.warning(f"Text does not match truth-source: {sanitized_text}")
            continue
        
        content_id = str(uuid.uuid4())
        block = {
            'content_id': content_id,
            'post': sanitized_text,
            'source_language': lang,
            'content_language': lang,
            'voice_tag': f"{lang}_default",
            'preferred_languages': user_profile.get('preferred_languages', list(SUPPORTED_LANGUAGES)),
            'platform_tones': {
                'twitter': 'neutral',
                'instagram': 'casual',
                'linkedin': 'formal',
                'sanatan': 'devotional'
            },
            'sentiment': sentiment,
            'bias_status': bias_status,
            'type': record.get('type', 'unknown')
        }
        if block['sentiment'] != sentiment:
            logger.warning(f"Skipping block ID {content_id}: sentiment mismatch")
            continue
        blocks.append(block)
        logger.info(f"Sanitized block ID {content_id} (lang: {lang}, pipeline: {pipeline})")
        save_metadata(block, metadata_dir)
    
    # Save blocks
    if blocks:
        timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
        output_file = os.path.join(output_dir, f"content_blocks_{timestamp}.json")
        content = json.dumps(blocks, ensure_ascii=False, indent=2)
        checksum = hashlib.sha256(content.encode('utf-8')).hexdigest()
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(content)
        logger.info(f"Saved {len(blocks)} blocks to {output_file} (checksum: {checksum})")
    else:
        logger.warning("No blocks to save")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Vaani Sentinel X: Miner & Sanitizer")
    parser.add_argument('--input', required=True, help="Input CSV or JSON file")
    parser.add_argument('--languages', nargs='+', required=True, help="Languages to process (e.g., en hi sa zh)")
    parser.add_argument('--platforms', nargs='+', choices=PLATFORMS, default=PLATFORMS, help="Platforms to process")
    parser.add_argument('--sentiment', choices=ALLOWED_SENTIMENTS, default='neutral', help="Sentiment for processing")
    parser.add_argument('--user-id', default='default', help="User ID for profile selection")
    args = parser.parse_args()
    
    run_miner_sanitizer(args.input, args.languages, args.platforms, args.sentiment, args.user_id)