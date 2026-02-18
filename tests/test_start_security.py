import unittest
from unittest.mock import patch, MagicMock
import sys
import os
import platform

# Add root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import start

class TestStartScriptSecurity(unittest.TestCase):
    @patch('subprocess.check_call')
    @patch('pathlib.Path.exists')
    def test_check_frontend_setup_no_shell_injection(self, mock_exists, mock_check_call):
        # Simulate node_modules missing
        mock_exists.return_value = False

        start.check_frontend_setup()

        # Verify check_call was called
        self.assertTrue(mock_check_call.called, "subprocess.check_call was not called")

        args, kwargs = mock_check_call.call_args
        command = args[0]

        # Verify command is a list
        self.assertIsInstance(command, list, f"Command should be a list, got {type(command)}")

        # Verify command executable
        self.assertIn(command[0], ["npm", "npm.cmd"], f"Command should start with npm or npm.cmd, got {command[0]}")

        # Verify arguments
        self.assertEqual(command[1], "install", "Command should be ['npm', 'install']")

        # Verify shell=False (default) or explicitly False
        self.assertFalse(kwargs.get('shell', False), "shell=True should not be used")

    @patch('subprocess.Popen')
    def test_main_frontend_start_no_shell_injection(self, mock_popen):
        # We need to mock check_frontend_setup to avoid side effects
        with patch('start.check_frontend_setup'):

            mock_process = MagicMock()
            mock_process.wait.return_value = None
            mock_popen.return_value = mock_process

            start.main()

            found_frontend = False
            for call in mock_popen.call_args_list:
                args, kwargs = call
                cmd = args[0]

                # Check if this is the frontend command
                is_frontend = False
                if isinstance(cmd, list) and len(cmd) > 0 and cmd[0] in ["npm", "npm.cmd"]:
                    is_frontend = True
                elif isinstance(cmd, str) and "npm" in cmd:
                    is_frontend = True # Should fail later if string

                if is_frontend:
                    found_frontend = True
                    self.assertIsInstance(cmd, list, f"Frontend command should be a list, got {type(cmd)}")
                    self.assertFalse(kwargs.get('shell', False), "shell=True should not be used for frontend")
                    self.assertEqual(cmd[1:], ["run", "dev"], "Frontend command args should be ['run', 'dev']")

            self.assertTrue(found_frontend, "Frontend start command not found in Popen calls")

if __name__ == '__main__':
    unittest.main()
