import json
import os
import logging
import glob
import re
import hashlib
import shutil
import argparse
from cryptography.fernet import Fernet
from datetime import datetime
from typing import Dict, Set, List

# Logging setup
USER_ID = 'agent_e_user'
logger = logging.getLogger('security_guard')
logger.setLevel(logging.INFO)

# Ensure logs directory exists relative to the script's location
script_dir = os.path.dirname(os.path.abspath(__file__))
logs_dir = os.path.join(script_dir, '..', 'logs')
os.makedirs(logs_dir, exist_ok=True)

file_handler = logging.FileHandler(os.path.join(logs_dir, 'security_guard.txt'), encoding='utf-8')
file_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - User: %(user)s - %(message)s')
file_handler.setFormatter(formatter)
file_handler.addFilter(lambda record: setattr(record, 'user', USER_ID) or True)
logger.handlers = [file_handler]

# Refined regex for bias detection
BIAS_PATTERNS = {
    'religious': re.compile(
        r'\b(ॐ|Om|Namaha?|Shivaya|Vishnu|Krishna|Allah|Jesus)\b',
        re.IGNORECASE | re.UNICODE
    ),
    'strong_opinionated': re.compile(
        r'\b(superior|inferior|only true)\b',
        re.IGNORECASE
    ),
    'mild_opinionated': re.compile(
        r'\b(amazing|terrible)\b',
        re.IGNORECASE
    ),
    'political': re.compile(
        r'\b(politics|party|election)\b',
        re.IGNORECASE
    ),
    'divisive_context': re.compile(
        r'(better than|worse than|superior to|inferior to|against|oppose)',
        re.IGNORECASE
    )
}

# Whitelist for terms that are safe in specific contexts
WHITELIST = {
    'sa': {'religious': ['ॐ', 'Om', 'Namaha', 'Shivaya', 'Vishnu', 'Krishna']},  # Religious terms are safe in Sanskrit
    'sanatan': {'religious': ['ॐ', 'Om', 'Namaha', 'Shivaya', 'Vishnu', 'Krishna']},  # Religious terms are safe in Sanatan platform
    'instagram': {'mild_opinionated': ['amazing']},  # Allow 'amazing' in Instagram posts
    'twitter': {'mild_opinionated': ['amazing']}     # Allow 'amazing' in Twitter posts
}

def generate_checksum(data: bytes) -> str:
    """Generate SHA-256 checksum for data."""
    try:
        return hashlib.sha256(data).hexdigest()
    except Exception as e:
        logger.error(f"Failed to generate checksum: {str(e)}")
        return ""

def encrypt_content(content: Dict, output_path: str) -> str:
    """Encrypt content and save to output path, return checksum."""
    try:
        key = Fernet.generate_key()
        fernet = Fernet(key)
        content_bytes = json.dumps(content, ensure_ascii=False).encode('utf-8')
        encrypted_content = fernet.encrypt(content_bytes)
        checksum = generate_checksum(encrypted_content)
        if not checksum:
            raise ValueError("Checksum generation failed")
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, 'wb') as f:
            f.write(encrypted_content)
        with open(f"{output_path}.key", 'wb') as f:
            f.write(key)
        logger.info(f"Encrypted content to {output_path} with checksum {checksum}")
        return checksum
    except Exception as e:
        logger.error(f"Failed to encrypt content to {output_path}: {str(e)}")
        return ""

def save_to_alert_dashboard(flagged_items: List[Dict]) -> None:
    """Save flagged items to the alert dashboard JSON file, overwriting previous content."""
    dashboard_path = os.path.join(logs_dir, 'alert_dashboard.json')
    try:
        # Overwrite the dashboard with new flagged items
        with open(dashboard_path, 'w', encoding='utf-8') as f:
            json.dump(flagged_items, f, ensure_ascii=False, indent=2)
        logger.info(f"Saved {len(flagged_items)} flagged items to alert dashboard at {dashboard_path}")
    except Exception as e:
        logger.error(f"Failed to save to alert dashboard at {dashboard_path}: {str(e)}")

def flag_content(file_path: str, flagged_ids: Set[str], flagged_items: List[Dict]) -> int:
    """Flag content for bias and return number of flagged items."""
    flagged_count = 0
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = json.load(f)
        blocks = content if isinstance(content, list) else [content]
        
        # Determine language and platform from file path
        language = None
        platform = None
        is_content_ready = 'content_ready' in file_path.lower()
        if is_content_ready:
            for lang in ['en', 'hi', 'sa']:
                if f'content_ready{os.sep}{lang}' in file_path.lower():
                    language = lang
                    break
            for plat in ['twitter', 'instagram', 'linkedin', 'sanatan']:
                if plat in file_path.lower():
                    platform = plat
                    break
        elif 'content_blocks.json' in file_path.lower():
            # For content_blocks.json, language might be specified in the block
            language = None  # Will be determined per block if available
            platform = 'input'

        for block in blocks:
            content_id = block.get('id')
            if not content_id or content_id in flagged_ids:
                continue
            
            # Determine language: for content_ready, use directory-based language; for content_blocks, use block's language field
            if is_content_ready:
                block_language = language  # Use directory-based language
            else:
                block_language = block.get('language', language)  # Use block's language field for content_blocks.json

            if not block_language:
                logger.warning(f"Language not determined for content ID {content_id} in {file_path}")
                block_language = 'unknown'

            text_fields = [
                block.get('tweet', ''),
                block.get('post', ''),
                block.get('voice_script', ''),
                block.get('content', ''),
                block.get('text', '')
            ]
            text = ' '.join(str(field) for field in text_fields if field)
            if not text:
                logger.info(f"No text found for content ID {content_id} (language: {block_language}, platform: {platform})")
                continue

            logger.info(f"Processing content ID {content_id} (language: {block_language}, platform: {platform})")

            # Check for bias using each pattern category
            religious_match = BIAS_PATTERNS['religious'].search(text)
            strong_opinion_match = BIAS_PATTERNS['strong_opinionated'].search(text)
            mild_opinion_match = BIAS_PATTERNS['mild_opinionated'].search(text)
            political_match = BIAS_PATTERNS['political'].search(text)
            divisive_match = BIAS_PATTERNS['divisive_context'].search(text)

            # Flag political content immediately
            if political_match:
                flagged_term = political_match.group(0)
                start_idx = max(0, political_match.start() - 20)
                end_idx = min(len(text), political_match.end() + 20)
                snippet = text[start_idx:end_idx]
                if start_idx > 0:
                    snippet = '...' + snippet
                if end_idx < len(text):
                    snippet = snippet + '...'
                logger.warning(f"Political bias detected in ID {content_id}: Term '{flagged_term}' found")
                flagged_items.append({
                    'content_id': content_id,
                    'file_path': file_path,
                    'language': block_language,
                    'platform': platform,
                    'flagged_term': flagged_term,
                    'snippet': snippet,
                    'reason': 'Contains political reference',
                    'timestamp': datetime.now().isoformat()
                })
                flagged_ids.add(content_id)
                flagged_count += 1
                continue

            # Flag strong opinionated content
            if strong_opinion_match:
                flagged_term = strong_opinion_match.group(0)
                start_idx = max(0, strong_opinion_match.start() - 20)
                end_idx = min(len(text), strong_opinion_match.end() + 20)
                snippet = text[start_idx:end_idx]
                if start_idx > 0:
                    snippet = '...' + snippet
                if end_idx < len(text):
                    snippet = snippet + '...'
                logger.warning(f"Strong opinionated bias detected in ID {content_id}: Term '{flagged_term}' found")
                flagged_items.append({
                    'content_id': content_id,
                    'file_path': file_path,
                    'language': block_language,
                    'platform': platform,
                    'flagged_term': flagged_term,
                    'snippet': snippet,
                    'reason': 'Contains strong opinionated language',
                    'timestamp': datetime.now().isoformat()
                })
                flagged_ids.add(content_id)
                flagged_count += 1
                continue

            # Flag mild opinionated content only if in divisive context
            if mild_opinion_match and divisive_match:
                flagged_term = mild_opinion_match.group(0)
                context_phrase = divisive_match.group(0)
                start_idx = max(0, mild_opinion_match.start() - 20)
                end_idx = min(len(text), mild_opinion_match.end() + 20)
                snippet = text[start_idx:end_idx]
                if start_idx > 0:
                    snippet = '...' + snippet
                if end_idx < len(text):
                    snippet = snippet + '...'
                # Check whitelist for mild opinionated terms
                is_whitelisted = False
                if platform and platform in WHITELIST:
                    if 'mild_opinionated' in WHITELIST[platform] and flagged_term.lower() in [term.lower() for term in WHITELIST[platform]['mild_opinionated']]:
                        is_whitelisted = True
                if is_whitelisted:
                    logger.info(f"Mild opinionated term '{flagged_term}' whitelisted for ID {content_id} (language: {block_language}, platform: {platform})")
                    continue
                logger.warning(f"Mild opinionated term '{flagged_term}' in divisive context '{context_phrase}' for ID {content_id}")
                flagged_items.append({
                    'content_id': content_id,
                    'file_path': file_path,
                    'language': block_language,
                    'platform': platform,
                    'flagged_term': flagged_term,
                    'snippet': snippet,
                    'reason': 'Contains opinionated language in divisive context',
                    'timestamp': datetime.now().isoformat()
                })
                flagged_ids.add(content_id)
                flagged_count += 1
                continue
            elif mild_opinion_match:
                flagged_term = mild_opinion_match.group(0)
                # Check whitelist for mild opinionated terms
                is_whitelisted = False
                if platform and platform in WHITELIST:
                    if 'mild_opinionated' in WHITELIST[platform] and flagged_term.lower() in [term.lower() for term in WHITELIST[platform]['mild_opinionated']]:
                        is_whitelisted = True
                if is_whitelisted:
                    logger.info(f"Mild opinionated term '{flagged_term}' whitelisted for ID {content_id} (language: {block_language}, platform: {platform})")
                else:
                    logger.info(f"Mild opinionated term '{flagged_term}' ignored for ID {content_id} (no divisive context)")

            # Handle religious content: flag only if harmful
            if religious_match:
                flagged_term = religious_match.group(0)
                # Check if the content is in a context where religious terms are safe
                is_safe_context = False
                if block_language and block_language in WHITELIST:
                    if 'religious' in WHITELIST[block_language] and flagged_term.lower() in [term.lower() for term in WHITELIST[block_language]['religious']]:
                        is_safe_context = True
                if platform and platform in WHITELIST:
                    if 'religious' in WHITELIST[platform] and flagged_term.lower() in [term.lower() for term in WHITELIST[platform]['religious']]:
                        is_safe_context = True
                
                if is_safe_context:
                    logger.info(f"Religious term '{flagged_term}' is safe for ID {content_id} (language: {block_language}, platform: {platform})")
                    continue

                # For non-safe contexts (e.g., twitter, instagram, linkedin), flag only if in a divisive or strong opinionated context
                if platform in ['twitter', 'instagram', 'linkedin'] and (divisive_match or strong_opinion_match):
                    context_phrase = divisive_match.group(0) if divisive_match else strong_opinion_match.group(0)
                    start_idx = max(0, religious_match.start() - 20)
                    end_idx = min(len(text), religious_match.end() + 20)
                    snippet = text[start_idx:end_idx]
                    if start_idx > 0:
                        snippet = '...' + snippet
                    if end_idx < len(text):
                        snippet = snippet + '...'
                    logger.warning(f"Harmful religious content detected in ID {content_id}: Term '{flagged_term}' in context '{context_phrase}'")
                    flagged_items.append({
                        'content_id': content_id,
                        'file_path': file_path,
                        'language': block_language,
                        'platform': platform,
                        'flagged_term': flagged_term,
                        'snippet': snippet,
                        'reason': 'Contains religious term in harmful context',
                        'timestamp': datetime.now().isoformat()
                    })
                    flagged_ids.add(content_id)
                    flagged_count += 1
                else:
                    logger.info(f"Religious term '{flagged_term}' not flagged for ID {content_id} (no harmful context)")
    except Exception as e:
        logger.error(f"Failed to flag content in {file_path}: {str(e)}")
    return flagged_count

def clear_all_encrypted_directories() -> None:
    """Clear all encrypted directories in the archives folder."""
    archives_dir = os.path.join(script_dir, '..', 'archives')
    try:
        for dir_name in os.listdir(archives_dir):
            if dir_name.startswith('encrypted_'):
                dir_path = os.path.join(archives_dir, dir_name)
                if os.path.isdir(dir_path):
                    shutil.rmtree(dir_path)
                    logger.info(f"Cleared encrypted directory: {dir_path}")
    except Exception as e:
        logger.error(f"Failed to clear encrypted directories in {archives_dir}: {str(e)}")

def clear_encrypted_directory(lang: str) -> None:
    """Clear the encrypted output directory for the specified language."""
    encrypted_dir = os.path.join(script_dir, '..', 'archives', f'encrypted_{lang}')
    try:
        os.makedirs(encrypted_dir, exist_ok=True)
    except Exception as e:
        logger.error(f"Failed to create encrypted directory {encrypted_dir}: {str(e)}")

def process_security(selected_language: str) -> None:
    """Run Agent E: Security & Ethics Guard for the specified language."""
    logger.info(f"Starting Agent E: Security & Ethics Guard for language: {selected_language}")

    # Clear all encrypted directories to start fresh
    clear_all_encrypted_directories()

    flagged_ids = set()
    flagged_items = []  # List to store flagged items for the dashboard
    total_flagged = 0

    # Flag input content (only if language matches or is 'all')
    input_file = os.path.join(script_dir, '..', 'content', 'structured', 'content_blocks.json')
    if os.path.exists(input_file):
        with open(input_file, 'r', encoding='utf-8') as f:
            content = json.load(f)
        blocks = content if isinstance(content, list) else [content]
        should_flag_input = False
        for block in blocks:
            block_lang = block.get('language')
            if block_lang and (selected_language == 'all' or block_lang == selected_language):
                should_flag_input = True
                break
        if should_flag_input:
            logger.info(f"Flagging input content in {input_file}")
            total_flagged += flag_content(input_file, flagged_ids, flagged_items)
            logger.info(f"Flagged {total_flagged} potentially controversial input items")
        else:
            logger.info(f"Skipping input file {input_file} as no blocks match language {selected_language}")
    else:
        logger.warning(f"Input file not found: {input_file}")

    # Flag and encrypt output content by language
    languages_to_process = ['en', 'hi', 'sa'] if selected_language == 'all' else [selected_language]
    for lang in languages_to_process:
        # Create the encrypted directory for this language
        clear_encrypted_directory(lang)

        lang_dir = os.path.join(script_dir, '..', 'content', 'content_ready', lang)
        if not os.path.exists(lang_dir):
            logger.warning(f"No content directory found for {lang} at {lang_dir}")
            continue

        content_files = glob.glob(os.path.join(lang_dir, '*.json'))
        if not content_files:
            logger.info(f"No JSON files found in {lang_dir}")
            continue

        for file_path in content_files:
            logger.info(f"Flagging output content in {file_path}")
            total_flagged += flag_content(file_path, flagged_ids, flagged_items)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = json.load(f)
                output_path = os.path.join(script_dir, '..', 'archives', f'encrypted_{lang}', f"{os.path.basename(file_path)}.enc")
                checksum = encrypt_content(content, output_path)
                if not checksum:
                    logger.error(f"Encryption failed for {file_path}")
            except Exception as e:
                logger.error(f"Failed to process {file_path}: {str(e)}")

    # Save flagged items to the alert dashboard
    if flagged_items:
        save_to_alert_dashboard(flagged_items)
    else:
        # Ensure the dashboard is cleared if no items are flagged
        save_to_alert_dashboard([])

    logger.info(f"Flagged {total_flagged} potentially controversial items")
    logger.info(f"Completed security processing at {datetime.now().isoformat()}")

def main() -> None:
    """Main function to run the security guard with a language argument."""
    parser = argparse.ArgumentParser(description="Run Agent E: Security & Ethics Guard")
    parser.add_argument('language', choices=['en', 'hi', 'sa', 'all'], help="Language to process (en, hi, sa, all)")
    args = parser.parse_args()
    
    process_security(args.language)

if __name__ == "__main__":
    main()