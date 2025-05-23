import json
import os
import logging
import sys
import shutil
from typing import Dict, List
from langdetect import detect, LangDetectException

# Logging setup for Agent F (Multilingual Pipeline)
USER_ID = 'agent_f_user'
logger = logging.getLogger('multilingual_pipeline')
logger.setLevel(logging.INFO)
# Compute absolute path for logs directory
script_dir = os.path.dirname(os.path.abspath(__file__))
log_dir = os.path.join(script_dir, '..', 'logs')
os.makedirs(log_dir, exist_ok=True)
log_path = os.path.join(log_dir, 'multilingual_pipeline.txt')
file_handler = logging.FileHandler(log_path, encoding='utf-8')
file_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - User: %(user)s - %(message)s')
file_handler.setFormatter(formatter)
file_handler.addFilter(lambda record: setattr(record, 'user', USER_ID) or True)
logger.handlers = [file_handler]

# Valid languages for routing (Task 2)
VALID_LANGUAGES = {'en', 'hi', 'sa'}

def load_content_blocks(input_path: str) -> List[Dict]:
    """Load sanitized content blocks from JSON (Task 2: Agent F)."""
    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            blocks = json.load(f)
        logger.info(f"Loaded {len(blocks)} content blocks from {input_path}")
        return blocks
    except Exception as e:
        logger.error(f"Failed to load content blocks: {str(e)}")
        raise

def clear_output_directory(output_dir: str) -> None:
    """Clear the output directory before routing new blocks."""
    if os.path.exists(output_dir):
        try:
            shutil.rmtree(output_dir)
            logger.info(f"Cleared output directory: {output_dir}")
        except Exception as e:
            logger.error(f"Failed to clear output directory {output_dir}: {str(e)}")
            raise
    os.makedirs(output_dir, exist_ok=True)

def detect_language(text: str) -> str:
    """Detect the language of the given text using langdetect."""
    try:
        detected_lang = detect(text)
        if detected_lang not in VALID_LANGUAGES:
            logger.warning(f"Detected language '{detected_lang}' not supported, defaulting to 'en'")
            return 'en'
        logger.info(f"Detected language: {detected_lang}")
        return detected_lang
    except LangDetectException as e:
        logger.error(f"Language detection failed: {str(e)}, defaulting to 'en'")
        return 'en'

def route_blocks(blocks: List[Dict], output_dir: str, selected_language: str) -> None:
    """Route blocks to language-specific folders for multilingual processing (Task 2: Agent F)."""
    language_counts = {lang: 0 for lang in VALID_LANGUAGES}
    
    for block in blocks:
        language = block.get('language', '').strip()
        block_id = block['id']
        text = block['text']
        text_preview = text[:50].replace('\n', ' ') + '...' if len(text) > 50 else text
        
        # Validate or detect language
        if not language or language not in VALID_LANGUAGES:
            logger.warning(f"Invalid or missing language '{language}' for block ID {block_id}, detecting language")
            language = detect_language(text)
            block['language'] = language
        
        # Filter blocks by selected language
        if selected_language != 'all' and language != selected_language:
            logger.info(f"Skipping block ID {block_id} (language: {language}) as it does not match selected language: {selected_language}")
            continue
        
        try:
            lang_dir = os.path.join(output_dir, language)
            os.makedirs(lang_dir, exist_ok=True)
            
            output_path = os.path.join(lang_dir, f'block_{block_id}.json')
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(block, f, ensure_ascii=False, indent=2)
            
            language_counts[language] += 1
            logger.info(f"Routed block ID {block_id} to {output_path} (text: {text_preview})")
            
        except Exception as e:
            logger.error(f"Failed to route block ID {block_id}: {str(e)}")
            continue
    
    # If not processing all languages, remove directories for other languages
    if selected_language != 'all':
        for lang in VALID_LANGUAGES:
            if lang != selected_language:
                lang_dir = os.path.join(output_dir, lang)
                if os.path.exists(lang_dir):
                    try:
                        shutil.rmtree(lang_dir)
                        logger.info(f"Removed directory for unselected language: {lang_dir}")
                    except Exception as e:
                        logger.error(f"Failed to remove directory {lang_dir}: {str(e)}")
    
    for lang, count in language_counts.items():
        if count > 0:
            logger.info(f"Routed {count} blocks to {lang} directory")

def run_multilingual_pipeline(selected_language: str) -> None:
    """Run Agent F: Multilingual Pipeline (Task 2)."""
    logger.info(f"Starting Agent F: Multilingual Pipeline for language: {selected_language}")
    
    # Compute absolute paths
    script_dir = os.path.dirname(os.path.abspath(__file__))
    input_path = os.path.join(script_dir, '..', 'content', 'structured', 'content_blocks.json')
    output_dir = os.path.join(script_dir, '..', 'content', 'multilingual_ready')
    
    # Clear the output directory before routing
    clear_output_directory(output_dir)
    
    blocks = load_content_blocks(input_path)
    route_blocks(blocks, output_dir, selected_language)
    
    logger.info("Multilingual pipeline completed")

if __name__ == "__main__":
    # Check for language argument
    if len(sys.argv) < 2:
        logger.error("Language argument required. Usage: python multilingual_pipeline.py <language>")
        sys.exit(1)

    selected_language = sys.argv[1]
    if selected_language not in ['en', 'hi', 'sa', 'all']:
        logger.error(f"Invalid language: {selected_language}. Supported languages: en, hi, sa, all")
        sys.exit(1)

    run_multilingual_pipeline(selected_language)