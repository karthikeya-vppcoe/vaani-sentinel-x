import argparse
import json
import os
import logging
import re
from typing import Dict, List
from groq import AsyncGroq
import asyncio
from datetime import datetime, timezone
import glob

# Logging setup for Agent H (Sentiment Tuner)
USER_ID = 'agent_h_user'
logger = logging.getLogger('sentiment_tuner')
logger.setLevel(logging.INFO)
log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'logs')
os.makedirs(log_dir, exist_ok=True)
log_path = os.path.join(log_dir, 'sentiment_tuner.txt')
file_handler = logging.FileHandler(log_path, encoding='utf-8')
file_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - User: %(user)s - %(message)s')
file_handler.setFormatter(formatter)
file_handler.addFilter(lambda record: setattr(record, 'user', USER_ID) or True)
logger.handlers = [file_handler, logging.StreamHandler()]

def regex_tune_sentiment(text: str, sentiment: str, language: str) -> str:
    """Regex-based sentiment tuning for Hindi/Sanskrit."""
    if language not in ['hi', 'sa']:
        return text

    # Fix grammar for "इस कारण का समर्थन करें" across all sentiments
    if language == 'hi':
        text = re.sub(r'इस कारण का समर्थन करें', 'इस कारण को समर्थन करें', text)

    if sentiment == 'uplifting':
        positive_phrases = {'hi': 'सकारात्मक और प्रेरणादायक', 'sa': 'आनन्ददायकं प्रेरणात्मकं च'}
        return f"{text} ({positive_phrases.get(language, '')})"
    elif sentiment == 'devotional':
        devotional_phrases = {'hi': 'आध्यात्मिक उत्थान हेतु', 'sa': 'संनातन धर्मस्य संनादति'}
        return f"{text} ({devotional_phrases.get(language, '')})"
    elif sentiment == 'neutral':
        if language == 'hi':
            text = re.sub(r'रोमांचक', 'नया', text)
            text = re.sub(r'का समर्थन करें', 'को जानें', text)
            text = re.sub(r'समर्थन करें', 'को जानें', text)
            return text
        elif language == 'sa':
            return text
    return text

async def tune_sentiment(text: str, sentiment: str, language: str, client: AsyncGroq = None) -> str:
    """Adjust text sentiment using Groq API (English) or regex (Hindi/Sanskrit, fallback)."""
    if not text:
        logger.warning(f"Empty text provided for language {language}, sentiment {sentiment}")
        return text

    if language != 'en' or not client:
        logger.info(f"Using regex-based tuning for {language} (sentiment: {sentiment})")
        return regex_tune_sentiment(text, sentiment, language)
    
    sentiment_prompts = {
        'uplifting': 'Rewrite this text to have an uplifting and positive tone suitable for the Instagram platform, keeping it concise and natural.',
        'neutral': 'Rewrite this text to have a neutral and factual tone, avoiding emotional embellishments, suitable for Instagram.',
        'devotional': 'Rewrite this text to have a devotional and spiritual tone suitable for Instagram audiences.'
    }
    prompt = f"{sentiment_prompts.get(sentiment, 'neutral')} Text: {text}"
    
    try:
        response = await client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.3-70b-versatile",
            max_tokens=1000
        )
        tuned_text = response.choices[0].message.content.strip()
        # Clean up the response
        if tuned_text.startswith("Here is a rewritten version"):
            parts = tuned_text.split('\n\n')
            tuned_text = parts[1].strip('"') if len(parts) > 1 else tuned_text
        tuned_text = tuned_text.split('\n\n')[0].strip('"')
        if sentiment == 'neutral':
            tuned_text = re.sub(r'and consider getting involved\.?', '', tuned_text).strip()
            if not tuned_text.endswith('.'):
                tuned_text += '.'
        return tuned_text
    except Exception as e:
        logger.error(f"Groq API failed for text '{text[:50]}...' (sentiment: {sentiment}, lang: {language}): {str(e)}")
        return regex_tune_sentiment(text, sentiment, language)

async def process_file(input_file: str, sentiment: str, languages: List[str] = None) -> None:
    """Process a single personalized content file with sentiment tuning."""
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            entry = json.load(f)
        logger.info(f"Loaded personalized content from {input_file}")
    except FileNotFoundError:
        logger.error(f"Input file {input_file} not found.")
        return
    except json.JSONDecodeError:
        logger.error(f"Invalid JSON in {input_file}.")
        return

    language = entry.get('language')
    if languages and language not in languages:
        logger.debug(f"Skipping {input_file} (language {language} not in {languages})")
        return
    if language not in ['en', 'hi', 'sa']:
        logger.warning(f"Skipping unsupported language {language} in {input_file}")
        return

    entry_id = f"{entry.get('content_id', 'unknown')}_{entry.get('user_id', 'unknown')}_{entry.get('tone', 'unknown')}"
    text = entry.get('personalized_text', '')
    
    client = None
    if language == 'en' and os.getenv('GROQ_API_KEY'):
        client = AsyncGroq()
    
    try:
        tuned_text = await tune_sentiment(text, sentiment, language, client)
        updated_entry = entry.copy()
        updated_entry['sentiment_tuned_text'] = tuned_text
        updated_entry['sentiment'] = sentiment
        updated_entry['text_history'] = {
            'translated': entry.get('translated_text', ''),
            'personalized': entry.get('personalized_text', ''),
            'sentiment_tuned': tuned_text
        }
        updated_entry['timestamp'] = datetime.now(timezone.utc).isoformat()
        
        with open(input_file, 'w', encoding='utf-8') as f:
            json.dump(updated_entry, f, ensure_ascii=False, indent=2)
        logger.info(f"Tuned sentiment to {sentiment} for entry {entry_id} (language: {language}, file: {input_file})")
    except Exception as e:
        logger.error(f"Failed to process {input_file} (entry {entry_id}): {str(e)}")
        updated_entry = entry.copy()
        updated_entry['sentiment_tuned_text'] = text
        updated_entry['sentiment'] = sentiment
        updated_entry['text_history'] = {
            'translated': entry.get('translated_text', ''),
            'personalized': entry.get('personalized_text', ''),
            'sentiment_tuned': text
        }
        updated_entry['timestamp'] = datetime.now(timezone.utc).isoformat()
        
        with open(input_file, 'w', encoding='utf-8') as f:
            json.dump(updated_entry, f, ensure_ascii=False, indent=2)
        logger.info(f"Tuned (fallback) sentiment to {sentiment} for entry {entry_id} (language: {language}, file: {input_file})")

async def run_sentiment_tuner_async(content_id: str, platform: str, user_id: str, sentiment: str, languages: List[str] = None) -> None:
    """Run Agent H: Sentiment Tuner on personalized content files."""
    logger.info(f"Starting Agent H: Sentiment Tuner for content_id: {content_id}, platform: {platform}, user_id: {user_id}, sentiment: {sentiment}, languages: {languages or 'all'}")
    
    # Search all pipelines under content_ready
    base_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
    pattern = os.path.join(base_dir, 'content', 'content_ready', '*', '*', f'personalized_{content_id}_{platform}_{user_id}.json')
    input_files = glob.glob(pattern, recursive=True)
    
    if not input_files:
        logger.error(f"No personalized content files found for content_id {content_id}, platform {platform}, user_id {user_id}. Tried pattern: {pattern}")
        logger.info(f"Hint: Run personalization_agent.py for content_id {content_id} to generate files in the correct pipeline.")
        return
    
    logger.info(f"Found {len(input_files)} files: {input_files}")
    
    # Process each file
    tasks = [process_file(input_file, sentiment, languages) for input_file in input_files]
    await asyncio.gather(*tasks)
    
    logger.info(f"Sentiment tuning completed for {len(input_files)} files")

def run_sentiment_tuner() -> None:
    """Wrapper to run the async function with CLI arguments."""
    parser = argparse.ArgumentParser(description="Run Agent H: Sentiment Tuner")
    parser.add_argument('--content_id', required=True, help='Content ID to process')
    parser.add_argument('--platform', required=True, help='Platform (e.g., instagram)')
    parser.add_argument('--user_id', required=True, help='User ID for personalization')
    parser.add_argument('--sentiment', choices=['uplifting', 'neutral', 'devotional'], default='neutral',
                        help="Sentiment to apply (uplifting, neutral, devotional)")
    parser.add_argument('--languages', help="Comma-separated list of languages to process (e.g., en,hi,sa)")
    args = parser.parse_args()
    
    languages = args.languages.split(',') if args.languages else None
    asyncio.run(run_sentiment_tuner_async(args.content_id, args.platform, args.user_id, args.sentiment, languages))

if __name__ == "__main__":
    run_sentiment_tuner()