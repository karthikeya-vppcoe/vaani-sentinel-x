import json
import os
import logging
import glob
import re
import asyncio
import shutil
import sys
from typing import Dict, List
from groq import AsyncGroq
from gtts import gTTS
import uuid
import argparse

# Logging setup for Agent G (Adaptive AI Writer & Voice Generator)
USER_ID = 'agent_g_user'
logger = logging.getLogger('ai_writer_voicegen')
logger.setLevel(logging.INFO)

# Ensure logs directory exists relative to the script's location
script_dir = os.path.dirname(os.path.abspath(__file__))
logs_dir = os.path.join(script_dir, '..', 'logs')
os.makedirs(logs_dir, exist_ok=True)

file_handler = logging.FileHandler(os.path.join(logs_dir, 'ai_writer_voicegen.txt'), encoding='utf-8')
file_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - User: %(user)s - %(message)s')
file_handler.setFormatter(formatter)
file_handler.addFilter(lambda record: setattr(record, 'user', USER_ID) or True)
logger.handlers = [file_handler]

def clean_text_for_tts(text: str) -> str:
    """Remove emojis and invalid characters for TTS (Task 2: Agent G)."""
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"
        "\U0001F300-\U0001F5FF"
        "\U0001F680-\U0001F6FF"
        "\U0001F700-\U0001F77F"
        "\U0001F780-\U0001F7FF"
        "\U0001F800-\U0001F8FF"
        "\U0001F900-\U0001F9FF"
        "\U0001FA00-\U0001FA6F"
        "\U0001FA70-\U0001FAFF"
        "\U00002700-\U0001F1FF"
        "]+",
        flags=re.UNICODE
    )
    return emoji_pattern.sub(r'', text).strip()

def standardize_formatting(text: str, language: str) -> str:
    """Standardize formatting and punctuation across languages."""
    # Remove extra asterisks and colons in lists
    text = re.sub(r'\*+', '', text)
    text = re.sub(r':\s*(?=\w)', '- ', text)  # Replace colons in lists with hyphens
    
    # Fix capitalization in English (don't capitalize mid-sentence)
    if language == 'en':
        sentences = text.split('. ')
        sentences = [s[0].upper() + s[1:].lower() if len(s) > 1 else s.upper() for s in sentences]
        text = '. '.join(sentences)
        # Ensure proper sentence-ending punctuation
        lines = text.split('\n')
        standardized_lines = []
        for line in lines:
            line = line.strip()
            if line and not line.endswith(('.', '!', '?')):
                line += '.'
            # Capitalize specific terms
            line = line.replace('ai', 'AI').replace('internet things', 'Internet of Things')
            standardized_lines.append(line)
        text = '\n'.join(standardized_lines)
    
    # For Hindi and Sanskrit, use standardize_punctuation
    if language in ['hi', 'sa']:
        text = standardize_punctuation(text, language)
    
    return text

def standardize_punctuation(text: str, language: str) -> str:
    """Standardize punctuation for Hindi and Sanskrit content."""
    text = re.sub(r'\s+', ' ', text)
    lines = text.split('\n')
    standardized_lines = []
    for line in lines:
        line = line.strip()
        if line and not line.endswith(('।', '!', '?', '॥')):
            if language == 'hi':
                line += '।'
            elif language == 'sa':
                line += '॥'
        standardized_lines.append(line)
    text = '\n'.join(standardized_lines)
    if language == 'sa':
        text = text.replace(':', '')
    return text

def correct_grammar(text: str, language: str) -> str:
    """Correct common grammatical errors in English, Hindi, and Sanskrit."""
    if language == 'en':
        # Add missing articles
        text = re.sub(r'\b(sense|new chance|vast expanse|blue hue|clean slate|stepping stone|human touch|driving force|better world|era|infinite possibilities)\b', r'a \1', text, flags=re.IGNORECASE)
        text = re.sub(r'\b(joys) that life', r'the \1 that life', text, flags=re.IGNORECASE)
        # Fix prepositions
        text = re.sub(r'for better', 'for the better', text, flags=re.IGNORECASE)
        text = re.sub(r'opening doors a', 'opening doors to a', text, flags=re.IGNORECASE)
        # Fix verb agreement
        text = re.sub(r'you ready soar', 'are you ready to soar', text, flags=re.IGNORECASE)
    elif language == 'hi':
        # Fix common Hindi grammatical errors
        text = re.sub(r'हर औरत', 'हर रात', text)  # Typo correction
        text = re.sub(r'जलाये रखों', 'जलाए रखें', text)
        text = re.sub(r'आसमान तरह', 'आसमान की तरह', text)
        text = re.sub(r'लोगों लिए', 'लोगों के लिए', text)
        text = re.sub(r'कर सकते हो', 'कर सकते हैं', text)
        text = re.sub(r'हो चुका हैं', 'हो चुका है', text)
        text = re.sub(r'इसके अलावा में', 'इसके अलावा', text)
        text = re.sub(r'क्योंक्यू', 'क्यों', text)
        text = re.sub(r'स्त्रोत', 'स्रोत', text)
    elif language == 'sa':
        # Fix sandhi and case endings
        text = re.sub(r'íृत्तिः', 'वृत्तिः', text)  # Typo correction
        text = re.sub(r'नम्भवे', 'नमः भवे', text)
        text = re.sub(r'शुभकर्मा', 'शुभकर्मणा', text)
        text = re.sub(r'स्थिरा', 'स्थिरः', text)
        text = re.sub(r'अनन्तस्यानťशिवतत्त्वस्य', 'अनन्तस्य शिवतत्त्वस्य', text)
        text = re.sub(r'सद्गुरोरन्रहेण', 'सद्गुरोरनुग्रहेण', text)
    return text

def reduce_repetition(text: str) -> str:
    """Reduce repetitive phrases in the content."""
    # Split by sentences (for English and Hindi) or lines (for Sanskrit)
    if '।' in text or '॥' in text:
        lines = text.split('।') if '।' in text else text.split('॥')
    else:
        lines = text.split('. ')
    
    seen_phrases = set()
    unique_lines = []
    for line in lines:
        line = line.strip()
        if line and line not in seen_phrases:
            seen_phrases.add(line)
            unique_lines.append(line)
        elif line in seen_phrases:
            logger.warning(f"Removed repetitive line: {line}")
    
    # Rejoin with appropriate separator
    separator = '. ' if '.' in text else ('। ' if '।' in text else '॥ ')
    text = separator.join(unique_lines)
    
    # Reduce word-level repetition
    words = text.split()
    word_counts = {}
    for i, word in enumerate(words):
        word_counts[word] = word_counts.get(word, 0) + 1
        if word_counts[word] > 3:
            logger.warning(f"Reducing repetition of word/phrase: {word}")
            words[i] = ''
    text = ' '.join(word for word in words if word)
    
    return text

def clean_generated_content(content: str, language: str) -> str:
    """Clean the generated content to ensure it’s in the specified language, removing translations, hashtags, and commentary."""
    # Remove hashtags
    content = re.sub(r'#\w+\s*', '', content)
    
    # Remove instructional notes and commentary
    content = re.sub(r'\(\s*pause\s*\)', '', content, flags=re.IGNORECASE)
    content = re.sub(r'(Morning mantras|Evening reflections)\)\s*', '', content, flags=re.IGNORECASE)
    content = re.sub(r'This script designed be uplifting.*?(?=\n|$)', '', content, flags=re.IGNORECASE)
    content = re.sub(r'^(Professional and formal post|Rewritten version of the post)[^\n]*\n', '', content, flags=re.IGNORECASE)
    content = re.sub(r'Translation:.*?(?=\n|$)', '', content, flags=re.DOTALL)
    content = re.sub(r'Feel free to adjust.*?(?=\n|$)', '', content, flags=re.DOTALL)
    content = re.sub(r'Here(?: is|\'s) a.*?:?\n?', '', content, flags=re.DOTALL)
    content = re.sub(r'This post maintains.*?(?=\n|$)', '', content, flags=re.DOTALL)
    content = re.sub(r'This post aims.*?(?=\n|$)', '', content, flags=re.DOTALL)
    content = re.sub(r'Let me know if.*?(?=\n|$)', '', content, flags=re.DOTALL)
    content = re.sub(r'This is a.*?(?=\n|$)', '', content, flags=re.DOTALL)
    content = re.sub(r'voice script suitable.*?(?=\n|$)', '', content, flags=re.DOTALL)
    content = re.sub(r'This script aims.*?(?=\n|$)', '', content, flags=re.DOTALL)
    content = re.sub(r'Example:.*?(?=\n|$)', '', content, flags=re.DOTALL)
    content = re.sub(r'tweet (?:for|suitable for) LinkedIn:?\n?', '', content, flags=re.DOTALL)
    content = re.sub(r'\(you can add the specific name of the initiative\)', '', content)
    content = re.sub(r'\*\*.*?:?\*\*\n?', '', content)  # Remove headings like **Title:**
    content = re.sub(r'\[.*?\]', '', content)  # Remove bracketed notes like [Namaste, a gentle tone]
    content = re.sub(r'I hope this script meets.*?(?=\n|$)', '', content, flags=re.DOTALL)
    content = re.sub(r'End of (script|update)\n?', '', content, flags=re.DOTALL)
    content = re.sub(r'Sources:.*?(?=\n|$)', '', content, flags=re.DOTALL)
    content = re.sub(r'\* \[Insert.*?\]', '', content, flags=re.DOTALL)
    
    # For Hindi and Sanskrit, remove English text and retain Devanagari script
    if language in ['hi', 'sa']:
        content = re.sub(r'[a-zA-Z0-9_]+', '', content)
        content = re.sub(r'[\[\]\(\)\.\!\?]', '', content)
        lines = content.split('\n')
        devanagari_lines = []
        for line in lines:
            if re.search(r'[\u0900-\u097F]', line):
                devanagari_lines.append(line.strip())
            else:
                logger.warning(f"Removed English line from {language} content: {line}")
        content = '\n'.join(devanagari_lines)
    
    # Reduce repetition
    content = reduce_repetition(content)
    
    # Standardize formatting and punctuation
    content = standardize_formatting(content, language)
    
    # Correct grammar
    content = correct_grammar(content, language)
    
    # Remove extra newlines and whitespace
    content = re.sub(r'\n\s*\n+', '\n', content).strip()
    return content

def truncate_tweet(text: str, max_length: int = 280) -> str:
    """Truncate tweet to fit within max_length characters and ensure it ends properly."""
    if len(text) <= max_length:
        return text
    # Find the last complete sentence within the limit
    truncated = text[:max_length]
    last_period = truncated.rfind('.')
    if last_period != -1 and last_period > 0:
        return truncated[:last_period + 1]
    # If no period, truncate at the last space and add a period
    last_space = truncated.rfind(' ')
    if last_space != -1:
        return truncated[:last_space] + '.'
    return truncated + '.'

async def generate_content(text: str, content_type: str, tone: str, language: str, sentiment: str, client: AsyncGroq = None) -> Dict:
    """Generate content with specified tone and sentiment (Task 2: Agent G)."""
    if "initiative" in text.lower() and "learn about this initiative" in text.lower():
        text = text.replace("Learn about this initiative", "Learn about the 'Clean Oceans Initiative,' which aims to reduce plastic waste in our oceans to protect marine life and promote a cleaner environment.")

    tone_prompts = {
        'formal': 'Write in a professional and formal tone suitable for LinkedIn.',
        'casual': 'Write in a friendly and casual tone suitable for Instagram.',
        'devotional': 'Write in a neutral and devotional tone suitable for Sanatan voice assistants.'
    }
    sentiment_prompts = {
        'uplifting': 'Ensure the content has an uplifting and positive tone.',
        'neutral': 'Ensure the content has a neutral and factual tone.',
        'devotional': 'Ensure the content has a devotional and spiritual tone.'
    }
    tone_instruction = tone_prompts.get(tone, '')
    sentiment_instruction = sentiment_prompts.get(sentiment, '')

    language_instructions = {
        'en': 'Generate the content entirely in English.',
        'hi': 'Generate the content entirely in Hindi using Devanagari script. Do not include English translations, hashtags, or commentary.',
        'sa': 'Generate the content entirely in Sanskrit using Devanagari script. Ensure the content is meaningful, non-repetitive, and reflective of Sanatan philosophical or devotional themes. Do not include English translations, hashtags, or commentary.'
    }
    lang_instruction = language_instructions.get(language, 'Generate the content in the specified language.')
    
    # Ensure consistent scope for tech advancements across languages
    if "technology" in text.lower() or "प्रौद्योगिकी" in text:
        prompt = f"{tone_instruction} {sentiment_instruction} {lang_instruction} Create a {content_type} about recent developments in technology, including advancements in artificial intelligence, 5G networks, blockchain, and sustainable energy solutions."
    elif text == "इस कारण को जानें" and language == 'hi':
        prompt = f"{tone_instruction} {sentiment_instruction} {lang_instruction} Create a {content_type} about understanding the reasons behind the success of ancient civilizations, their contributions to humanity, and how we can learn from their history."
    else:
        prompt = f"{tone_instruction} {sentiment_instruction} {lang_instruction} Create a {content_type} based on: {text}"
    
    if not client:
        logger.info(f"No Groq API client, using fallback text for {content_type} (tone: {tone}, lang: {language})")
        return {'content': text, 'tone': tone, 'sentiment': sentiment, 'language': language}
    
    try:
        max_tokens = 270 if content_type == 'tweet' else 1000  # Reduced for tweets to avoid truncation
        response = await client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.3-70b-versatile",
            max_tokens=max_tokens
        )
        content = response.choices[0].message.content.strip()
        
        content = clean_generated_content(content, language)
        
        if language == 'sa':
            lines = content.split('\n')
            phrase_counts = {}
            for line in lines:
                line = line.strip()
                if line:
                    phrase_counts[line] = phrase_counts.get(line, 0) + 1
            if any(count > 2 for count in phrase_counts.values()) or len(content) < 20:
                logger.warning(f"Sanskrit content is repetitive or too short, generating fallback: {content}")
                if "ॐ नमः शिवाय" in text:
                    content = "ॐ नमः शिवाय। शिवः सर्वं विश्वस्य आधारः। तस्य कृपया जीवनं पावनं भवति। सर्वं शिवमयं विश्वं नमति।"
                elif "विद्या विनयं ददाति" in text:
                    content = "विद्या विनयं ददाति। विनयात् धर्मः जायते। धर्मात् सुखं सम्भवति। सुखेन जीवनं पूर्णं भवति।"
        
        if content_type == 'tweet':
            content = truncate_tweet(content)
        
        return {'content': content, 'tone': tone, 'sentiment': sentiment, 'language': language}
    except Exception as e:
        logger.error(f"Failed to generate {content_type} (tone: {tone}, sentiment: {sentiment}, lang: {language}): {str(e)}")
        return {'content': text, 'tone': tone, 'sentiment': sentiment, 'language': language}

async def generate_tts(result: Dict, output_path: str, language: str, voice: str = 'normal') -> bool:
    """Generate TTS audio using gTTS (Task 2: Agent G)."""
    try:
        lang_map = {'en': 'en', 'hi': 'hi', 'sa': 'hi'}  # Sanskrit uses Hindi as fallback for TTS
        tts_lang = lang_map.get(language, 'en')
        slow = voice == 'slow'
        
        text = clean_text_for_tts(result.get('voice_script', ''))
        if not text:
            logger.warning(f"Empty or invalid voice script for ID {result.get('id', 'unknown')}, skipping TTS")
            return False
        
        tts = gTTS(text=text, lang=tts_lang, slow=slow)
        await asyncio.to_thread(tts.save, output_path)
        logger.info(f"Generated TTS for ID {result.get('id', 'unknown')} at {output_path} (voice: {voice})")
        return True
    except Exception as e:
        logger.error(f"Failed to generate TTS for ID {result.get('id', 'unknown')}: {str(e)}")
        return False

async def process_content_blocks(blocks: List[Dict], output_dir: str, language: str, client: AsyncGroq = None) -> None:
    """Process content blocks for tweets, posts, and voice (Task 2: Agent G)."""
    for block in blocks:
        block_id = block.get('id', 'unknown')
        text = block.get('text', '')
        sentiment = block.get('sentiment', 'neutral')
        try:
            # Generate tweet
            tweet_data = await generate_content(text, 'tweet', 'formal', language, sentiment, client)
            tweet_content = tweet_data['content']
            tweet_path = os.path.join(output_dir, f"tweet_{block_id}_twitter_{uuid.uuid4().hex}.json")
            os.makedirs(os.path.dirname(tweet_path), exist_ok=True)
            with open(tweet_path, 'w', encoding='utf-8') as f:
                json.dump({'id': block_id, 'tweet': tweet_content, 'platform': 'twitter', 'content_type': 'tweet', 'tone': 'formal', 'sentiment': sentiment, 'version': 1}, f, ensure_ascii=False)
            logger.info(f"Generated twitter tweet for ID {block_id} at {tweet_path}")

            # Generate Instagram post
            post_data_ig = await generate_content(text, 'post', 'casual', language, sentiment, client)
            post_path_ig = os.path.join(output_dir, f"post_{block_id}_instagram_{uuid.uuid4().hex}.json")
            with open(post_path_ig, 'w', encoding='utf-8') as f:
                json.dump({'id': block_id, 'post': post_data_ig['content'], 'platform': 'instagram', 'content_type': 'post', 'tone': 'casual', 'sentiment': sentiment, 'version': 1}, f, ensure_ascii=False)
            logger.info(f"Generated instagram post for ID {block_id} at {post_path_ig}")

            # Generate LinkedIn post
            post_data_li = await generate_content(text, 'post', 'formal', language, sentiment, client)
            post_path_li = os.path.join(output_dir, f"post_{block_id}_linkedin_{uuid.uuid4().hex}.json")
            with open(post_path_li, 'w', encoding='utf-8') as f:
                json.dump({'id': block_id, 'post': post_data_li['content'], 'platform': 'linkedin', 'content_type': 'post', 'tone': 'formal', 'sentiment': sentiment, 'version': 1}, f, ensure_ascii=False)
            logger.info(f"Generated linkedin post for ID {block_id} at {post_path_li}")

            # Generate voice script
            voice_data = await generate_content(text, 'voice_script', 'devotional', language, sentiment, client)
            voice_path = os.path.join(output_dir, f"voice_{block_id}_sanatan_{uuid.uuid4().hex}.json")
            os.makedirs(os.path.dirname(voice_path), exist_ok=True)
            result = {'id': block_id, 'voice_script': voice_data['content'], 'platform': 'sanatan', 'content_type': 'voice_script', 'tone': 'devotional', 'sentiment': sentiment, 'version': 1}
            with open(voice_path, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False)
            logger.info(f"Generated sanatan voice script for ID {block_id} at {voice_path}")

            # Generate TTS for voice script
            tts_path = os.path.join(output_dir, f"voice_{block_id}_sanatan_{uuid.uuid4().hex}.mp3")
            voice_style = 'slow' if language == 'sa' else 'normal'
            if await generate_tts(result, tts_path, language, voice=voice_style):
                logger.info(f"Processed block {block_id} with TTS for sanatan ({language})")
            else:
                logger.info(f"Processed block {block_id} without TTS for sanatan ({language})")
        except Exception as e:
            logger.error(f"Failed to process block {block_id}: {str(e)}")
            continue

def load_blocks(input_dir: str, language: str) -> List[Dict]:
    """Load blocks from language-specific folders (Task 2: Agent G)."""
    blocks = []
    lang_dir = os.path.join(input_dir, language)
    if not os.path.exists(lang_dir):
        logger.warning(f"Input directory not found for language {language}: {lang_dir}")
        return blocks
    for block_file in glob.glob(os.path.join(lang_dir, 'block_*.json')):
        try:
            with open(block_file, 'r', encoding='utf-8') as f:
                block = json.load(f)
                blocks.append(block)
            logger.info(f"Loaded block from {block_file}")
        except Exception as e:
            logger.error(f"Failed to load {block_file}: {str(e)}")
    return blocks

def clear_output_directory(output_dir: str) -> None:
    """Clear the output directory before processing new content."""
    if os.path.exists(output_dir):
        try:
            shutil.rmtree(output_dir)
            logger.info(f"Cleared output directory: {output_dir}")
        except Exception as e:
            logger.error(f"Failed to clear output directory {output_dir}: {str(e)}")
            raise
    os.makedirs(output_dir, exist_ok=True)

async def run_ai_writer_voicegen_async(selected_language: str, sentiment: str) -> None:
    """Run Agent G: Adaptive AI Writer & Voice Generator (Task 2) with proper client handling."""
    logger.info(f"Starting Agent G: Adaptive AI Writer & Voice Generator for language: {selected_language}")
    client = None
    try:
        if os.getenv('GROQ_API_KEY'):
            client = AsyncGroq(api_key=os.getenv("GROQ_API_KEY"))
        else:
            logger.warning("GROQ_API_KEY not set, running in fallback mode without API calls")
        
        input_dir = os.path.join(script_dir, '..', 'content', 'multilingual_ready')
        output_base_dir = os.path.join(script_dir, '..', 'content', 'content_ready')
        
        # Clear the output directory to remove stale content
        clear_output_directory(output_base_dir)
        
        # Determine which languages to process
        languages_to_process = ['en', 'hi', 'sa'] if selected_language == 'all' else [selected_language]
        
        for lang in languages_to_process:
            blocks = load_blocks(input_dir, lang)
            if blocks:
                output_dir = os.path.join(output_base_dir, lang)
                await process_content_blocks(blocks, output_dir, lang, client)
            else:
                logger.warning(f"No blocks found for language {lang}")
    except Exception as e:
        logger.error(f"Script execution failed: {str(e)}")
        raise
    finally:
        if client:
            await client.close()
            logger.info("Groq API client closed successfully")
    
    logger.info("Completed AI writing and voice generation")

def run_ai_writer_voicegen() -> None:
    """Wrapper to run the async function with language and sentiment arguments."""
    parser = argparse.ArgumentParser(description="Run Agent G: AI Writer & Voice Generator")
    parser.add_argument('--sentiment', choices=['uplifting', 'neutral', 'devotional'], default='neutral', help="Sentiment to apply (uplifting, neutral, devotional)")
    parser.add_argument('language', choices=['en', 'hi', 'sa', 'all'], help="Language to process (en, hi, sa, all)")
    args = parser.parse_args()
    
    asyncio.run(run_ai_writer_voicegen_async(args.language, args.sentiment))

if __name__ == "__main__":
    run_ai_writer_voicegen()