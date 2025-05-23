import csv
import json
import os
import logging
from typing import List, Dict, Set
from langdetect import detect, LangDetectException

# Logging setup for Agent A (Knowledge Miner & Sanitizer)
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

# Supported languages
SUPPORTED_LANGUAGES = {'en', 'hi', 'sa'}

# Keywords for Sanskrit detection
SANSKRIT_KEYWORDS = {'ॐ', 'महादेव', 'नमः', 'शिवाय', 'विद्या', 'विनयं'}

def load_sample_data(file_path: str) -> List[Dict]:
    """Load sample data from CSV and strip comments from fields."""
    data = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Strip comments (e.g., # Comment) from each field
                cleaned_row = {key: value.split('#')[0].strip() for key, value in row.items()}
                data.append(cleaned_row)
        logger.info(f"Loaded {len(data)} records from {file_path}")
        return data
    except Exception as e:
        logger.error(f"Failed to load sample data from {file_path}: {str(e)}")
        return []

def load_truth_source(file_path: str) -> Set[str]:
    """Load truth source facts from CSV."""
    facts = set()
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            next(reader)  # Skip header
            for row in reader:
                if row and row[0].strip():
                    facts.add(row[0].strip())
        logger.info(f"Loaded {len(facts)} facts from {file_path}")
        return facts
    except Exception as e:
        logger.error(f"Failed to load truth source from {file_path}: {str(e)}")
        return set()

def detect_language(text: str) -> str:
    """Detect the language of the given text with custom Sanskrit detection."""
    # Custom rule: Check for Sanskrit keywords
    if any(keyword in text for keyword in SANSKRIT_KEYWORDS):
        logger.info("Detected Sanskrit based on keywords")
        return 'sa'
    
    # Fallback to langdetect
    try:
        detected_lang = detect(text)
        if detected_lang not in SUPPORTED_LANGUAGES:
            logger.warning(f"Detected language '{detected_lang}' not supported, defaulting to 'en'")
            return 'en'
        logger.info(f"Detected language via langdetect: {detected_lang}")
        return detected_lang
    except LangDetectException as e:
        logger.error(f"Language detection failed: {str(e)}, defaulting to 'en'")
        return 'en'

def check_profanity(text: str) -> bool:
    """Check for profanity in the text."""
    profanity_words = {'damn', 'offensive'}  # Simplified list for this example
    words = set(text.lower().split())
    return bool(words & profanity_words)

def check_bias(text: str, language: str) -> str:
    """Check for bias in the text (e.g., political, religious, or opinionated content)."""
    # Political bias detection
    political_keywords = {'political', 'party'}
    if any(keyword in text.lower() for keyword in political_keywords):
        return "biased"
    
    # Religious bias detection
    religious_keywords = {'ॐ', 'शिवाय', 'महादेव'}  # Religious terms
    harmful_keywords = {'नाशति', 'destroy', 'hate', 'enemy', 'शत्रून्'}  # Harmful context
    
    # Check if the text contains religious terms
    has_religious_content = any(keyword in text for keyword in religious_keywords)
    
    # If religious content is present, check for harmful context
    if has_religious_content:
        if any(harmful in text for harmful in harmful_keywords):
            return "biased"  # Harmful religious content
        return "neutral"  # Benign religious content
    
    # Default case: no bias detected
    return "neutral"

def sanitize_content_block(block: Dict, truth_facts: Set[str]) -> Dict:
    """Sanitize a content block and add metadata with language detection."""
    text = block['text']
    content_type = block['type']
    
    # Check for language field; if missing or invalid, detect the language
    language = block.get('language', '').strip()
    if not language or language not in SUPPORTED_LANGUAGES:
        logger.warning(f"Language field missing or invalid ('{language}') for block ID {block['id']}, detecting language")
        language = detect_language(text)
        block['language'] = language
    
    # Check for profanity
    has_profanity = check_profanity(text)
    
    # Check for bias
    bias = check_bias(text, language)
    
    # Verify facts against truth source
    verified = False
    if content_type == 'fact':
        verified = text in truth_facts
    # For non-fact types (e.g., quote, micro-article), verification is not required
    else:
        verified = False  # Default for non-facts
    
    # Add metadata to the block
    block['profanity'] = has_profanity
    block['bias'] = bias
    block['verified'] = verified
    
    return block

def run_miner_sanitizer() -> None:
    """Run Agent A: Knowledge Miner & Sanitizer."""
    logger.info("Starting Agent A: Knowledge Miner & Sanitizer")
    
    # Define file paths
    script_dir = os.path.dirname(os.path.abspath(__file__))
    raw_dir = os.path.join(script_dir, '..', 'content', 'raw')
    structured_dir = os.path.join(script_dir, '..', 'content', 'structured')
    sample_file = os.path.join(raw_dir, 'sample.csv')
    truth_file = os.path.join(raw_dir, 'truth-source.csv')
    output_file = os.path.join(structured_dir, 'content_blocks.json')
    
    # Create output directory if it doesn't exist
    os.makedirs(structured_dir, exist_ok=True)
    
    # Load data
    sample_data = load_sample_data(sample_file)
    if not sample_data:
        logger.error("No sample data loaded, exiting")
        return
    
    truth_facts = load_truth_source(truth_file)
    
    # Sanitize content blocks
    sanitized_blocks = []
    for block in sample_data:
        block_id = block['id']
        sanitized_block = sanitize_content_block(block, truth_facts)
        
        # Skip blocks that fail sanitization
        if sanitized_block['profanity']:
            logger.warning(f"Skipping block ID {block_id} (lang: {sanitized_block['language']}, profanity: True, bias: {sanitized_block['bias']}, verified: {sanitized_block['verified']})")
            continue
        if sanitized_block['bias'] == "biased":
            logger.warning(f"Skipping block ID {block_id} (lang: {sanitized_block['language']}, profanity: {sanitized_block['profanity']}, bias: biased, verified: {sanitized_block['verified']})")
            continue
        if sanitized_block['type'] == 'fact' and not sanitized_block['verified']:
            logger.warning(f"Skipping block ID {block_id} (lang: {sanitized_block['language']}, profanity: {sanitized_block['profanity']}, bias: {sanitized_block['bias']}, verified: False)")
            continue
        
        logger.info(f"Sanitized block ID {block_id}")
        sanitized_blocks.append(sanitized_block)
    
    # Save sanitized blocks
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(sanitized_blocks, f, ensure_ascii=False, indent=2)
    logger.info(f"Saved {len(sanitized_blocks)} content blocks to {output_file}")
    logger.info(f"Processed {len(sanitized_blocks)} content blocks")

if __name__ == "__main__":
    run_miner_sanitizer()