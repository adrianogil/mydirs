import contextlib
import io
import json
import os
import tempfile
import threading
import unittest

from mydirs.mydirscontroller import (
    HISTORY_BACKUP_FORMAT,
    HISTORY_BACKUP_VERSION,
    MyDirsController,
)


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

    def test_concurrent_navigation_history_keeps_source_target_pairs(self):
        controllers = [self.controller]
        controllers.extend(MyDirsController() for _ in range(3))
        errors = []

        def record(controller, index):
            try:
                controller.save_navigation(
                    os.path.join(self.tmpdir.name, 'source %d' % index),
                    os.path.join(self.tmpdir.name, 'target %d' % index),
                )
            except BaseException as error:
                errors.append(error)

        threads = [
            threading.Thread(target=record, args=(controller, index))
            for index, controller in enumerate(controllers)
        ]
        try:
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join()
        finally:
            for controller in controllers[1:]:
                controller.finish()

        entries = self.controller.read_history_entries()
        self.assertEqual(errors, [])
        self.assertEqual(len(entries), 8)
        for index in range(4):
            source = os.path.join(self.tmpdir.name, 'source %d' % index)
            target = os.path.join(self.tmpdir.name, 'target %d' % index)
            self.assertEqual(entries[entries.index(source) + 1], target)

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

    def test_export_history_writes_versioned_json_shape(self):
        entries = [
            os.path.join(self.tmpdir.name, 'first path'),
            os.path.join(self.tmpdir.name, 'café'),
        ]
        backup_path = os.path.join(self.tmpdir.name, 'history backup.json')
        self.controller.write_history_entries(entries)

        with contextlib.redirect_stdout(io.StringIO()):
            self.controller.export_history([backup_path], {})

        with open(backup_path, 'r', encoding='utf-8') as backup_handler:
            backup = json.load(backup_handler)

        self.assertEqual(backup, {
            'format': HISTORY_BACKUP_FORMAT,
            'version': HISTORY_BACKUP_VERSION,
            'entries': entries,
        })

    def test_import_history_round_trip_restores_entries(self):
        entries = [
            os.path.join(self.tmpdir.name, 'first'),
            os.path.join(self.tmpdir.name, 'second'),
            os.path.join(self.tmpdir.name, 'first'),
        ]
        backup_path = os.path.join(self.tmpdir.name, 'history.json')
        self.controller.write_history_entries(entries)
        with contextlib.redirect_stdout(io.StringIO()):
            self.controller.export_history([backup_path], {})

        self.controller.write_history_entries([
            os.path.join(self.tmpdir.name, 'new local entry'),
        ])
        with contextlib.redirect_stdout(io.StringIO()):
            self.controller.import_history([backup_path], {})

        self.assertEqual(self.controller.read_history_entries(), entries)

    def test_import_history_rejects_malformed_json_without_changing_history(self):
        original_entries = [os.path.join(self.tmpdir.name, 'existing')]
        backup_path = os.path.join(self.tmpdir.name, 'malformed.json')
        self.controller.write_history_entries(original_entries)
        with open(backup_path, 'w', encoding='utf-8') as backup_handler:
            backup_handler.write('{"format": "mydirs-history",')

        with self.assertRaisesRegex(ValueError, 'invalid history backup JSON'):
            self.controller.import_history([backup_path], {})

        self.assertEqual(
            self.controller.read_history_entries(),
            original_entries,
        )

    def test_import_history_rejects_invalid_entries_without_changing_history(self):
        original_entries = [os.path.join(self.tmpdir.name, 'existing')]
        backup_path = os.path.join(self.tmpdir.name, 'invalid-entry.json')
        self.controller.write_history_entries(original_entries)
        with open(backup_path, 'w', encoding='utf-8') as backup_handler:
            json.dump({
                'format': HISTORY_BACKUP_FORMAT,
                'version': HISTORY_BACKUP_VERSION,
                'entries': [os.path.join(self.tmpdir.name, 'valid'), 42],
            }, backup_handler)

        with self.assertRaisesRegex(ValueError, 'only strings'):
            self.controller.import_history([backup_path], {})

        self.assertEqual(
            self.controller.read_history_entries(),
            original_entries,
        )

    def test_import_history_collapses_only_consecutive_duplicates(self):
        first_path = os.path.join(self.tmpdir.name, 'first')
        second_path = os.path.join(self.tmpdir.name, 'second')
        backup_path = os.path.join(self.tmpdir.name, 'duplicates.json')
        with open(backup_path, 'w', encoding='utf-8') as backup_handler:
            json.dump({
                'format': HISTORY_BACKUP_FORMAT,
                'version': HISTORY_BACKUP_VERSION,
                'entries': [first_path, first_path, second_path, first_path],
            }, backup_handler)

        with contextlib.redirect_stdout(io.StringIO()):
            self.controller.import_history([backup_path], {})

        self.assertEqual(
            self.controller.read_history_entries(),
            [first_path, second_path, first_path],
        )


if __name__ == '__main__':
    unittest.main()
