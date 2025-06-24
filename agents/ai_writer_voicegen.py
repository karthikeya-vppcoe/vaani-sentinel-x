import json
import os
import logging
import glob
import re
import asyncio
import uuid
import argparse
from typing import Dict, List
from groq import AsyncGroq
from datetime import datetime, timezone
from tenacity import retry, stop_after_attempt, wait_fixed
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Logging setup for Agent G (Adaptive AI Writer & Voice Generator)
USER_ID = 'agent_g_user'
logger = logging.getLogger('ai_writer_voicegen')
logger.setLevel(logging.INFO)

script_dir = os.path.dirname(os.path.abspath(__file__))
logs_dir = os.path.join(script_dir, '..', 'logs')
os.makedirs(logs_dir, exist_ok=True)

file_handler = logging.FileHandler(os.path.join(logs_dir, 'ai_writer_voicegen.txt'), encoding='utf-8')
file_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - User: %(user)s - %(message)s')
file_handler.setFormatter(formatter)
file_handler.addFilter(lambda record: setattr(record, 'user', USER_ID) or True)
logger.handlers = [file_handler, logging.StreamHandler()]

# Supported languages and platforms
SUPPORTED_LANGUAGES = ['en', 'hi', 'sa']
SUPPORTED_PLATFORMS = ['instagram', 'twitter', 'linkedin', 'sanatan']

def clean_text_for_tts(text: str) -> str:
    """Remove emojis and invalid characters for TTS."""
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
    text = re.sub(r'\s+', ' ', text)
    lines = text.split('\n')
    standardized_lines = []
    for line in lines:
        line = line.strip()
        if line:
            if language == 'en' and not line.endswith(('.', '!', '?')):
                line += '.'
            elif language == 'hi' and not line.endswith('।'):
                line += '।'
            elif language == 'sa' and not line.endswith('॥'):
                line += '॥'
            standardized_lines.append(line)
    text = '\n'.join(standardized_lines)
    if language == 'sa':
        text = text.replace(':', '')
    if language == 'en':
        text = text.replace('ai', 'AI').replace('internet things', 'Internet of Things')
    return text

def correct_grammar(text: str, language: str) -> str:
    """Correct common grammatical errors."""
    if language == 'en':
        text = re.sub(r'\b(sense|new chance|vast expanse|blue hue|clean slate|stepping stone|human touch|driving force|better world|era|infinite possibilities)\b', r'a \1', text, flags=re.IGNORECASE)
        text = re.sub(r'for better', 'for the better', text, flags=re.IGNORECASE)
        text = re.sub(r'opening doors a', 'opening doors to a', text, flags=re.IGNORECASE)
        text = re.sub(r'you ready soar', 'are you ready to soar', text, flags=re.IGNORECASE)
    elif language == 'hi':
        text = re.sub(r'हर औरत', 'हर रात', text)
        text = re.sub(r'जलाये रखों', 'जलाए रखें', text)
        text = re.sub(r'आसमान तरह', 'आसमान की तरह', text)
        text = re.sub(r'लोगों लिए', 'लोगों के लिए', text)
        text = re.sub(r'कर सकते हो', 'कर सकते हैं', text)
        text = re.sub(r'हो चुका हैं', 'हो चुका है', text)
        text = re.sub(r'इसके अलावा में', 'इसके अलावा', text)
        text = re.sub(r'क्योंक्यू', 'क्यों', text)
        text = re.sub(r'स्त्रोत', 'स्रोत', text)
    elif language == 'sa':
        text = re.sub(r'íृत्तिः', 'वृत्तिः', text)
        text = re.sub(r'नम्भवे', 'नमः भवे', text)
        text = re.sub(r'शुभकर्मा', 'शुभकर्मणा', text)
        text = re.sub(r'स्थिरा', 'स्थिरः', text)
        text = re.sub(r'अनन्तस्यानťशिवतत्त्वस्य', 'अनन्तस्य शिवतत्त्वस्य', text)
        text = re.sub(r'सद्गुरोरन्रहेण', 'सद्गुरोरनुग्रहेण', text)
    return text

def reduce_repetition(text: str) -> str:
    """Reduce repetitive phrases."""
    separator = '।' if '।' in text else ('॥' if '॥' in text else '.')
    lines = text.split(separator)
    seen_phrases = set()
    unique_lines = []
    for line in lines:
        line = line.strip()
        if line and line not in seen_phrases:
            seen_phrases.add(line)
            unique_lines.append(line)
        elif line:
            logger.warning(f"Removed repetitive line: {line}")
    return f'{separator} '.join(unique_lines).strip()

def clean_generated_content(content: str, language: str) -> str:
    """Clean content, removing hashtags, commentary, and non-target language text."""
    content = re.sub(r'#\w+\s*', '', content)
    content = re.sub(r'\(\s*[^\)]*\s*\)', '', content)
    content = re.sub(r'(Morning mantras|Evening reflections|Translation|This script|Rewritten version|Feel free|Here is|This post|Let me know|Example|tweet for|voice script|suitable for|I hope|End of|Sources|\[Insert)[^\n]*?(?=\n|$)', '', content, flags=re.DOTALL | re.IGNORECASE)
    content = re.sub(r'\*\*.*?:?\*\*\n?', '', content)
    content = re.sub(r'\[.*?\]', '', content)
    if language in ['hi', 'sa']:
        content = re.sub(r'[a-zA-Z0-9_]+', '', content)
        content = re.sub(r'[\[\]\(\)\.\!\?]', '', content)
        lines = content.split('\n')
        devanagari_lines = [line.strip() for line in lines if re.search(r'[\u0900-\u097F]', line)]
        content = '\n'.join(devanagari_lines)
    content = reduce_repetition(content)
    content = standardize_formatting(content, language)
    content = correct_grammar(content, language)
    content = re.sub(r'\n\s*\n+', '\n', content).strip()
    if language == 'sa':
        content = re.sub(r'(शान्तिः\s*){2,}', 'शान्तिः ', content)
        content = re.sub(r'(\b\w+\b)\s*\1+', r'\1', content)
    return content

def estimate_word_count(text: str, language: str) -> int:
    """Estimate word count for content length validation."""
    if language in ['hi', 'sa']:
        return len(re.findall(r'[\u0900-\u097F]+', text))
    return len(text.split())

def truncate_to_word_limit(text: str, language: str, max_words: int) -> str:
    """Truncate text to max word count, preserving sentence integrity."""
    separator = '।' if language in ['hi', 'sa'] else '.'
    sentences = text.split(separator)
    current_count = 0
    truncated_sentences = []
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
        words = re.findall(r'[\u0900-\u097F]+', sentence) if language in ['hi', 'sa'] else sentence.split()
        if current_count + len(words) <= max_words:
            truncated_sentences.append(sentence)
            current_count += len(words)
        else:
            break
    truncated = f'{separator} '.join(truncated_sentences).strip()
    return standardize_formatting(truncated + (separator if truncated else ''), language)

def pad_to_word_limit(text: str, language: str, min_words: int, content_type: str, platform: str) -> str:
    """Pad text to minimum word count with context-aware content."""
    current_count = estimate_word_count(text, language)
    if current_count >= min_words:
        return text
    padding = {
        'en': {
            'post': {
                'instagram': ' Embrace today with positivity and joy!',
                'twitter': ' Seize the day with enthusiasm!',
                'linkedin': ' Start today with purpose and positivity.'
            },
            'voice_script': ' May this day bring peace and purpose to your heart.'
        },
        'hi': {
            'post': {
                'instagram': ' आज के दिन को सकारात्मकता और खुशी के साथ अपनाएं।',
                'twitter': ' आज उत्साह के साथ दिन शुरू करें।',
                'linkedin': ' आज उद्देश्य और सकारात्मकता के साथ शुरू करें।'
            },
            'voice_script': ' यह दिन आपके हृदय में शांति और उद्देश्य लाए।'
        },
        'sa': {
            'post': {
                'instagram': ' सर्वं सौम्यं भवतु। शान्तिः॥',
                'twitter': ' सर्वं शुभं भवतु।',
                'linkedin': ' सर्वं धर्मेन संनादति।'
            },
            'voice_script': ' सर्वं सौम्यं भवतु। शान्तिः॥'
        }
    }
    while current_count < min_words:
        pad_text = padding.get(language, {}).get(content_type, {}).get(platform, padding.get(language, {}).get(content_type, ''))
        text = f"{text} {pad_text}".strip()
        current_count = estimate_word_count(text, language)
    return standardize_formatting(text, language)

def get_sanskrit_fallback(text: str, content_type: str, platform: str) -> str:
    """Generate context-aware Sanskrit fallback for short/repetitive content."""
    fallbacks = {
        'sun': {
            'post': {
                'instagram': "सूर्यः पूर्वदिशि उदयति। किरणैः विश्वं संनादति। नवं दिनं समृद्धं भवति। आनन्देन प्रभातं प्रेरति। जीवनं धर्मेन संनादति। सर्वं शुभं भवतु। शान्तिः॥",
                'twitter': "सूर्यः पूर्वदिशि उदयति। किरणैः विश्वं संनादति। नवं दिनं शुभं भवतु। आनन्देन प्रभातं प्रेरति। शान्तिः॥",
                'linkedin': "सूर्यः पूर्वदिशि उदयति। किरणैः विश्वं संनादति। नवं दिनं समृद्धं भवति। धर्मेन जीवनं प्रेरति। सर्वं शुभं भवतु। शान्तिः॥"
            },
            'voice_script': "सूर्यः पूर्वदिशि उदयति। तस्य किरणैः विश्वं संनादति। नवं दिनं समृद्धं भवति। आनन्देन जीवनं प्रेरति। धर्मः सत्यं च मार्गः। सर्वं सौम्यं भवतु। शान्तिः॥ प्रभातस्य शान्त्या सर्वं विश्वं संनादति। जीवनं सत्येन संनादति।"
        },
        'shiva': {
            'post': {
                'instagram': "ॐ नमः शिवाय। शिवः विश्वस्य आधारः। कृपया जीवनं पावनं भवति। शान्तिः सर्वत्र प्रसारति। धर्मेन संनादति। सर्वं शुभं भवतु। शान्तिः॥",
                'twitter': "ॐ नमः शिवाय। शिवः विश्वस्य आधारः। कृपया जीवनं पावनं भवति। सर्वं शुभं भवतु। शान्तिः॥",
                'linkedin': "ॐ नमः शिवाय। शिवः विश्वस्य आधारः। कृपया जीवनं पावनं भवति। धर्मेन शान्तिः प्रसारति। सर्वं शुभं भवतु। शान्तिः॥"
            },
            'voice_script': "ॐ नमः शिवाय। शिवः सर्वं विश्वस्य आधारः। तस्य कृपया जीवनं पावनं भवति। ध्यानं शान्तिं ददाति। धर्मः सत्यं च मार्गः। सर्वं शुभं भवतु। शान्तिः॥ ध्यानेन जीवनं समृद्धं भवति। सर्वं विश्वं शान्त्या संनादति।"
        },
        'default': {
            'post': {
                'instagram': "विद्या विनयं ददाति। विनयात् धर्मः जायते। धर्मात् सुखं सम्भवति। प्रभातस्य शान्तिः विश्वं प्रेरति। सत्यं जीवनस्य आधारः। सर्वं सौम्यं भवतु। शान्तिः॥",
                'twitter': "विद्या विनयं ददाति। विनयात् धर्मः जायते। सुखं सम्भवति। प्रभातस्य शान्तिः प्रेरति। सर्वं शुभं भवतु। शान्तिः॥",
                'linkedin': "विद्या विनयं ददाति। विनयात् धर्मः जायते। धर्मात् सुखं सम्भवति। जीवनं धर्मेन संनादति। सर्वं सौम्यं भवतु। शान्तिः॥"
            },
            'voice_script': "विद्या विनयं ददाति। विनयात् धर्मः जायते। धर्मात् सुखं सम्भवति। प्रभातस्य शान्तिः सर्वं प्रेरति। सत्यं जीवनस्य आधारः। सर्वं सौम्यं भवतु। शान्तिः॥ जीवनं धर्मेन संनादति। विश्वं शान्त्या समृद्धं भवति।"
        }
    }
    key = 'sun' if 'सूर्य' in text or 'sun' in text.lower() else 'shiva' if 'शिव' in text or 'shiva' in text.lower() else 'default'
    return fallbacks[key][content_type].get(platform, fallbacks[key][content_type]) if content_type == 'post' else fallbacks[key][content_type]

@retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
async def generate_content(text: str, content_type: str, tone: str, language: str, sentiment: str, platform: str, client: AsyncGroq = None) -> Dict:
    """Generate content with specified tone, sentiment, and platform using Groq."""
    tone_prompts = {
        'casual': 'Write in a friendly and casual tone suitable for social media.',
        'professional': 'Write in a professional and polished tone suitable for LinkedIn.',
        'devotional': 'Write in a neutral and devotional tone suitable for Sanatan voice assistants, keeping it 20–30 seconds long.'
    }
    sentiment_prompts = {
        'uplifting': 'Ensure the content has an uplifting and positive tone.',
        'neutral': 'Ensure the content has a neutral and factual tone.',
        'devotional': 'Ensure the content has a devotional and spiritual tone.'
    }
    language_instructions = {
        'en': 'Generate the content entirely in English.',
        'hi': 'Generate the content entirely in Hindi using Devanagari script. Do not include English translations, hashtags, or commentary.',
        'sa': 'Generate the content entirely in Sanskrit using Devanagari script. Ensure the content is meaningful, non-repetitive, and reflective of Sanatan philosophical or devotional themes. Do not include English translations, hashtags, or commentary.'
    }
    word_limits = {
        'post': {
            'instagram': (30, 50),
            'twitter': (20, 30),
            'linkedin': (30, 50)
        },
        'voice_script': {
            'sanatan': (50, 100) if language == 'en' else (30, 60)
        }
    }
    min_words, max_words = word_limits[content_type][platform]
    prompt = f"{tone_prompts.get(tone, '')} {sentiment_prompts.get(sentiment, '')} {language_instructions.get(language, '')} Create a {content_type} for {platform} based on: {text}. Ensure the content is between {min_words} and {max_words} words."
    
    # Log input parameters for debugging
    logger.debug(f"Generating content: content_type={content_type}, tone={tone}, lang={language}, platform={platform}, prompt={prompt[:100]}...")
    
    if not client:
        logger.info(f"No Groq client, using fallback text for {content_type} (tone: {tone}, lang: {language}, platform: {platform})")
        content = text if content_type == 'post' else get_sanskrit_fallback(text, content_type, platform) if language == 'sa' else text
        content = truncate_to_word_limit(content, language, max_words)
        content = pad_to_word_limit(content, language, min_words, content_type, platform)
        return {'content': content, 'tone': tone, 'sentiment': sentiment, 'language': language}
    
    try:
        max_tokens = 300 if content_type == 'post' else 500
        response = await client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.3-70b-versatile",
            max_tokens=max_tokens
        )
        content = response.choices[0].message.content.strip()
        content = clean_generated_content(content, language)
        content = truncate_to_word_limit(content, language, max_words)
        content = pad_to_word_limit(content, language, min_words, content_type, platform)
        word_count = estimate_word_count(content, language)
        if language == 'sa' and (word_count < min_words or re.search(r'(\b\w+\b).*?\1', content)):
            logger.warning(f"Sanskrit content is too short ({word_count} words) or repetitive: {content}")
            content = get_sanskrit_fallback(text, content_type, platform)
            content = truncate_to_word_limit(content, language, max_words)
            content = pad_to_word_limit(content, language, min_words, content_type, platform)
            word_count = estimate_word_count(content, language)
        if word_count < min_words or word_count > max_words:
            logger.warning(f"{content_type} length {word_count} words outside target {min_words}–{max_words} for {language} on {platform}: {content}")
        result = {'content': content, 'tone': tone, 'sentiment': sentiment, 'language': language}
        logger.debug(f"Generated content: {result}")
        # Add delay to avoid rate limits
        await asyncio.sleep(3)
        return result
    except Exception as e:
        logger.error(f"Failed to generate {content_type} (tone: {tone}, sentiment: {sentiment}, lang: {language}, platform: {platform}): {str(e)}")
        content = text if content_type == 'post' else get_sanskrit_fallback(text, content_type, platform) if language == 'sa' else text
        content = truncate_to_word_limit(content, language, max_words)
        content = pad_to_word_limit(content, language, min_words, content_type, platform)
        result = {'content': content, 'tone': tone, 'sentiment': sentiment, 'language': language}
        logger.debug(f"Fallback content: {result}")
        # Add delay even in fallback to avoid rapid retries
        await asyncio.sleep(3)
        return result

# Replace the process_content_blocks function in ai_writer_voicegen.py with this version
async def process_content_blocks(blocks: List[Dict], output_dir: str, language: str, content_id: str, platforms: List[str], client: AsyncGroq = None) -> List[Dict]:
    """Process content blocks for multiple platforms."""
    tts_simulations = []  # Keep for compatibility but won't save
    for block in blocks:
        block_id = block.get('content_id', 'unknown')
        text = block.get('sentiment_tuned_text', block.get('personalized_text', ''))
        sentiment = block.get('sentiment', 'uplifting')
        voice_tag = block.get('voice_tag', f"{language}_female_casual_1")
        
        if not text:
            logger.warning(f"Missing sentiment_tuned_text or personalized_text for ID {block_id}, skipping")
            continue
        if not voice_tag:
            logger.warning(f"Missing voice_tag for ID {block_id}, using default: {voice_tag}")
        
        for platform in platforms:
            try:
                if platform in ['instagram', 'twitter', 'linkedin']:
                    tone = 'professional' if platform == 'linkedin' else 'casual'
                    post_data = await generate_content(text, 'post', tone, language, sentiment, platform, client)
                    if not isinstance(post_data, dict):
                        logger.error(f"Invalid post_data type for {platform}: {type(post_data)}, expected dict")
                        continue
                    post_path = os.path.join(output_dir, f"post_{block_id}_{platform}_{uuid.uuid4().hex}.json")
                    os.makedirs(os.path.dirname(post_path), exist_ok=True)
                    if not os.access(os.path.dirname(post_path), os.W_OK):
                        raise PermissionError(f"No write permission for {os.path.dirname(post_path)}")
                    post_entry = {
                        'content_id': block_id,
                        'post': post_data['content'],
                        'platform': platform,
                        'content_type': 'post',
                        'tone': tone,
                        'sentiment': sentiment,
                        'language': language,
                        'voice_tag': voice_tag,
                        'version': 1,
                        'timestamp': datetime.now(timezone.utc).isoformat()
                    }
                    with open(post_path, 'w', encoding='utf-8') as f:
                        json.dump(post_entry, f, ensure_ascii=False, indent=2)
                    logger.info(f"Generated {platform} post for ID {block_id} at {post_path}")
                
                elif platform == 'sanatan':
                    voice_data = await generate_content(text, 'voice_script', 'devotional', language, sentiment, platform, client)
                    if not isinstance(voice_data, dict):
                        logger.error(f"Invalid voice_data type for {platform}: {type(voice_data)}, expected dict")
                        content = voice_data if isinstance(voice_data, str) else text
                    else:
                        content = voice_data['content']
                    voice_path = os.path.join(output_dir, f"voice_{block_id}_sanatan_{uuid.uuid4().hex}.json")
                    os.makedirs(os.path.dirname(voice_path), exist_ok=True)
                    if not os.access(os.path.dirname(voice_path), os.W_OK):
                        raise PermissionError(f"No write permission for {os.path.dirname(voice_path)}")
                    voice_entry = {
                        'content_id': block_id,
                        'voice_script': content,
                        'platform': 'sanatan',
                        'content_type': 'voice_script',
                        'tone': 'devotional',
                        'sentiment': sentiment,
                        'language': language,
                        'voice_tag': voice_tag,
                        'version': 1,
                        'timestamp': datetime.now(timezone.utc).isoformat()
                    }
                    with open(voice_path, 'w', encoding='utf-8') as f:
                        json.dump(voice_entry, f, ensure_ascii=False, indent=2)
                    logger.info(f"Generated Sanatan voice script for ID {block_id} at {voice_path}")

                    # Simulate TTS (log only, don't save)
                    tts_path = os.path.abspath(os.path.join(output_dir, f"voice_{block_id}_sanatan_{uuid.uuid4().hex}.mp3"))
                    tts_simulation = {
                        'content_id': block_id,
                        'language': language,
                        'tone': 'devotional',
                        'voice_tag': voice_tag,
                        'dummy_audio_path': tts_path,
                        'voice_script': content,
                        'timestamp': datetime.now(timezone.utc).isoformat()
                    }
                    tts_simulations.append(tts_simulation)
                    logger.info(f"Simulated TTS for ID {block_id} at {tts_path} (voice: {voice_tag})")
            
            except Exception as e:
                logger.error(f"Failed to process block {block_id} for {platform} (text: {text[:50]}...): {str(e)}")
                continue
    
    # Do not save tts_simulations to avoid redundancy
    return tts_simulations

def validate_block(block: Dict, language: str) -> bool:
    """Validate block schema."""
    required_fields = ['content_id', 'sentiment_tuned_text', 'voice_tag', 'sentiment']
    for field in required_fields:
        if field not in block:
            logger.warning(f"Missing field '{field}' in block for language {language}")
            return False
    return True

def load_blocks(input_dir: str, language: str, content_id: str) -> List[Dict]:
    """Load personalized content from content_ready."""
    blocks = []
    pattern = os.path.join(input_dir, '*', language, f'personalized_{content_id}_*.json')
    for block_file in glob.glob(pattern, recursive=True):
        try:
            with open(block_file, 'r', encoding='utf-8') as f:
                block = json.load(f)
                if validate_block(block, language):
                    blocks.append(block)
                else:
                    logger.warning(f"Invalid block schema in {block_file}, skipping")
            logger.info(f"Loaded block from {block_file}")
        except Exception as e:
            logger.error(f"Failed to load {block_file}: {str(e)}")
    return blocks

def clear_old_data(output_base_dir: str, language: str, content_id: str, platforms: List[str]) -> None:
    """Remove old output files for the given content_id, language, and platforms."""
    output_dir = os.path.join(output_base_dir, language)
    if not os.path.exists(output_dir):
        return
    patterns = []
    for platform in platforms:
        if platform in ['instagram', 'twitter', 'linkedin']:
            patterns.append(f"post_{content_id}_{platform}_*.json")
        elif platform == 'sanatan':
            patterns.extend([f"voice_{content_id}_*.json", f"tts_simulation_output_{content_id}.json"])
    for pattern in patterns:
        for file in glob.glob(os.path.join(output_dir, pattern)):
            try:
                os.remove(file)
                logger.info(f"Removed old file: {file}")
            except Exception as e:
                logger.error(f"Failed to remove old file {file}: {str(e)}")

def validate_platforms(platforms: List[str]) -> List[str]:
    """Validate and return supported platforms."""
    valid_platforms = [platform for platform in platforms if platform in SUPPORTED_PLATFORMS]
    invalid_platforms = set(platforms) - set(valid_platforms)
    if invalid_platforms:
        logger.warning(f"Invalid platforms ignored: {', '.join(invalid_platforms)}. Supported platforms: {', '.join(SUPPORTED_PLATFORMS)}")
    return valid_platforms

def validate_languages(languages: List[str]) -> List[str]:
    """Validate and return supported languages."""
    valid_languages = [lang for lang in languages if lang in SUPPORTED_LANGUAGES]
    invalid_languages = set(languages) - set(valid_languages)
    if invalid_languages:
        logger.warning(f"Unsupported languages ignored: {', '.join(invalid_languages)}. Supported languages: {', '.join(SUPPORTED_LANGUAGES)}")
    return valid_languages

async def process_language(lang: str, input_base_dir: str, output_base_dir: str, content_id: str, platforms: List[str], client: AsyncGroq = None) -> None:
    """Process a single language for multiple platforms."""
    clear_old_data(output_base_dir, lang, content_id, platforms)
    blocks = load_blocks(input_base_dir, lang, content_id)
    if blocks:
        output_dir = os.path.join(output_base_dir, lang)
        os.makedirs(output_dir, exist_ok=True)
        await process_content_blocks(blocks, output_dir, lang, content_id, platforms, client)
    else:
        logger.warning(f"No blocks found for language {lang} and content_id {content_id}")

async def run_ai_writer_voicegen_async(content_id: str, platforms: List[str], user_id: str, sentiment: str, languages: List[str]) -> None:
    """Run Agent G: Adaptive AI Writer & Voice Generator for multiple platforms."""
    valid_platforms = validate_platforms(platforms)
    valid_languages = validate_languages(languages)
    
    if not valid_platforms:
        logger.error("No valid platforms provided. Exiting.")
        return
    if not valid_languages:
        logger.error("No valid languages provided. Exiting.")
        return
    
    logger.info(f"Starting Agent G for content_id: {content_id}, platforms: {valid_platforms}, user_id: {user_id}, sentiment: {sentiment}, languages: {valid_languages}")
    client = None
    try:
        if os.getenv('GROQ_API_KEY'):
            client = AsyncGroq(api_key=os.getenv("GROQ_API_KEY"))
        else:
            logger.warning("GROQ_API_KEY not set, running in fallback mode")
        
        input_base_dir = os.path.join(script_dir, '..', 'content', 'content_ready')
        output_base_dir = os.path.join(script_dir, '..', 'content', 'content_final')
        
        tasks = [process_language(lang, input_base_dir, output_base_dir, content_id, valid_platforms, client) for lang in valid_languages]
        await asyncio.gather(*tasks)
    except Exception as e:
        logger.error(f"Script execution failed: {str(e)}")
        raise
    finally:
        if client:
            await client.close()
            logger.info("Groq API client closed successfully")
    
    logger.info(f"Completed AI writing and voice generation for content_id {content_id}")

def run_ai_writer_voicegen() -> None:
    """Wrapper to run the async function with CLI arguments."""
    parser = argparse.ArgumentParser(description="Run Agent G: AI Writer & Voice Generator")
    parser.add_argument('--content_id', required=True, help='Content ID to process')
    parser.add_argument('--platforms', required=True, help='Comma-separated list of platforms (e.g., instagram,twitter,linkedin,sanatan)')
    parser.add_argument('--user_id', required=True, help='User ID for personalization')
    parser.add_argument('--sentiment', choices=['uplifting', 'neutral', 'devotional'], default='neutral', help='Sentiment to apply')
    parser.add_argument('--languages', help='Comma-separated list of languages (e.g., en,hi,sa)', default='en,hi,sa')
    args = parser.parse_args()
    
    platforms = args.platforms.split(',')
    languages = args.languages.split(',')
    asyncio.run(run_ai_writer_voicegen_async(args.content_id, platforms, args.user_id, args.sentiment, languages))

if __name__ == "__main__":
    run_ai_writer_voicegen()