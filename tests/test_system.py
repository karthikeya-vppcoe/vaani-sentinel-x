"""
Basic test framework for Vaani Sentinel X agents.
Production-ready tests for deployment validation.
"""

import os
import sys
import unittest
import tempfile
import shutil
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from config.settings import get_config
from utils.common import HealthChecker, setup_logger


class BaseAgentTest(unittest.TestCase):
    """Base test class for agent testing."""
    
    @classmethod
    def setUpClass(cls):
        """Set up test environment."""
        cls.config = get_config()
        cls.health_checker = HealthChecker()
        cls.logger = setup_logger(f'test_{cls.__name__}', 'test_user')
        
        # Create temporary test directory
        cls.test_temp_dir = tempfile.mkdtemp(prefix='vaani_test_')
        
    @classmethod
    def tearDownClass(cls):
        """Clean up test environment."""
        if hasattr(cls, 'test_temp_dir') and os.path.exists(cls.test_temp_dir):
            shutil.rmtree(cls.test_temp_dir)
    
    def test_dependencies_available(self):
        """Test that all required dependencies are available."""
        health_status = self.health_checker.check_dependencies()
        missing_deps = [dep for dep, status in health_status.items() if not status]
        self.assertEqual(
            len(missing_deps), 0, 
            f"Missing dependencies: {missing_deps}"
        )
    
    def test_directories_exist(self):
        """Test that all required directories exist."""
        health_status = self.health_checker.check_directories()
        missing_dirs = [dir_name for dir_name, status in health_status.items() if not status]
        self.assertEqual(
            len(missing_dirs), 0,
            f"Missing directories: {missing_dirs}"
        )
    
    def test_config_files_exist(self):
        """Test that configuration files exist."""
        health_status = self.health_checker.check_config_files()
        missing_files = [file_name for file_name, status in health_status.items() if not status]
        self.assertEqual(
            len(missing_files), 0,
            f"Missing configuration files: {missing_files}"
        )


class TestCommandCenter(BaseAgentTest):
    """Test command center functionality."""
    
    def test_agent_paths_valid(self):
        """Test that all agent files exist."""
        from cli.command_center import AGENTS
        
        missing_agents = []
        for agent_id, agent_info in AGENTS.items():
            if not os.path.exists(agent_info['path']):
                missing_agents.append(f"{agent_id}: {agent_info['path']}")
        
        self.assertEqual(
            len(missing_agents), 0,
            f"Missing agent files: {missing_agents}"
        )
    
    def test_pipeline_agents_exist(self):
        """Test that all pipeline agents are defined."""
        from cli.command_center import PIPELINE, AGENTS
        
        missing_pipeline_agents = []
        for agent_id, agent_name in PIPELINE:
            if agent_id not in AGENTS:
                missing_pipeline_agents.append(f"{agent_id}: {agent_name}")
        
        self.assertEqual(
            len(missing_pipeline_agents), 0,
            f"Pipeline agents not in AGENTS: {missing_pipeline_agents}"
        )


class TestUtilities(BaseAgentTest):
    """Test utility functions."""
    
    def test_safe_json_operations(self):
        """Test JSON save and load operations."""
        from utils.common import safe_json_save, safe_json_load
        
        test_data = {"test": "data", "number": 42}
        test_file = os.path.join(self.test_temp_dir, "test.json")
        
        # Test save
        result = safe_json_save(test_data, test_file)
        self.assertTrue(result, "JSON save should succeed")
        self.assertTrue(os.path.exists(test_file), "JSON file should exist")
        
        # Test load
        loaded_data = safe_json_load(test_file)
        self.assertIsNotNone(loaded_data, "JSON load should not return None")
        self.assertEqual(loaded_data, test_data, "Loaded data should match saved data")
    
    def test_validation_functions(self):
        """Test input validation functions."""
        from utils.common import validate_language, validate_sentiment, validate_platform
        
        # Valid inputs
        self.assertTrue(validate_language('en'))
        self.assertTrue(validate_sentiment('neutral'))
        self.assertTrue(validate_platform('twitter'))
        
        # Invalid inputs
        self.assertFalse(validate_language('invalid'))
        self.assertFalse(validate_sentiment('invalid'))
        self.assertFalse(validate_platform('invalid'))


class TestConfiguration(BaseAgentTest):
    """Test configuration management."""
    
    def test_config_initialization(self):
        """Test that configuration initializes correctly."""
        self.assertIsNotNone(self.config)
        self.assertIsNotNone(self.config.directories)
        self.assertIsNotNone(self.config.agents)
        self.assertIsNotNone(self.config.security)
    
    def test_directory_creation(self):
        """Test that configuration creates required directories."""
        # This is already tested in the setup, but verify explicitly
        required_dirs = [
            self.config.directories.logs_dir,
            self.config.directories.content_dir,
            self.config.directories.raw_dir,
        ]
        
        for dir_path in required_dirs:
            full_path = self.config.get_absolute_path(dir_path)
            self.assertTrue(
                full_path.exists(),
                f"Directory should exist: {full_path}"
            )


if __name__ == '__main__':
    # Run tests
    unittest.main(verbosity=2)