import os
import json
import logging
import argparse
import shutil
from datetime import datetime, timezone
from typing import List, Dict
from langdetect import detect, LangDetectException

# Logging setup
USER_ID = 'agent_f_user'
logger = logging.getLogger('multilingual_pipeline')
logger.setLevel(logging.INFO)
log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'logs')
os.makedirs(log_dir, exist_ok=True)
log_path = os.path.join(log_dir, 'multilingual_pipeline.txt')
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
VALID_PIPELINES = {
    'latin_pipeline': {'range': (0x0000, 0x007F), 'description': 'ASCII characters'},
    'devanagari_pipeline': {'range': (0x0900, 0x097F), 'description': 'Devanagari script'},
    'cjk_pipeline': {'range': (0x4E00, 0x9FFF), 'description': 'CJK characters'},
    'dravidian_pipeline': {'range': (0x0B80, 0x0BFF), 'description': 'Dravidian scripts (Tamil, etc.)'},
    'arabic_pipeline': {'range': (0x0600, 0x06FF), 'description': 'Arabic script'}
}
PLATFORMS = ['twitter', 'instagram', 'linkedin', 'sanatan']
ALLOWED_SENTIMENTS = ['uplifting', 'neutral', 'devotional']

def validate_pipelines() -> None:
    """Validate that all pipelines in PIPELINES are defined in VALID_PIPELINES."""
    for lang, pipeline in PIPELINES.items():
        if pipeline not in VALID_PIPELINES:
            logger.error(f"Invalid pipeline '{pipeline}' for language '{lang}'")
            raise ValueError(f"Pipeline '{pipeline}' not defined in VALID_PIPELINES")
    logger.info("All pipelines validated successfully")

def load_content_blocks(input_dir: str) -> List[Dict]:
    """Load the latest content_blocks_*.json file."""
    try:
        files = [f for f in os.listdir(input_dir) if f.startswith('content_blocks_') and f.endswith('.json')]
        if not files:
            logger.error("No content_blocks_*.json files found")
            return []
        latest_file = max(files, key=lambda f: os.path.getmtime(os.path.join(input_dir, f)))
        file_path = os.path.join(input_dir, latest_file)
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        logger.info(f"Loaded {len(data)} blocks from {file_path}")
        return data
    except Exception as e:
        logger.error(f"Failed to load content blocks: {str(e)}")
        return []

def clear_output_directory(output_dir: str) -> None:
    """Clear existing files in output directory."""
    try:
        if os.path.exists(output_dir):
            shutil.rmtree(output_dir)
            logger.info(f"Cleared output directory: {output_dir}")
        os.makedirs(output_dir, exist_ok=True)
    except PermissionError as e:
        logger.error(f"Permission denied while clearing output directory {output_dir}: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Failed to clear output directory {output_dir}: {str(e)}")
        raise

def detect_language(text: str) -> str:
    """Detect language with fallback to 'en' for unsupported languages."""
    try:
        detected_lang = detect(text)
        if detected_lang == 'zh-cn':
            logger.info("Mapped zh-cn to zh")
            return 'zh'
        if detected_lang not in SUPPORTED_LANGUAGES:
            logger.warning(f"Detected language '{detected_lang}' not supported, defaulting to 'en'")
            return 'en'
        logger.info(f"Detected language: {detected_lang}")
        return detected_lang
    except LangDetectException as e:
        logger.error(f"Language detection failed: {str(e)}, defaulting to 'en'")
        return 'en'

def route_content_block(block: Dict, pipeline: str, platform: str, sentiment: str, output_dir: str) -> None:
    """Route a content block to a pipeline and platform."""
    content_id = block['content_id']
    source_language = block['source_language']
    text = block['post']
    text_preview = text[:50].replace('\n', ' ') + '...' if len(text) > 50 else text
    preferred_tone = block['platform_tones'].get(platform, 'neutral')
    
    output_data = {
        'content_id': content_id,
        'post': text,
        'source_language': source_language,
        'content_language': block.get('content_language', source_language),
        'voice_tag': block.get('voice_tag', f"{source_language}_default"),
        'pipeline': pipeline,
        'platform': platform,
        'preferred_tone': preferred_tone,
        'sentiment': sentiment,
        'preferred_languages': block['preferred_languages'],
        'bias_status': block.get('bias_status', 'neutral'),
        'type': block.get('type', 'unknown'),
        'processed_at': datetime.now(timezone.utc).isoformat()
    }
    
    pipeline_dir = os.path.join(output_dir, pipeline)
    try:
        os.makedirs(pipeline_dir, exist_ok=True)
        output_file = os.path.join(pipeline_dir, f"{content_id}_{platform}.json")
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)
        logger.info(f"Routed block ID {content_id} to {pipeline}/{platform} (file: {output_file}, text: {text_preview})")
    except PermissionError as e:
        logger.error(f"Permission denied while writing to {output_file}: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Failed to route block ID {content_id}: {str(e)}")
        raise

def run_multilingual_pipeline(languages: List[str] = None, platforms: List[str] = None, sentiment: str = 'neutral') -> None:
    """Run Agent F: Multilingual Pipeline."""
    if sentiment not in ALLOWED_SENTIMENTS:
        logger.error(f"Invalid sentiment: {sentiment}. Supported: {', '.join(ALLOWED_SENTIMENTS)}")
        raise ValueError(f"Invalid sentiment: {sentiment}")
    
    if platforms:
        invalid_platforms = [p for p in platforms if p not in PLATFORMS]
        if invalid_platforms:
            logger.error(f"Invalid platforms: {invalid_platforms}. Supported: {', '.join(PLATFORMS)}")
            raise ValueError(f"Invalid platforms: {invalid_platforms}")
    
    if languages:
        invalid_languages = [l for l in languages if l not in SUPPORTED_LANGUAGES]
        if invalid_languages:
            logger.error(f"Invalid languages: {invalid_languages}. Supported: {', '.join(SUPPORTED_LANGUAGES)}")
            raise ValueError(f"Invalid languages: {invalid_languages}")
    
    logger.info(f"Starting Agent F: Multilingual Pipeline (sentiment: {sentiment})")
    
    # Validate pipelines
    validate_pipelines()
    
    # File paths
    script_dir = os.path.dirname(os.path.abspath(__file__))
    input_dir = os.path.join(script_dir, '..', 'content', 'structured')
    output_dir = os.path.join(script_dir, '..', 'content', 'multilingual_ready')
    
    # Clear output directory
    clear_output_directory(output_dir)
    
    # Load content blocks
    content_blocks = load_content_blocks(input_dir)
    if not content_blocks:
        logger.error("No content blocks loaded, exiting")
        return
    
    # Filter by languages
    if languages:
        content_blocks = [block for block in content_blocks if block['source_language'] in languages]
        logger.info(f"Filtered to {len(content_blocks)} blocks for languages: {', '.join(languages)}")
    
    # Route blocks
    platforms = platforms or PLATFORMS
    language_counts = {lang: 0 for lang in SUPPORTED_LANGUAGES}
    for block in content_blocks:
        source_language = block.get('source_language', '')
        content_id = block['content_id']
        text = block['post']
        block_sentiment = block.get('sentiment', 'neutral')
        
        if not text.strip():
            logger.warning(f"Skipping block ID {content_id} due to empty or whitespace-only text")
            continue
        
        if block_sentiment != sentiment:
            logger.warning(f"Skipping block ID {content_id} due to sentiment mismatch (block: {block_sentiment}, required: {sentiment})")
            continue
        
        if not source_language or source_language not in SUPPORTED_LANGUAGES:
            logger.warning(f"Invalid or missing language '{source_language}' for block ID {content_id}, detecting language")
            source_language = detect_language(text)
            block['source_language'] = source_language
        
        if languages and source_language not in languages:
            logger.info(f"Skipping block ID {content_id} (language: {source_language}) as it does not match selected languages")
            continue
        
        pipeline = PIPELINES.get(source_language, 'latin_pipeline')
        for platform in platforms:
            route_content_block(block, pipeline, platform, sentiment, output_dir)
            language_counts[source_language] += 1
    
    for lang, count in language_counts.items():
        if count > 0:
            logger.info(f"Routed {count} blocks to {lang} pipeline")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Vaani Sentinel X: Multilingual Pipeline")
    parser.add_argument('--languages', nargs='+', help="Languages to process (e.g., en hi sa)")
    parser.add_argument('--platforms', nargs='+', choices=PLATFORMS, help="Platforms to route to (e.g., twitter instagram linkedin sanatan)")
    parser.add_argument('--sentiment', choices=ALLOWED_SENTIMENTS, default='neutral', help="Sentiment for processing (uplifting, neutral, devotional)")
    args = parser.parse_args()
    
    run_multilingual_pipeline(args.languages, args.platforms, args.sentiment)