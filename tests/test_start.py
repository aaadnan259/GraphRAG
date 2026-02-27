import unittest
from unittest.mock import patch, MagicMock, call
import sys
import os
import subprocess
import platform
from pathlib import Path

# Add root to sys.path so we can import start.py
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import start

class TestStartScript(unittest.TestCase):

    @patch('start.log')
    @patch('sys.exit')
    @patch('subprocess.check_call')
    @patch('pathlib.Path.exists')
    def test_check_frontend_setup_failure(self, mock_exists, mock_check_call, mock_exit, mock_log):
        # Simulate node_modules missing
        mock_exists.return_value = False
        # Simulate subprocess failure
        mock_check_call.side_effect = subprocess.CalledProcessError(1, 'npm install')

        start.check_frontend_setup()

        # Verify check_call was called
        mock_check_call.assert_called_once()

        # Verify error log
        mock_log.assert_any_call("Failed to install frontend dependencies.", "ERROR")

        # Verify sys.exit(1) was called
        mock_exit.assert_called_once_with(1)

    @patch('start.log')
    @patch('sys.exit')
    @patch('subprocess.check_call')
    @patch('pathlib.Path.exists')
    def test_check_frontend_setup_success(self, mock_exists, mock_check_call, mock_exit, mock_log):
        # Simulate node_modules missing
        mock_exists.return_value = False
        # Simulate subprocess success (default)

        start.check_frontend_setup()

        # Verify check_call was called
        mock_check_call.assert_called_once()

        # Verify success log
        mock_log.assert_any_call("Frontend dependencies installed.", "SUCCESS")

        # Verify sys.exit was NOT called
        mock_exit.assert_not_called()

    @patch('start.log')
    @patch('sys.exit')
    @patch('subprocess.check_call')
    @patch('pathlib.Path.exists')
    def test_check_frontend_setup_already_installed(self, mock_exists, mock_check_call, mock_exit, mock_log):
        # Simulate node_modules already exists
        mock_exists.return_value = True

        start.check_frontend_setup()

        # Verify check_call was NOT called
        mock_check_call.assert_not_called()

        # Verify info log
        mock_log.assert_called_once_with("Frontend dependencies found.", "INFO")

        # Verify sys.exit was NOT called
        mock_exit.assert_not_called()

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
