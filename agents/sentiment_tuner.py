import json
import os
import logging
import glob
import argparse
import re
from typing import Dict, List
from groq import AsyncGroq
import asyncio

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
logger.handlers = [file_handler]

def regex_tune_sentiment(text: str, sentiment: str, language: str) -> str:
    """Regex-based sentiment tuning for Hindi/Sanskrit (Task 2: Agent H)."""
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
            # Replace "रोमांचक" (exciting) with "नया" (new)
            text = re.sub(r'रोमांचक', 'नया', text)
            # Replace "का समर्थन करें" or "समर्थन करें" with "को जानें"
            text = re.sub(r'का समर्थन करें', 'को जानें', text)
            text = re.sub(r'समर्थन करें', 'को जानें', text)
            return text
        elif language == 'sa':
            return text
    return text

async def tune_sentiment(text: str, sentiment: str, language: str, client: AsyncGroq = None) -> str:
    """Adjust text sentiment using Groq API (English) or regex (Hindi/Sanskrit, fallback) (Task 2: Agent H)."""
    if language != 'en' or not client:
        logger.info(f"Using regex-based tuning for {language} (sentiment: {sentiment})")
        return regex_tune_sentiment(text, sentiment, language)
    
    sentiment_prompts = {
        'uplifting': 'Rewrite this text to have an uplifting and positive tone.',
        'neutral': 'Rewrite this text to have a neutral and factual tone.',
        'devotional': 'Rewrite this text to have a devotional and spiritual tone suitable for Sanatan audiences.'
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
            if "Or, if you'd like to add a bit more context:" in tuned_text:
                tuned_text = tuned_text.split('\n\n')[0].strip('"')
        tuned_text = tuned_text.split('\n\n')[0].strip('"')
        # For neutral sentiment, ensure no call to action and add a period
        if sentiment == 'neutral':
            tuned_text = re.sub(r'and consider getting involved\.?', '', tuned_text).strip()
            if not tuned_text.endswith('.'):
                tuned_text += '.'
        return tuned_text
    except Exception as e:
        logger.error(f"Groq API failed for text '{text[:50]}...' (sentiment: {sentiment}, lang: {language}): {str(e)}")
        return regex_tune_sentiment(text, sentiment, language)

def load_blocks(input_dir: str, language: str) -> List[Dict]:
    """Load blocks from language-specific folders (Task 2: Agent H)."""
    blocks = []
    lang_dir = os.path.join(input_dir, language)
    if not os.path.exists(lang_dir):
        logger.warning(f"Language directory does not exist: {lang_dir}")
        return blocks
    for block_file in glob.glob(os.path.join(lang_dir, 'block_*.json')):
        try:
            with open(block_file, 'r', encoding='utf-8') as f:
                block = json.load(f)
                block['file_path'] = block_file
                blocks.append(block)
            logger.info(f"Loaded block from {block_file}")
        except Exception as e:
            logger.error(f"Failed to load {block_file}: {str(e)}")
    return blocks

async def process_blocks(blocks: List[Dict], sentiment: str, language: str) -> None:
    """Process content blocks with sentiment tuning (Task 2: Agent H)."""
    client = None
    if language == 'en' and os.getenv('GROQ_API_KEY'):
        client = AsyncGroq()
    
    for block in blocks:
        block_id = block.get('id', 'unknown')
        text = block.get('text', '')
        
        try:
            tuned_text = await tune_sentiment(text, sentiment, language, client)
            block['text'] = tuned_text
            block['sentiment'] = sentiment  # Explicitly set the sentiment field
            logger.info(f"Set sentiment to {sentiment} for block ID {block_id} (language: {language})")
            with open(block['file_path'], 'w', encoding='utf-8') as f:
                json.dump(block, f, ensure_ascii=False, indent=2)
            logger.info(f"Tuned and saved block ID {block_id} with {sentiment} sentiment")
        except Exception as e:
            logger.error(f"Failed to process block ID {block_id}: {str(e)}")

async def run_sentiment_tuner_async(selected_language: str, sentiment: str) -> None:
    """Run Agent H: Sentiment Tuner (Task 2) for the specified language."""
    logger.info(f"Starting Agent H: Sentiment Tuner for language: {selected_language} with sentiment: {sentiment}")
    
    input_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'content', 'multilingual_ready')
    # Determine which languages to process
    languages_to_process = ['en', 'hi', 'sa'] if selected_language == 'all' else [selected_language]
    
    for lang in languages_to_process:
        blocks = load_blocks(input_dir, lang)
        if blocks:
            await process_blocks(blocks, sentiment, lang)
        else:
            logger.warning(f"No blocks found for language {lang}")
    
    logger.info("Sentiment tuning completed")

def run_sentiment_tuner() -> None:
    """Wrapper to run the async function with language and sentiment arguments."""
    parser = argparse.ArgumentParser(description="Run Agent H: Sentiment Tuner")
    parser.add_argument('language', choices=['en', 'hi', 'sa', 'all'], help="Language to process (en, hi, sa, all)")
    parser.add_argument('--sentiment', choices=['uplifting', 'neutral', 'devotional'], default='neutral',
                        help="Sentiment to apply (uplifting, neutral, devotional)")
    args = parser.parse_args()
    
    asyncio.run(run_sentiment_tuner_async(args.language, args.sentiment))

if __name__ == "__main__":
    run_sentiment_tuner()