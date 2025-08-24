#!/usr/bin/env python3
"""
Language Mapper Agent for Vaani Sentinel X.
Maps language codes to appropriate processing pipelines.
"""

import os
import sys
import argparse
import logging
from typing import Dict, List

# Add parent directory to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from config.settings import get_config
from utils.common import setup_logger, validate_language


class LanguageMapper:
    """Maps languages to appropriate processing pipelines."""
    
    def __init__(self):
        self.config = get_config()
        self.logger = setup_logger('language_mapper', 'language_mapper_user')
        
        # Language to pipeline mapping
        self.language_pipelines = {
            # Devanagari script languages
            'hi': 'devanagari_pipeline',
            'sa': 'devanagari_pipeline', 
            'mr': 'devanagari_pipeline',
            'bn': 'devanagari_pipeline',
            'gu': 'devanagari_pipeline',
            'pa': 'devanagari_pipeline',
            
            # Dravidian languages
            'ta': 'dravidian_pipeline',
            'te': 'dravidian_pipeline',
            'kn': 'dravidian_pipeline',
            'ml': 'dravidian_pipeline',
            
            # CJK languages
            'zh': 'cjk_pipeline',
            'ja': 'cjk_pipeline',
            
            # Arabic script
            'ar': 'arabic_pipeline',
            
            # Latin script
            'en': 'latin_pipeline',
            'es': 'latin_pipeline',
            'fr': 'latin_pipeline',
            'de': 'latin_pipeline',
            'ru': 'latin_pipeline',
            'pt': 'latin_pipeline',
            'it': 'latin_pipeline',
        }
    
    def map_language_to_pipeline(self, language: str) -> str:
        """Map a language code to its processing pipeline."""
        if not validate_language(language):
            self.logger.warning(f"Unsupported language: {language}, defaulting to latin_pipeline")
            return 'latin_pipeline'
        
        pipeline = self.language_pipelines.get(language, 'latin_pipeline')
        self.logger.info(f"Mapped language '{language}' to pipeline '{pipeline}'")
        return pipeline
    
    def get_supported_languages(self) -> List[str]:
        """Get list of supported languages."""
        return list(self.language_pipelines.keys())
    
    def get_pipeline_languages(self, pipeline: str) -> List[str]:
        """Get languages supported by a specific pipeline."""
        return [lang for lang, pipe in self.language_pipelines.items() if pipe == pipeline]
    
    def run_mapping(self, languages: List[str]) -> Dict[str, str]:
        """Map multiple languages to their pipelines."""
        self.logger.info(f"Starting language mapping for: {languages}")
        
        mapping = {}
        for language in languages:
            mapping[language] = self.map_language_to_pipeline(language)
        
        self.logger.info(f"Language mapping completed: {mapping}")
        return mapping


def main():
    """Main function for language mapper agent."""
    parser = argparse.ArgumentParser(description="Vaani Sentinel X: Language Mapper")
    parser.add_argument('--languages', nargs='+', default=['en'], 
                       help="Languages to map (e.g., en hi sa)")
    
    args = parser.parse_args()
    
    try:
        mapper = LanguageMapper()
        result = mapper.run_mapping(args.languages)
        
        print("\n=== Language Mapping Results ===")
        for lang, pipeline in result.items():
            print(f"Language: {lang} -> Pipeline: {pipeline}")
        
        print(f"\n✓ Language mapping completed successfully")
        
    except Exception as e:
        logger = setup_logger('language_mapper', 'language_mapper_user')
        logger.error(f"Language mapping failed: {e}")
        print(f"✗ Language mapping failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()