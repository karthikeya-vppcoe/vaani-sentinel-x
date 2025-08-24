#!/usr/bin/env python3
"""
Simulated Translation Generator for Vaani Sentinel X.
Generates simulated translations for testing and development.
"""

import os
import sys
import argparse
import logging
import json
from typing import Dict, List, Optional
from datetime import datetime, timezone

# Add parent directory to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from config.settings import get_config
from utils.common import setup_logger, validate_language, safe_json_save, generate_content_id


class SimulateTranslation:
    """Generates simulated translations for testing purposes."""
    
    def __init__(self):
        self.config = get_config()
        self.logger = setup_logger('simulate_translation', 'simulate_translation_user')
        
        # Sample translations for common phrases
        self.sample_translations = {
            'en': {
                'hello': 'Hello',
                'goodbye': 'Goodbye', 
                'thank_you': 'Thank you',
                'welcome': 'Welcome',
                'good_morning': 'Good morning'
            },
            'hi': {
                'hello': 'नमस्ते',
                'goodbye': 'अलविदा',
                'thank_you': 'धन्यवाद',
                'welcome': 'स्वागत है',
                'good_morning': 'शुभ प्रभात'
            },
            'sa': {
                'hello': 'नमस्कारः',
                'goodbye': 'पुनर्मिलाम',
                'thank_you': 'धन्यवादः',
                'welcome': 'स्वागतम्',
                'good_morning': 'सुप्रभातम्'
            },
            'es': {
                'hello': 'Hola',
                'goodbye': 'Adiós',
                'thank_you': 'Gracias',
                'welcome': 'Bienvenido',
                'good_morning': 'Buenos días'
            },
            'fr': {
                'hello': 'Bonjour',
                'goodbye': 'Au revoir',
                'thank_you': 'Merci',
                'welcome': 'Bienvenue',
                'good_morning': 'Bonjour'
            }
        }
    
    def generate_translation(self, text: str, source_lang: str, target_lang: str) -> str:
        """Generate simulated translation."""
        # Simple keyword-based translation for testing
        if source_lang == target_lang:
            return text
        
        # Check if it's a known phrase
        source_dict = self.sample_translations.get(source_lang, {})
        target_dict = self.sample_translations.get(target_lang, {})
        
        # Find matching phrase
        for phrase_key, phrase_text in source_dict.items():
            if text.lower().strip() == phrase_text.lower():
                return target_dict.get(phrase_key, f"[SIMULATED: {text} -> {target_lang}]")
        
        # For unknown text, return simulated translation
        return f"[SIMULATED: '{text}' from {source_lang} to {target_lang}]"
    
    def generate_translations(self, content_blocks: List[Dict], target_languages: List[str]) -> List[Dict]:
        """Generate translations for content blocks."""
        self.logger.info(f"Starting translation simulation for {len(content_blocks)} blocks to languages: {target_languages}")
        
        translated_blocks = []
        
        for block in content_blocks:
            source_lang = block.get('source_language', 'en')
            source_text = block.get('text', '')
            
            for target_lang in target_languages:
                if target_lang == source_lang:
                    continue
                
                translated_text = self.generate_translation(source_text, source_lang, target_lang)
                
                translated_block = {
                    'id': generate_content_id(),
                    'original_id': block.get('id'),
                    'text': translated_text,
                    'source_language': source_lang,
                    'target_language': target_lang,
                    'translation_type': 'simulated',
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    'metadata': {
                        'original_text': source_text,
                        'translation_confidence': 0.85,  # Simulated confidence
                        'method': 'keyword_matching'
                    }
                }
                
                translated_blocks.append(translated_block)
        
        self.logger.info(f"Generated {len(translated_blocks)} simulated translations")
        return translated_blocks
    
    def run_simulation(self, source_file: str, target_languages: List[str], output_file: Optional[str] = None) -> None:
        """Run translation simulation."""
        self.logger.info(f"Starting translation simulation from {source_file}")
        
        # Load source content
        try:
            with open(source_file, 'r', encoding='utf-8') as f:
                content_blocks = json.load(f)
        except Exception as e:
            self.logger.error(f"Failed to load source file {source_file}: {e}")
            raise
        
        # Generate translations
        translated_blocks = self.generate_translations(content_blocks, target_languages)
        
        # Save results
        if output_file:
            output_path = output_file
        else:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_dir = self.config.get_absolute_path(self.config.directories.structured_dir)
            output_path = output_dir / f"simulated_translations_{timestamp}.json"
        
        success = safe_json_save(translated_blocks, output_path)
        if success:
            self.logger.info(f"Saved {len(translated_blocks)} translations to {output_path}")
            print(f"✓ Saved {len(translated_blocks)} simulated translations to {output_path}")
        else:
            self.logger.error("Failed to save translations")
            raise RuntimeError("Failed to save translations")


def main():
    """Main function for simulated translation generator."""
    parser = argparse.ArgumentParser(description="Vaani Sentinel X: Simulated Translation Generator")
    parser.add_argument('--source', required=True, help="Source content file (JSON)")
    parser.add_argument('--languages', nargs='+', default=['hi', 'sa'], 
                       help="Target languages for translation")
    parser.add_argument('--output', help="Output file path (optional)")
    
    args = parser.parse_args()
    
    try:
        # Validate target languages
        invalid_languages = [lang for lang in args.languages if not validate_language(lang)]
        if invalid_languages:
            print(f"✗ Invalid languages: {invalid_languages}")
            sys.exit(1)
        
        simulator = SimulateTranslation()
        simulator.run_simulation(args.source, args.languages, args.output)
        
        print("✓ Translation simulation completed successfully")
        
    except Exception as e:
        logger = setup_logger('simulate_translation', 'simulate_translation_user')
        logger.error(f"Translation simulation failed: {e}")
        print(f"✗ Translation simulation failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()