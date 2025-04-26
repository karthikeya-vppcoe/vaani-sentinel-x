import re
import json
import os
import logging
from datetime import datetime
from cryptography.fernet import Fernet

# Custom filter to add user field to log records
class UserFilter(logging.Filter):
    def __init__(self, user_id):
        super().__init__()
        self.user_id = user_id

    def filter(self, record):
        record.user = self.user_id
        return True

# Configure logging
USER_ID = 'agent_e_user'
logger = logging.getLogger('security_guard')
logger.setLevel(logging.INFO)

# Create file handler
os.makedirs('logs', exist_ok=True)
file_handler = logging.FileHandler('logs/security.log')
file_handler.setLevel(logging.INFO)

# Create formatter with the custom format
formatter = logging.Formatter('%(asctime)s - %(levelname)s - User: %(user)s - %(message)s')
file_handler.setFormatter(formatter)

# Add the custom filter to inject the user field
file_handler.addFilter(UserFilter(USER_ID))

# Add a stream handler for console output
stream_handler = logging.StreamHandler()
stream_handler.setLevel(logging.INFO)
stream_handler.setFormatter(formatter)
stream_handler.addFilter(UserFilter(USER_ID))

# Add handlers to the logger
logger.handlers = []
logger.addHandler(file_handler)
logger.addHandler(stream_handler)

# Reduce verbosity of external libraries
logging.getLogger('httpx').setLevel(logging.WARNING)
logging.getLogger('httpcore').setLevel(logging.WARNING)

# Controversial terms regex
CONTROVERSIAL_TERMS = re.compile(
    r'\b(religion|religious|politics|political|bias|offensive|racist|sexist|controversial)\b',
    re.IGNORECASE
)

def flag_content(file_path, is_input=True):
    """Flag controversial content in JSON files."""
    source = 'input' if is_input else 'output'
    logger.info(f"User: {USER_ID} - Flagging {source} content in {file_path}")
    try:
        with open(file_path, 'r') as f:
            content = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logger.error(f"User: {USER_ID} - Failed to load {file_path}: {str(e)}")
        raise

    alerts = []
    if is_input:
        # Process input content_blocks.json
        for block in content:
            text = block.get('text', '')
            block_id = block.get('id', 'unknown')
            if CONTROVERSIAL_TERMS.search(text):
                alert = f"Controversial {source} content detected in block ID {block_id}: {text[:50]}..."
                logger.warning(f"User: {USER_ID} - {alert}")
                alerts.append({'id': block_id, 'alert': alert, 'source': source})
    else:
        # Process output JSON (tweet, post, voice_script)
        content_type = os.path.basename(file_path).split('_')[0]
        content_id = os.path.basename(file_path).split('_')[1]
        text = content.get(content_type if content_type != 'voice' else 'voice_script', '')
        if CONTROVERSIAL_TERMS.search(text):
            alert = f"Controversial {source} content detected in {content_type} ID {content_id}: {text[:50]}..."
            logger.warning(f"User: {USER_ID} - {alert}")
            alerts.append({'id': content_id, 'alert': alert, 'source': source})

    return alerts

def encrypt_content(content_dir, encrypted_output):
    """Encrypt all content in the directory and save to a single file."""
    key = Fernet.generate_key()
    fernet = Fernet(key)
    all_content = []

    # Collect all content files, excluding encrypted.json and encrypted.json.key
    for filename in os.listdir(content_dir):
        if filename.endswith('.json') and filename not in ['encrypted.json', 'encrypted.json.key']:
            file_path = os.path.join(content_dir, filename)
            try:
                with open(file_path, 'r') as f:
                    all_content.append(json.load(f))
                logger.info(f"User: {USER_ID} - Successfully loaded {filename} for encryption")
            except json.JSONDecodeError as e:
                logger.error(f"User: {USER_ID} - Failed to parse {filename} as JSON: {e}")
                continue
            except Exception as e:
                logger.error(f"User: {USER_ID} - Error reading {filename}: {e}")
                continue

    if not all_content:
        logger.warning(f"User: {USER_ID} - No valid content files found to encrypt")
        return

    # Encrypt the combined content
    combined_content = json.dumps(all_content).encode()
    encrypted_content = fernet.encrypt(combined_content)

    # Save encrypted content and key
    with open(encrypted_output, 'wb') as f:
        f.write(encrypted_content)
    with open(f"{encrypted_output}.key", 'wb') as f:
        f.write(key)

    logger.info(f"User: {USER_ID} - Encrypted content saved to {encrypted_output}")

def main():
    """Main function to run Agent E."""
    logger.info(f"User: {USER_ID} - Starting Agent E: Security & Ethics Guard")
    input_file = 'content/structured/content_blocks.json'
    content_dir = 'content/content_ready'
    encrypted_output = 'content/content_ready/encrypted.json'

    # Flag input content
    input_alerts = flag_content(input_file, is_input=True)
    print(f"Flagged {len(input_alerts)} potentially controversial input items. See logs/security.log")

    # Flag output content
    output_alerts = []
    for filename in os.listdir(content_dir):
        if filename.endswith('.json') and 'encrypted' not in filename:
            file_path = os.path.join(content_dir, filename)
            output_alerts.extend(flag_content(file_path, is_input=False))
    print(f"Flagged {len(output_alerts)} potentially controversial output items. See logs/security.log")

    # Encrypt content
    encrypt_content(content_dir, encrypted_output)
    print(f"Encrypted content saved to {encrypted_output}")

    logger.info(f"User: {USER_ID} - Completed processing at {datetime.now()}")

if __name__ == "__main__":
    main()