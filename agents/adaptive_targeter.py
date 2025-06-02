import json
import os
import logging
import glob
import re
import shutil
import argparse
from datetime import datetime
from typing import Dict, List
import platform
import uuid

# Logging setup for Agent I (Context-Aware Platform Targeter)
USER_ID = 'agent_i_user'
logger = logging.getLogger('adaptive_targeter')
logger.setLevel(logging.INFO)
log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'logs')
os.makedirs(log_dir, exist_ok=True)
log_path = os.path.join(log_dir, 'adaptive_targeter.txt')
file_handler = logging.FileHandler(log_path, encoding='utf-8')
file_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - User: %(user)s - %(message)s')
file_handler.setFormatter(formatter)
file_handler.addFilter(lambda record: setattr(record, 'user', USER_ID) or True)
logger.handlers = [file_handler]

def tailor_content(content: str, platform: str, content_type: str, language: str) -> str:
    """Tailor content for specific platform and type (Task 2: Agent I)."""
    try:
        # Clean up content by removing commentary and notes
        if content_type == 'voice_script':
            # Remove lines like "voice script in a neutral and devotional tone suitable for Sanatan voice assistants:"
            content = re.sub(r'voice script in a [a-zA-Z\s]+tone[a-zA-Z\s:]*?\n', '', content, flags=re.DOTALL)
            # Remove lines like "Note: ..." or "[Note: ...]"
            content = re.sub(r'(\[Note:.*?]|\bNote:.*?(?:\n|$))', '', content, flags=re.DOTALL)

        # Fix typos in English content
        if language == 'en':
            content = content.replace('wAIting', 'waiting').replace('dAIly', 'daily')
            content = content.replace('sustAInable', 'sustainable').replace('rAIse', 'raise')
            content = content.replace('awAIt', 'await').replace('AIr', 'air').replace('fAIth', 'faith')
            content = content.replace('blockchAIn', 'blockchain').replace('remAIn', 'remain')
            content = content.replace('captAIn', 'captain')
            content = content.replace('a blue hue', 'blue hue').replace('a era', 'era')
            content = re.sub(r'get ready soar', 'get ready to soar', content)

        # Fix language inconsistencies and grammar in Hindi
        if language == 'hi':
            content = content.replace('تکنولوجिकल', 'तकनीकी')  # Replace Urdu with Hindi
            content = content.replace('新的', 'नए')  # Replace Chinese with Hindi
            content = re.sub(r'जिसके साथ हम का पल आनंद बिताते हैं।', 'जिसके साथ हम हर पल आनंद बिताते हैं।', content)
            content = re.sub(r'लिए यह एक संकेत कि हमारे जीवन में', 'यह एक संकेत है कि हमारे जीवन में', content)
            content = re.sub(r'क्योंकि इन शब्दों महादेव सान्निध्य', 'क्योंकि इन शब्दों में महादेव का सान्निध्य है', content)
            content = re.sub(r'अपने की लड़ाई में जीत हासिल करें', 'अपने लक्ष्य की लड़ाई में जीत हासिल करें', content)
            content = content.replace('इसका उपयोग कर हमारे व्यवसाय लेनदेन', 'इसका उपयोग करके हम हमारे व्यवसाय लेनदेन')
            content = content.replace('हो जाता हैं', 'हो जाता है')
            content = content.replace('नित é प्रेरणा', 'नित्य प्रेरणा')

        # Fix language inconsistencies in Sanskrit
        if language == 'sa':
            content = content.replace('पापम्ハ हन्ति', 'पापं हन्ति')  # Replace Japanese katakana with Sanskrit

        if platform == 'linkedin' and content_type == 'tweet':
            tailored = f"{content[:260]}..." if len(content) > 280 else content
            logger.info(f"Tailored LinkedIn tweet: {tailored}")
            return tailored
        elif platform == 'twitter' and content_type == 'tweet':
            hashtags_map = {
                'en': ['#Inspiration', '#Motivation', '#Growth', '#Wisdom'],
                'hi': ['#प्रेरणा', '#उत्साह', '#सकारात्मक', '#ज्ञान'],
                'sa': ['#प्रेरणा', '#सनातन', '#आनन्दः', '#शान्तिः']
            }
            hashtags = hashtags_map.get(language, ['#Inspiration'])[:2]
            # Remove all hashtags at the end
            main_content = re.sub(r'(\s*#\w+)+$', '', content.strip())
            # Always append exactly 1–2 hashtags
            tailored = f"{main_content} {' '.join(hashtags)}"
            logger.info(f"Tailored Twitter tweet (lang: {language}): {tailored}")
            return tailored.strip()
        elif platform == 'instagram' and content_type == 'post':
            hashtags_map = {
                'en': ['#Inspiration', '#Motivation', '#Uplifting', '#GoodVibes', '#Growth'],
                'hi': ['#प्रेरणा', '#उत्साह', '#सकारात्मक', '#खुशरहो', '#ज्ञान'],
                'sa': ['#प्रेरणा', '#आनन्दः', '#सनातन', '#शान्तिः', '#ज्ञान']
            }
            emoji_map = {'en': '🌟', 'hi': '✨', 'sa': '🕉️'}
            hashtags = hashtags_map.get(language, ['#Inspiration', '#Motivation', '#Uplifting', '#GoodVibes'])[:4]
            emoji = emoji_map.get(language, '🌟')
            # Remove all hashtags and emojis at the end
            main_content = re.sub(r'(\s*#\w+)*\s*[\U0001F300-\U0001FAFF]*$', '', content.strip())
            # Always append emoji and exactly 3–4 hashtags
            tailored = f"{main_content}\n{emoji} {' '.join(hashtags[:4])}"
            logger.info(f"Tailored Instagram post (lang: {language}): {tailored}")
            return tailored.strip()
        elif platform == 'spotify' and content_type == 'voice_script':
            intro_map = {
                'en': '[Intro: Welcome to our Spotify podcast! This is a 30-second introduction.]',
                'hi': '[प्रस्तावना: हमारे Spotify पॉडकास्ट में आपका स्वागत है! यह 30-सेकंड की प्रस्तावना है.]',
                'sa': '[प्रस्तावना: Spotify वार्तालापे स्वागतम्! एषा 30-क्षणस्य प्रस्तावना अस्ति.]'
            }
            outro_map = {
                'en': '[Outro: Thanks for listening on Spotify! This is a 30-second outro.]',
                'hi': '[समापन: सुनने के लिए धन्यवाद! यह 30-सेकंड का समापन है.]',
                'sa': '[समापन: श्रवणाय धन्यवादः! एषः 30-क्षणस्य समापनम् अस्ति.]'
            }
            intro = intro_map.get(language, '[Intro: 30-sec intro]')
            outro = outro_map.get(language, '[Outro: 30-sec outro]')
            # Remove any previous intros/outros
            content_clean = re.sub(r'^\[Intro:.*?\]\s*', '', content.strip(), flags=re.DOTALL)
            content_clean = re.sub(r'\[Outro:.*?\]\s*$', '', content_clean, flags=re.DOTALL)
            # Always add intro and outro
            tailored = f"{intro}\n{content_clean}\n{outro}"
            logger.info(f"Tailored Spotify voice script (lang: {language}): {tailored}")
            return tailored.strip()
        elif platform == 'sanatan' and content_type == 'voice_script':
            prefix = {
                'en': 'Welcome to our Sanatan voice assistant!',
                'hi': 'हमारे सनातन वॉयस असिस्टेंट में स्वागत है!',
                'sa': 'सनातन वाचः सहायके स्वागतम्!'
            }
            outro_map = {
                'en': 'Namaste, dear one.',
                'hi': 'नमस्ते, प्रिय मित्र।',
                'sa': 'नमस्ते, प्रियः।'
            }
            main_content = content.strip()
            # Remove any existing prefix or outro to avoid duplication
            for lang, pfx in prefix.items():
                main_content = main_content.replace(pfx, '').strip()
            for lang, out in outro_map.items():
                main_content = main_content.replace(out, '').strip()
            # Add prefix and outro
            tailored = f"{prefix.get(language, 'Welcome!')} {main_content} {outro_map.get(language, 'Namaste.')}"
            logger.info(f"Tailored Sanatan voice script (lang: {language}): {tailored}")
            return tailored.strip()
        logger.info(f"No tailoring applied for platform: {platform}, content_type: {content_type}, content: {content}")
        return content.strip()
    except Exception as e:
        logger.error(f"Failed to tailor content for {platform} {content_type} (lang: {language}): {str(e)}")
        return content.strip()

def regenerate_tts(voice_file: str, tailored_content: str, lang: str) -> bool:
    """Regenerate the corresponding MP3 file for a voice script, ensuring only one MP3 per voice script."""
    try:
        # Check if running in Pyodide (Emscripten environment)
        if platform.system() == "Emscripten":
            logger.warning(f"TTS generation is not supported in Pyodide for {voice_file}. MP3 generation skipped.")
            return True  # Skip actual TTS generation but proceed as if successful

        # If not in Pyodide, proceed with TTS generation
        from gtts import gTTS  # Import here to avoid issues in Pyodide

        # Extract the base filename (e.g., 'voice_1_sanatan')
        base_name = '_'.join(os.path.basename(voice_file).split('_')[:3])  # e.g., 'voice_1_sanatan'
        mp3_dir = os.path.dirname(voice_file)
        # Generate a consistent UUID for the MP3 file to avoid duplicates
        uuid_str = str(uuid.uuid5(uuid.NAMESPACE_DNS, base_name))
        mp3_path = os.path.join(mp3_dir, f"{base_name}_{uuid_str}.mp3")

        # Map language codes to gTTS language codes
        tts_lang_map = {'en': 'en', 'hi': 'hi', 'sa': 'hi'}  # Sanskrit uses Hindi TTS as a fallback
        tts_lang = tts_lang_map.get(lang, 'en')

        # Always regenerate the MP3 file to ensure it matches the tailored content
        logger.info(f"Regenerating MP3 for {voice_file} at {mp3_path}")
        tts = gTTS(text=tailored_content, lang=tts_lang, slow=False)
        tts.save(mp3_path)
        logger.info(f"Generated TTS MP3 at {mp3_path}")

        return True
    except Exception as e:
        logger.error(f"Failed to regenerate TTS for {voice_file}: {str(e)}")
        return False

def clear_mp3_files(lang_dir: str) -> None:
    """Clear all existing MP3 files in the specified directory."""
    try:
        mp3_files = glob.glob(os.path.join(lang_dir, '*.mp3'))
        for mp3_file in mp3_files:
            os.remove(mp3_file)
            logger.info(f"Removed MP3 file: {mp3_file}")
    except Exception as e:
        logger.error(f"Failed to clear MP3 files in {lang_dir}: {str(e)}")

def process_files(input_dir: str, lang: str) -> None:
    """Process content files for a given language, avoiding duplicates (Task 2: Agent I)."""
    # Compute absolute path for input_dir
    abs_input_dir = os.path.abspath(input_dir)
    lang_dir = os.path.join(abs_input_dir, lang)
    
    # Debug: Log the absolute path and check if the directory exists
    logger.info(f"Looking for files in absolute path: {lang_dir}")
    if not os.path.exists(lang_dir):
        logger.warning(f"No content directory found for {lang} at {lang_dir}")
        return
    logger.info(f"Directory exists for {lang}: {lang_dir}")

    # Clear existing MP3 files for this language
    clear_mp3_files(lang_dir)

    processed_files = set()
    tailored_pattern = re.compile(r'.*_\d{8}_\d{6}\.json$')

    # Debug: Log all files found in the directory
    all_files = glob.glob(os.path.join(lang_dir, '*.json'))
    logger.info(f"All JSON files in {lang_dir}: {all_files}")

    # Process tweets
    tweet_files = [
        f for f in glob.glob(os.path.join(lang_dir, 'tweet_*.json'))
        if not tailored_pattern.match(os.path.basename(f)) and f not in processed_files
    ]
    logger.info(f"Found {len(tweet_files)} unique tweet files for {lang}: {tweet_files}")
    for tweet_file in tweet_files:
        try:
            with open(tweet_file, 'r', encoding='utf-8') as f:
                content = json.load(f)
            content_id = content.get('id')
            platform = content.get('platform')
            tweet_text = content.get('tweet', '')
            sentiment = content.get('sentiment', 'neutral')  # Preserve sentiment
            tone = content.get('tone', 'formal')  # Preserve tone
            content_type = content.get('content_type', 'tweet')  # Preserve content_type
            version = content.get('version', 1)  # Preserve version
            if not content_id or not platform:
                logger.warning(f"Missing ID or platform in {tweet_file}, skipping")
                continue
            if not tweet_text:
                logger.warning(f"No tweet text found in {tweet_file}, skipping")
                continue
            tailored_tweet = tailor_content(tweet_text, platform, 'tweet', lang)
            with open(tweet_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'id': content_id,
                    'tweet': tailored_tweet,
                    'platform': platform,
                    'content_type': content_type,
                    'tone': tone,
                    'sentiment': sentiment,
                    'version': version
                }, f, ensure_ascii=False, indent=2)
            logger.info(f"Overwrote tailored tweet in {tweet_file}")
            processed_files.add(tweet_file)
        except Exception as e:
            logger.error(f"Failed to process tweet file {tweet_file}: {str(e)}")

    # Process posts
    post_files = [
        f for f in glob.glob(os.path.join(lang_dir, 'post_*.json'))
        if not tailored_pattern.match(os.path.basename(f)) and f not in processed_files
    ]
    logger.info(f"Found {len(post_files)} unique post files for {lang}: {post_files}")
    for post_file in post_files:
        try:
            with open(post_file, 'r', encoding='utf-8') as f:
                content = json.load(f)
            content_id = content.get('id')
            platform = content.get('platform')
            post_text = content.get('post', '')
            sentiment = content.get('sentiment', 'neutral')  # Preserve sentiment
            tone = content.get('tone', 'casual')  # Preserve tone
            content_type = content.get('content_type', 'post')  # Preserve content_type
            version = content.get('version', 1)  # Preserve version
            if not content_id or not platform:
                logger.warning(f"Missing ID or platform in {post_file}, skipping")
                continue
            if not post_text:
                logger.warning(f"No post text found in {post_file}, skipping")
                continue
            tailored_post = tailor_content(post_text, platform, 'post', lang)
            with open(post_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'id': content_id,
                    'post': tailored_post,
                    'platform': platform,
                    'content_type': content_type,
                    'tone': tone,
                    'sentiment': sentiment,
                    'version': version
                }, f, ensure_ascii=False, indent=2)
            logger.info(f"Overwrote tailored post in {post_file}")
            processed_files.add(post_file)
        except Exception as e:
            logger.error(f"Failed to process post file {post_file}: {str(e)}")

    # Process voice scripts
    voice_files = [
        f for f in glob.glob(os.path.join(lang_dir, 'voice_*.json'))
        if not tailored_pattern.match(os.path.basename(f)) and f not in processed_files
    ]
    logger.info(f"Found {len(voice_files)} unique voice script files for {lang}: {voice_files}")
    for voice_file in voice_files:
        try:
            with open(voice_file, 'r', encoding='utf-8') as f:
                content = json.load(f)
            content_id = content.get('id')
            platform = content.get('platform')
            voice_script = content.get('voice_script', '')
            sentiment = content.get('sentiment', 'neutral')  # Preserve sentiment
            tone = content.get('tone', 'devotional')  # Preserve tone
            content_type = content.get('content_type', 'voice_script')  # Preserve content_type
            version = content.get('version', 1)  # Preserve version
            if not content_id or not platform:
                logger.warning(f"Missing ID or platform in {voice_file}, skipping")
                continue
            if not voice_script:
                logger.warning(f"No voice script found in {voice_file}, skipping")
                continue
            tailored_voice = tailor_content(voice_script, platform, 'voice_script', lang)
            with open(voice_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'id': content_id,
                    'voice_script': tailored_voice,
                    'platform': platform,
                    'content_type': content_type,
                    'tone': tone,
                    'sentiment': sentiment,
                    'version': version
                }, f, ensure_ascii=False, indent=2)
            logger.info(f"Overwrote tailored voice script in {voice_file}")
            # Regenerate the corresponding MP3 file if necessary
            if not regenerate_tts(voice_file, tailored_voice, lang):
                logger.warning(f"TTS regeneration failed for {voice_file}, proceeding without MP3 update")
            processed_files.add(voice_file)
        except Exception as e:
            logger.error(f"Failed to process voice file {voice_file}: {str(e)}")

def run_adaptive_targeter(selected_language: str) -> None:
    """Run Agent I: Context-Aware Platform Targeter for the specified language (Task 2)."""
    logger.info(f"Starting Agent I: Context-Aware Platform Targeter for language: {selected_language}")
    # Compute absolute path for the input directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    input_dir = os.path.join(script_dir, '..', 'content', 'content_ready')
    logger.info(f"Input directory (absolute path): {input_dir}")
    
    languages_to_process = ['en', 'hi', 'sa'] if selected_language == 'all' else [selected_language]
    for lang in languages_to_process:
        lang_dir = os.path.join(input_dir, lang)
        try:
            if not os.path.exists(lang_dir):
                os.makedirs(lang_dir, exist_ok=True)
                logger.warning(f"Created missing content directory for {lang} at {lang_dir}")
            process_files(input_dir, lang)
        except Exception as e:
            logger.error(f"Failed to process content for {lang}: {str(e)}")
    logger.info("Completed content tailoring")

def main() -> None:
    """Main function to run the adaptive targeter with a language argument."""
    parser = argparse.ArgumentParser(description="Run Agent I: Context-Aware Platform Targeter")
    parser.add_argument('language', choices=['en', 'hi', 'sa', 'all'], help="Language to process (en, hi, sa, all)")
    args = parser.parse_args()
    
    run_adaptive_targeter(args.language)

if __name__ == "__main__":
    main()