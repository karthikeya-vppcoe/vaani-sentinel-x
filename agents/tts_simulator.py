import json
import os
import logging
import glob
import uuid
import re
from datetime import datetime, timezone
from typing import Dict, List
from pathlib import Path

# Logging setup for TTS Simulator
USER_ID = 'tts_sim_user'
logger = logging.getLogger('tts_simulator')
logger.setLevel(logging.DEBUG)  # Increased verbosity for debugging

script_dir = os.path.dirname(os.path.abspath(__file__))
logs_dir = os.path.join(script_dir, '..', 'logs')
os.makedirs(logs_dir, exist_ok=True)

file_handler = logging.FileHandler(os.path.join(logs_dir, 'tts_simulator.txt'), encoding='utf-8')
file_handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - User: %(user)s - %(message)s')
file_handler.setFormatter(formatter)
file_handler.addFilter(lambda record: setattr(record, 'user', USER_ID) or True)
logger.handlers = [file_handler, logging.StreamHandler()]

class TTSSimulator:
    def __init__(self):
        """Initialize the TTS Simulator."""
        self.supported_languages = [
            'en', 'hi', 'sa', 'mr', 'ta', 'te', 'kn', 'ml', 'bn', 'gu', 'pa',  # Indian
            'es', 'fr', 'de', 'zh', 'ja', 'ru', 'ar', 'pt', 'it'  # Global
        ]
        logger.info("TTSSimulator initialized with supported languages: %s", self.supported_languages)

    def clean_voice_script(self, voice_script: str) -> str:
        """Clean voice script by removing extra quotes, trailing punctuation, and incomplete phrases."""
        voice_script = voice_script.strip()
        voice_script = re.sub(r'^"|"$', '', voice_script)  # Remove leading/trailing quotes
        voice_script = re.sub(r'\s*\."\s*$', '', voice_script)  # Remove trailing quote and period
        voice_script = re.sub(r'\s*\.\s*$', '', voice_script)  # Remove trailing period
        voice_script = re.sub(r'\s+and\s+your\s+spirit\s+lifted\s+with\.\s*$', '', voice_script)  # Remove incomplete phrase
        voice_script = re.sub(r'\s+filled\s+with\s*\.\s*$', '', voice_script)  # Remove incomplete phrase
        voice_script = re.sub(r'\s+', ' ', voice_script).strip()  # Normalize spaces
        return voice_script

    def load_language_voice_map(self, language_voice_map_path: str) -> Dict:
        """Load language voice map from JSON file."""
        try:
            with open(language_voice_map_path, 'r', encoding='utf-8') as f:
                voice_map = json.load(f)
            logger.info("Loaded language voice map from %s: %s", language_voice_map_path, json.dumps(voice_map, ensure_ascii=False, indent=2))
            return voice_map
        except Exception as e:
            logger.error("Failed to load language voice map from %s: %s", language_voice_map_path, str(e))
            default_map = {
                lang: {
                    'devotional': {
                        'uplifting': [f"{lang}_female_devotional_1", f"{lang}_male_devotional_1"],
                        'neutral': [f"{lang}_female_neutral_1"]
                    },
                    'casual': {
                        'uplifting': [f"{lang}_female_casual_1"],
                        'neutral': [f"{lang}_female_neutral_2"]
                    }
                } for lang in self.supported_languages
            }
            logger.info("Using default language voice map: %s", json.dumps(default_map, ensure_ascii=False, indent=2))
            return default_map

    def validate_content(self, content: Dict, content_id: str) -> bool:
        """Validate content JSON schema."""
        required_fields = ['content_id', 'voice_script', 'platform', 'content_type', 'tone', 'sentiment', 'language']
        missing_fields = [field for field in required_fields if field not in content]
        if missing_fields:
            logger.warning("Missing fields %s in content for content_id %s", missing_fields, content_id)
            return False
        if content['platform'] != 'sanatan' or content['content_type'] != 'voice_script':
            logger.warning("Invalid platform or content_type for content_id %s: %s, %s", content_id, content['platform'], content['content_type'])
            return False
        if content['language'] not in self.supported_languages:
            logger.warning("Invalid language for content_id %s: %s", content_id, content['language'])
            return False
        return True

    def load_personalized_content(self, personalized_content_path: str, content_id: str) -> List[Dict]:
        """Load personalized content from content_final directory."""
        content_list = []
        pattern = os.path.join(personalized_content_path, '*', f'voice_{content_id}_sanatan_*.json')
        logger.debug("Searching for content with pattern: %s", pattern)
        files_found = glob.glob(pattern, recursive=True)
        if not files_found:
            logger.warning("No content files found for content_id %s with pattern %s", content_id, pattern)
        for content_file in files_found:
            try:
                with open(content_file, 'r', encoding='utf-8') as f:
                    content = json.load(f)
                    if self.validate_content(content, content_id):
                        content_list.append(content)
                        logger.info("Loaded content from %s", content_file)
                    else:
                        logger.warning("Invalid content schema in %s, skipping", content_file)
            except Exception as e:
                logger.error("Failed to load content from %s: %s", content_file, str(e))
        return content_list

    def select_voice_tag(self, content: Dict, voice_map: Dict) -> str:
        """Select voice tag based on language, tone, and sentiment."""
        language = content.get('language', 'en')
        tone = content.get('tone', 'devotional')
        sentiment = content.get('sentiment', 'uplifting')
        existing_voice_tag = content.get('voice_tag', '')

        # Use existing voice_tag if present
        if existing_voice_tag:
            logger.info("Using existing voice_tag: %s for content_id %s", existing_voice_tag, content['content_id'])
            return existing_voice_tag

        # Select from voice_map
        try:
            # Check tone_voice_mapping first
            tone_voice = voice_map.get('tone_voice_mapping', {}).get(language, {}).get(tone, '')
            if tone_voice:
                logger.info("Selected voice_tag: %s for language: %s, tone: %s from tone_voice_mapping", tone_voice, language, tone)
                return tone_voice

            # Fallback to default_voices_by_language
            default_voice = voice_map.get('default_voices_by_language', {}).get(language, voice_map.get('fallback_voice_for_language', 'english_female_1'))
            if default_voice:
                logger.info("Selected default voice_tag: %s for language: %s", default_voice, language)
                return default_voice

            logger.warning("No voice tags found for language: %s, tone: %s, sentiment: %s", language, tone, sentiment)
        except Exception as e:
            logger.error("Error selecting voice tag for language: %s, tone: %s, sentiment: %s: %s", language, tone, sentiment, str(e))

        # Fallback to default
        default_voice = f"{language}_female_devotional_1"
        logger.warning("Using default voice_tag: %s for content_id %s", default_voice, content['content_id'])
        return default_voice

    def simulate_tts(self, personalized_content_path: str, language_voice_map_path: str, output_path: str, content_id: str):
        """Simulates TTS output and creates tts_simulation_output.json.

        Args:
            personalized_content_path (str): Path to content_final directory (e.g., E:\projects\vaani-sentinel-x\content\content_final).
            language_voice_map_path (str): Path to language_voice_map.json or updated_language_voice_map.json.
            output_path (str): Path to save tts_simulation_output.json (e.g., E:\projects\vaani-sentinel-x\data\tts_simulation_output.json).
            content_id (str): Content ID to process (e.g., 1b4239cf-7c8f-40c1-b265-757111149621).
        """
        logger.info("Starting TTS simulation for content_id: %s, content_path: %s, voice_map: %s, output: %s", content_id, personalized_content_path, language_voice_map_path, output_path)

        # Load voice map and content
        voice_map = self.load_language_voice_map(language_voice_map_path)
        content_list = self.load_personalized_content(personalized_content_path, content_id)

        if not content_list:
            logger.error("No valid content found for content_id %s in %s", content_id, personalized_content_path)
            return

        simulation_output = []
        for content in content_list:
            try:
                # Select voice tag
                voice_tag = self.select_voice_tag(content, voice_map)

                # Clean voice script
                voice_script = self.clean_voice_script(content['voice_script'])

                # Generate dummy audio path
                dummy_audio_path = os.path.abspath(os.path.join(
                    os.path.dirname(output_path),
                    f"voice_{content['content_id']}_sanatan_{uuid.uuid4().hex}.mp3"
                )).replace('\\', '\\\\')

                # Create simulation entry
                simulation_entry = {
                    'content_id': content['content_id'],
                    'language': content['language'],
                    'tone': content['tone'],
                    'sentiment': content['sentiment'],
                    'voice_tag': voice_tag,
                    'dummy_audio_path': dummy_audio_path,
                    'voice_script': voice_script,
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }
                simulation_output.append(simulation_entry)
                logger.info("Simulated TTS for content_id: %s, language: %s, voice_tag: %s, dummy_audio_path: %s", content['content_id'], content['language'], voice_tag, dummy_audio_path)
            except Exception as e:
                logger.error("Failed to simulate TTS for content_id %s: %s", content['content_id'], str(e))
                continue

        # Save simulation output
        try:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            if not os.access(os.path.dirname(output_path), os.W_OK):
                raise PermissionError(f"No write permission for {os.path.dirname(output_path)}")
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(simulation_output, f, ensure_ascii=False, indent=2)
            logger.info("Saved TTS simulation output to %s", output_path)
        except Exception as e:
            logger.error("Failed to save TTS simulation output to %s: %s", output_path, str(e))

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description="TTS Simulator for Vaani Sentinel X")
    parser.add_argument('--content_id', required=True, help='Content ID to process (e.g., 1b4239cf-7c8f-40c1-b265-757111149621)')
    parser.add_argument('--content_path', default='E:\\projects\\vaani-sentinel-x\\content\\content_final', help='Path to content_final directory')
    parser.add_argument('--voice_map_path', default='E:\\projects\\vaani-sentinel-x\\config\\language_voice_map.json', help='Path to language_voice_map.json')
    parser.add_argument('--output_path', default='E:\\projects\\vaani-sentinel-x\\data\\tts_simulation_output.json', help='Path to save tts_simulation_output.json')
    args = parser.parse_args()

    simulator = TTSSimulator()
    simulator.simulate_tts(args.content_path, args.voice_map_path, args.output_path, args.content_id)
    logger.info("TTSSimulator script executed.")