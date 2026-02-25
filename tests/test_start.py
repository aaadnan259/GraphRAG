import unittest
from unittest.mock import patch
import sys
import os
import platform

# Add root to sys.path so we can import start.py
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import start

class TestStartScript(unittest.TestCase):
    @patch('platform.system')
    def test_get_npm_command_windows(self, mock_system):
        """Test that get_npm_command returns ['npm.cmd'] on Windows."""
        mock_system.return_value = "Windows"
        expected_command = ["npm.cmd"]

        actual_command = start.get_npm_command()

        self.assertEqual(actual_command, expected_command)

    @patch('platform.system')
    def test_get_npm_command_non_windows(self, mock_system):
        """Test that get_npm_command returns ['npm'] on non-Windows platforms."""
        # Test Linux
        mock_system.return_value = "Linux"
        expected_command = ["npm"]
        actual_command = start.get_npm_command()
        self.assertEqual(actual_command, expected_command)

        # Test Darwin (macOS)
        mock_system.return_value = "Darwin"
        expected_command = ["npm"]
        actual_command = start.get_npm_command()
        self.assertEqual(actual_command, expected_command)

if __name__ == '__main__':
    unittest.main()
