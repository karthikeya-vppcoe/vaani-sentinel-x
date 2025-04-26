import pandas as pd
import json
import os
import re
import logging
from datetime import datetime
from better_profanity import profanity
from textblob import TextBlob

# Custom filter to add user field to log records
class UserFilter(logging.Filter):
    def __init__(self, user_id):
        super().__init__()
        self.user_id = user_id

    def filter(self, record):
        record.user = self.user_id
        return True

# Configure logging
USER_ID = 'agent_a_user'
logger = logging.getLogger('miner_sanitizer')
logger.setLevel(logging.INFO)

# Create file handler
os.makedirs('logs', exist_ok=True)
file_handler = logging.FileHandler('logs/log.txt')
file_handler.setLevel(logging.INFO)

# Create formatter with the custom format
formatter = logging.Formatter('%(asctime)s - %(levelname)s - User: %(user)s - %(message)s')
file_handler.setFormatter(formatter)

# Add the custom filter to inject the user field
file_handler.addFilter(UserFilter(USER_ID))

# Add the handler to the logger
logger.handlers = []
logger.addHandler(file_handler)

# Reduce verbosity of external libraries
logging.getLogger('httpx').setLevel(logging.WARNING)
logging.getLogger('httpcore').setLevel(logging.WARNING)

def load_data(file_path):
    logger.info(f"Loading data from {file_path}", extra={"user": USER_ID})
    if file_path.endswith('.csv'):
        return pd.read_csv(file_path)
    elif file_path.endswith('.json'):
        return pd.read_json(file_path)
    raise ValueError("Unsupported file format")

def check_profanity(text):
    return profanity.contains_profanity(text)

def check_bias(text):
    blob = TextBlob(text)
    polarity = blob.sentiment.polarity
    political_keywords = re.compile(r'\b(politics|political|party|government|election)\b', re.IGNORECASE)
    has_political_content = bool(political_keywords.search(text))
    emotional_keywords = re.compile(r'\b(amazing|terrible|horrible|wonderful|awful|fantastic|disgusting)\b', re.IGNORECASE)
    has_emotional_content = bool(emotional_keywords.search(text))
    is_biased = abs(polarity) > 0.5 or has_political_content or has_emotional_content
    return "biased" if is_biased else "neutral"

def verify_content(text, truth_source, content_type):
    truth_df = pd.read_csv(truth_source)
    if content_type == 'fact':
        # Stricter verification for facts
        return text.lower() in truth_df['fact'].str.lower().values
    elif content_type == 'quote':
        # Quotes don't need truth verification
        return True
    elif content_type == 'micro-article':
        # Partial match for micro-articles
        return any(text.lower() in fact.lower() or fact.lower() in text.lower() for fact in truth_df['fact'])
    else:
        # Misc content doesn't need verification
        return True

def structure_content(data, truth_source, output_path):
    if 'id' not in data.columns or 'text' not in data.columns or 'type' not in data.columns:
        logger.error(f"Input data missing 'id', 'text', or 'type' columns", extra={"user": USER_ID})
        raise ValueError("Input data must have 'id', 'text', and 'type' columns")

    content_blocks = []
    for _, row in data.iterrows():
        text = row['text']
        content_type = row['type']
        has_profanity = check_profanity(text)
        bias_status = check_bias(text)
        is_verified = verify_content(text, truth_source, content_type)

        # Skip content with profanity or bias
        if has_profanity or bias_status == "biased":
            logger.warning(f"Skipping block ID {row['id']} (profanity: {has_profanity}, bias: {bias_status})", extra={"user": USER_ID})
            continue

        if not is_verified:
            logger.warning(f"Skipping block ID {row['id']} (not verified against truth source)", extra={"user": USER_ID})
            continue

        block = {
            'id': row['id'],
            'text': text,
            'type': content_type,
            'profanity': False,  # Explicitly set to False since we filtered
            'bias': 'neutral',  # Explicitly set to neutral since we filtered
            'verified': True    # Explicitly set to True since we filtered
        }
        content_blocks.append(block)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump(content_blocks, f, indent=2)
    logger.info(f"Saved {len(content_blocks)} content blocks to {output_path}", extra={"user": USER_ID})
    return content_blocks

def main():
    logger.info(f"Starting Agent A: Knowledge Miner & Sanitizer", extra={"user": USER_ID})
    input_file = 'content/raw/sample.csv'
    truth_source = 'content/raw/truth-source.csv'
    output_path = 'content/structured/content_blocks.json'

    data = load_data(input_file)
    blocks = structure_content(data, truth_source, output_path)
    logger.info(f"Processed {len(blocks)} content blocks", extra={"user": USER_ID})
    print(f"Processed {len(blocks)} content blocks. Saved to {output_path}")

if __name__ == "__main__":
    os.makedirs('logs', exist_ok=True)
    main()