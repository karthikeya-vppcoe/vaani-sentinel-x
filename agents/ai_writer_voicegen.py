import json
import os
import logging
import re
from datetime import datetime
from groq import Groq
from gtts import gTTS
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Custom filter to add user field to log records
class UserFilter(logging.Filter):
    def __init__(self, user_id):
        super().__init__()
        self.user_id = user_id

    def filter(self, record):
        record.user = self.user_id
        return True

# Configure logging
USER_ID = 'agent_b_user'
logger = logging.getLogger('ai_writer_voicegen')
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

# Controversial terms regex
CONTROVERSIAL_TERMS = re.compile(
    r'\b(religion|religious|politics|political|bias|offensive|racist|sexist|controversial)\b',
    re.IGNORECASE
)

# Initialize Groq client
groq_api_key = os.getenv('GROQ_API_KEY')
if not groq_api_key:
    logger.error("GROQ_API_KEY not found")
    raise ValueError("GROQ_API_KEY environment variable is required")
client = Groq(api_key=groq_api_key)

def load_content_blocks(file_path):
    """Load structured content blocks from JSON."""
    logger.info(f"Loading content blocks from {file_path}")
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error(f"File {file_path} not found")
        raise
    except json.JSONDecodeError:
        logger.error(f"Invalid JSON format in {file_path}")
        raise

def generate_tweet(text, max_length=280):
    """Generate a tweet from the input text using Groq Llama 3 70B."""
    prompt = f"Convert the following text into a tweet (max {max_length} characters): {text}"
    try:
        response = client.chat.completions.create(
            model='llama3-70b-8192',
            messages=[
                {'role': 'system', 'content': 'You are a concise content creator.'},
                {'role': 'user', 'content': prompt}
            ],
            max_tokens=60,
            temperature=0.7
        )
        tweet = response.choices[0].message.content.strip()
        if len(tweet) > max_length:
            tweet = tweet[:max_length-3] + '...'
        return tweet
    except Exception as e:
        logger.error(f"Failed to generate tweet: {str(e)}")
        raise

def generate_post(text):
    """Generate a 1-paragraph Instagram/LinkedIn post from the input text."""
    prompt = f"Convert the following text into a 1-paragraph post for Instagram or LinkedIn: {text}"
    try:
        response = client.chat.completions.create(
            model='llama3-70b-8192',
            messages=[
                {'role': 'system', 'content': 'You are a professional content creator.'},
                {'role': 'user', 'content': prompt}
            ],
            max_tokens=150,
            temperature=0.7
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"Failed to generate post: {str(e)}")
        raise

def generate_voice_script(text):
    """Generate a 20-30 second voice script from the input text."""
    prompt = f"Convert the following text into a 20-30 second voice script for use in an AI assistant: {text}"
    try:
        response = client.chat.completions.create(
            model='llama3-70b-8192',
            messages=[
                {'role': 'system', 'content': 'You are an engaging AI assistant.'},
                {'role': 'user', 'content': prompt}
            ],
            max_tokens=100,
            temperature=0.7
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"Failed to generate voice script: {str(e)}")
        raise

def generate_tts(text, output_path):
    """Generate a TTS audio file from the text."""
    logger.info(f"Generating TTS file at {output_path}")
    try:
        tts = gTTS(text=text, lang='en')
        tts.save(output_path)
    except Exception as e:
        logger.error(f"Failed to generate TTS: {str(e)}")
        raise

def save_content(content, output_path, content_type):
    """Save content to a JSON file."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump({content_type: content}, f, indent=2)
    logger.info(f"Saved {content_type} to {output_path}")

def process_content_blocks(blocks, output_dir):
    """Process each content block and generate outputs."""
    for block in blocks:
        if block['profanity'] or not block['verified'] or block['bias'] == 'biased' or CONTROVERSIAL_TERMS.search(block['text']):
            logger.info(f"Skipping block ID {block['id']} (profanity: {block['profanity']}, verified: {block['verified']}, bias: {block['bias']}, controversial: {bool(CONTROVERSIAL_TERMS.search(block['text']))})")
            continue
        
        text = block['text']
        block_id = block['id']
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Generate and save tweet
        tweet = generate_tweet(text)
        tweet_path = f"{output_dir}/tweet_{block_id}_{timestamp}.json"
        save_content(tweet, tweet_path, 'tweet')
        
        # Generate and save post
        post = generate_post(text)
        post_path = f"{output_dir}/post_{block_id}_{timestamp}.json"
        save_content(post, post_path, 'post')
        
        # Generate and save voice script
        voice_script = generate_voice_script(text)
        voice_path = f"{output_dir}/voice_{block_id}_{timestamp}.json"
        save_content(voice_script, voice_path, 'voice_script')
        
        # Generate TTS for voice script
        tts_path = f"{output_dir}/voice_{block_id}_{timestamp}.mp3"
        generate_tts(voice_script, tts_path)

def main():
    """Main function to run Agent B."""
    logger.info("Starting Agent B: AI Writer & Voice Synth Generator")
    input_file = 'content/structured/content_blocks.json'
    output_dir = 'content/content_ready'
    
    blocks = load_content_blocks(input_file)
    process_content_blocks(blocks, output_dir)
    logger.info(f"Completed processing at {datetime.now()}")
    print(f"Processed {len(blocks)} content blocks. Outputs saved to {output_dir}")

if __name__ == "__main__":
    os.makedirs('content/content_ready', exist_ok=True)
    main()