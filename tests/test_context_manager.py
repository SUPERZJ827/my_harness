import os
import unittest
from contextlib import contextmanager
from src.utils import change_dir, change_metalog_path
from src.logs import create_logger

class TestContextManagers(unittest.TestCase):
    def test_change_dir(self):
        # Test changing to a valid directory
        with change_dir('/path/to/new/dir'):
            self.assertEqual(os.getcwd(), '/path/to/new/dir')

        # Test changing to an invalid directory
        with self.assertRaises(FileNotFoundError):
            with change_dir('/path/to/nonexistent/dir'):
                pass

        # Test changing back to the original directory
        original_dir = os.getcwd()
        with change_dir('/path/to/new/dir'):
            pass
        self.assertEqual(os.getcwd(), original_dir)

    def test_change_metalog_path(self):
        # Test changing the log file path
        logger, _, _ = create_logger()
        original_logfile = logger.logfile
        with change_metalog_path(logger, file_path='/path/to/new/logfile.log'):
            self.assertEqual(logger.logfile, '/path/to/new/logfile.log')

        # Test removing the log file path
        with change_metalog_path(logger):
            self.assertIsNone(logger.logfile)

        # Test changing the log levels
        with change_metalog_path(logger, print_level='DEBUG', logfile_level='INFO'):
            self.assertEqual(logger.level, 'DEBUG')
            self.assertEqual(logger.logfile_level, 'INFO')

        # Test removing the logger
        with change_metalog_path(logger):
            self.assertFalse(logger.is_enabled())

if __name__ == '__main__':
    unittest.main()