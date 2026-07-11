import contextlib
import io
import os
import tempfile
import unittest

from mydirs.mydirscontroller import MyDirsController


class MyDirsHistoryTest(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.previous_mydirs_directory = os.environ.get('MYDIRS_DIRECTORY')
        self.previous_mydirs_db = os.environ.get('MYDIRS_DB')
        os.environ['MYDIRS_DIRECTORY'] = self.tmpdir.name
        os.environ['MYDIRS_DB'] = self.tmpdir.name + os.sep
        self.controller = MyDirsController()

    def tearDown(self):
        self.controller.finish()
        if self.previous_mydirs_directory is None:
            os.environ.pop('MYDIRS_DIRECTORY', None)
        else:
            os.environ['MYDIRS_DIRECTORY'] = self.previous_mydirs_directory

        if self.previous_mydirs_db is None:
            os.environ.pop('MYDIRS_DB', None)
        else:
            os.environ['MYDIRS_DB'] = self.previous_mydirs_db

        self.tmpdir.cleanup()

    def test_save_history_preserves_paths_with_shell_metacharacters(self):
        path = os.path.join(self.tmpdir.name, 'dir with spaces "and quotes"')

        self.controller.save_history(path)

        self.assertEqual(self.controller.read_history_entries(), [path])

    def test_save_history_does_not_duplicate_consecutive_paths(self):
        path = os.path.join(self.tmpdir.name, 'same path')

        self.controller.save_history(path)
        self.controller.save_history(path)

        self.assertEqual(self.controller.read_history_entries(), [path])

    def test_show_history_prints_newest_entries_first(self):
        first_path = os.path.join(self.tmpdir.name, 'first')
        second_path = os.path.join(self.tmpdir.name, 'second')
        third_path = os.path.join(self.tmpdir.name, 'third')
        self.controller.write_history_entries([first_path, second_path, third_path])

        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.controller.show_history(['2'], {})

        self.assertEqual(output.getvalue().splitlines(), [third_path, second_path])

    def test_go_back_skips_current_directory_entries(self):
        current_path = self.tmpdir.name
        previous_path = os.path.join(self.tmpdir.name, 'previous path')
        self.controller.write_history_entries([previous_path, current_path])

        output = io.StringIO()
        old_cwd = os.getcwd()
        try:
            os.chdir(current_path)
            with contextlib.redirect_stdout(output):
                self.controller.go_back([], {})
        finally:
            os.chdir(old_cwd)

        self.assertEqual(output.getvalue().strip(), previous_path)
        self.assertEqual(self.controller.read_history_entries(), [])


if __name__ == '__main__':
    unittest.main()
