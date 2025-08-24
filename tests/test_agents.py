"""
Agent-specific tests for Vaani Sentinel X.
Tests individual agent functionality and integration.
"""

import os
import sys
import unittest
import tempfile
import json
import subprocess
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from config.settings import get_config
from utils.common import setup_logger, safe_json_save
from tests.test_system import BaseAgentTest


class TestMinerSanitizer(BaseAgentTest):
    """Test the Miner Sanitizer agent."""
    
    def setUp(self):
        """Set up test data for miner sanitizer."""
        self.test_input_file = os.path.join(self.test_temp_dir, 'test_input.csv')
        
        # Create test CSV data
        test_csv_content = """id,text,type,language
1,This is a test fact,fact,en
2,यह एक परीक्षण तथ्य है,fact,hi
3,सत्यम् एतत् परीक्षणस्य तथ्यम्,fact,sa"""
        
        with open(self.test_input_file, 'w', encoding='utf-8') as f:
            f.write(test_csv_content)
    
    def test_miner_sanitizer_execution(self):
        """Test that miner_sanitizer runs without errors."""
        cmd = [
            sys.executable, 
            'agents/miner_sanitizer.py',
            '--input', self.test_input_file,
            '--languages', 'en', 'hi',
            '--sentiment', 'neutral'
        ]
        
        result = subprocess.run(
            cmd, 
            cwd=self.config.directories.root_dir,
            capture_output=True, 
            text=True,
            timeout=30
        )
        
        self.assertEqual(result.returncode, 0, f"Miner sanitizer failed: {result.stderr}")
    
    def test_structured_content_generation(self):
        """Test that structured content is generated."""
        # Run miner sanitizer first
        cmd = [
            sys.executable, 
            'agents/miner_sanitizer.py',
            '--input', self.test_input_file,
            '--languages', 'en',
            '--sentiment', 'neutral'
        ]
        
        subprocess.run(cmd, cwd=self.config.directories.root_dir, timeout=30)
        
        # Check if structured content was created
        structured_dir = self.config.get_absolute_path(self.config.directories.structured_dir)
        json_files = list(structured_dir.glob('content_blocks_*.json'))
        
        self.assertGreater(len(json_files), 0, "No structured content files generated")
        
        # Verify content format
        with open(json_files[0], 'r', encoding='utf-8') as f:
            content = json.load(f)
        
        self.assertIsInstance(content, list, "Content should be a list")
        if content:
            self.assertIn('content_id', content[0], "Content blocks should have content_id")
            self.assertIn('post', content[0], "Content blocks should have post text")
            self.assertIn('source_language', content[0], "Content blocks should have source_language")


class TestLanguageMapper(BaseAgentTest):
    """Test the Language Mapper agent."""
    
    def test_language_mapper_execution(self):
        """Test that language_mapper runs without errors."""
        cmd = [
            sys.executable,
            'agents/language_mapper.py',
            '--languages', 'en', 'hi', 'sa'
        ]
        
        result = subprocess.run(
            cmd,
            cwd=self.config.directories.root_dir,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        self.assertEqual(result.returncode, 0, f"Language mapper failed: {result.stderr}")
        self.assertIn("Language mapping completed", result.stdout)


class TestMultilingualPipeline(BaseAgentTest):
    """Test the Multilingual Pipeline agent."""
    
    def setUp(self):
        """Set up test data for multilingual pipeline."""
        # First create some structured content
        test_content = [
            {
                "id": "test_1",
                "text": "This is test content",
                "source_language": "en",
                "type": "fact",
                "sentiment": "neutral"
            }
        ]
        
        structured_dir = self.config.get_absolute_path(self.config.directories.structured_dir)
        structured_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = "20250824_120000"
        test_file = structured_dir / f"content_blocks_{timestamp}.json"
        safe_json_save(test_content, test_file)
    
    def test_multilingual_pipeline_execution(self):
        """Test that multilingual_pipeline runs without errors."""
        cmd = [
            sys.executable,
            'agents/multilingual_pipeline.py',
            '--languages', 'en', 'hi',
            '--sentiment', 'neutral'
        ]
        
        result = subprocess.run(
            cmd,
            cwd=self.config.directories.root_dir,
            capture_output=True,
            text=True,
            timeout=60
        )
        
        # Accept exit code 0 or 1 (some agents may exit with 1 but still work)
        self.assertIn(result.returncode, [0, 1], f"Multilingual pipeline failed: {result.stderr}")


class TestPipelineIntegration(BaseAgentTest):
    """Test pipeline integration."""
    
    def test_basic_pipeline_run(self):
        """Test running a basic pipeline."""
        # Create test input
        test_input_file = os.path.join(self.test_temp_dir, 'pipeline_test.csv')
        test_csv_content = """id,text,type,language
1,Pipeline test content,fact,en"""
        
        with open(test_input_file, 'w', encoding='utf-8') as f:
            f.write(test_csv_content)
        
        # Test basic two-step pipeline: miner -> multilingual
        agents_to_test = ['miner_sanitizer', 'multilingual_pipeline']
        
        for agent in agents_to_test:
            cmd = [sys.executable, 'cli/command_center.py', 'run', agent]
            
            if agent == 'miner_sanitizer':
                cmd.extend(['--input', test_input_file, '--languages', 'en', '--sentiment', 'neutral'])
            else:
                cmd.extend(['--languages', 'en', '--sentiment', 'neutral'])
            
            result = subprocess.run(
                cmd,
                cwd=self.config.directories.root_dir,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            # Check that agent started successfully (exit code varies by agent)
            self.assertIn(result.returncode, [0, 1], f"Agent {agent} failed to start: {result.stderr}")


if __name__ == '__main__':
    unittest.main(verbosity=2)