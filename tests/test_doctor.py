import contextlib
import errno
import io
import os
import tempfile
import unittest
from unittest import mock

from mydirs.mydirscontroller import MyDirsController


class MyDirsDoctorTest(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.original_cwd = os.getcwd()
        self.previous_directory = os.environ.get('MYDIRS_DIRECTORY')
        self.previous_db = os.environ.get('MYDIRS_DB')
        os.environ['MYDIRS_DIRECTORY'] = self.tmpdir.name
        os.environ['MYDIRS_DB'] = os.path.join(self.tmpdir.name, 'database')
        self.controller = MyDirsController(clock=lambda: 2_000_000_000)

    def tearDown(self):
        os.chdir(self.original_cwd)
        self.controller.finish()
        if self.previous_directory is None:
            os.environ.pop('MYDIRS_DIRECTORY', None)
        else:
            os.environ['MYDIRS_DIRECTORY'] = self.previous_directory
        if self.previous_db is None:
            os.environ.pop('MYDIRS_DB', None)
        else:
            os.environ['MYDIRS_DB'] = self.previous_db
        self.tmpdir.cleanup()

    def save(self, alias, path):
        os.makedirs(path, exist_ok=True)
        os.chdir(path)
        self.controller.save([alias], {})
        return os.getcwd()

    def findings_by_alias(self):
        return {
            finding['alias']: finding
            for finding in self.controller.doctor_records()
        }

    def test_classifies_missing_and_inaccessible_separately(self):
        missing = os.path.join(self.tmpdir.name, 'deleted directory')
        inaccessible = os.path.join(self.tmpdir.name, 'private directory')
        missing = self.save('missing', missing)
        inaccessible = self.save('private', inaccessible)
        os.chdir(self.tmpdir.name)
        os.rmdir(missing)

        real_stat = os.stat

        def controlled_stat(path, *args, **kwargs):
            if path == inaccessible:
                raise PermissionError(errno.EACCES, 'Permission denied', path)
            return real_stat(path, *args, **kwargs)

        with mock.patch('mydirs.mydirscontroller.os.stat', controlled_stat):
            findings = self.findings_by_alias()

        self.assertEqual(findings['missing']['status'], 'missing')
        self.assertEqual(findings['private']['status'], 'inaccessible')

    def test_symlink_and_target_are_duplicate_directory_records(self):
        target = os.path.join(self.tmpdir.name, 'real directory')
        link = os.path.join(self.tmpdir.name, 'linked directory')
        self.save('real', target)
        os.symlink(target, link)
        os.chdir(link)
        self.controller.save(['symlink'], {})

        findings = self.findings_by_alias()

        self.assertEqual(findings['real']['status'], 'ok')
        self.assertEqual(findings['symlink']['status'], 'duplicate')
        self.assertEqual(findings['symlink']['duplicate_of'], 'real')

    def test_existing_file_is_not_reported_as_a_directory(self):
        path = os.path.join(self.tmpdir.name, 'was a directory')
        self.save('file', path)
        os.chdir(self.tmpdir.name)
        os.rmdir(path)
        with open(path, 'w', encoding='utf-8') as handler:
            handler.write('not a directory')

        self.assertEqual(
            self.findings_by_alias()['file']['status'], 'not-directory'
        )

    def test_rename_produces_conservative_identity_suggestion_without_mutation(self):
        old_path = os.path.join(self.tmpdir.name, 'old folder — ação')
        new_path = os.path.join(self.tmpdir.name, 'new folder — 東京')
        stored_old_path = self.save('moved alias', old_path)
        with self.controller.conn:
            self.controller.conn.execute('''
                UPDATE PathByKey SET usage_count = 4, last_used_at = ?
                WHERE path_key = ?
            ''', (2_000_000_000, 'moved alias'))
        os.chdir(self.tmpdir.name)
        os.rename(old_path, new_path)

        finding = self.findings_by_alias()['moved alias']

        self.assertEqual(finding['status'], 'moved')
        self.assertEqual(finding['suggestions'], [os.path.realpath(new_path)])
        self.assertEqual(
            self.controller.dao.alias('moved alias')[1], stored_old_path
        )

        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.controller.repair_moved(['moved alias', new_path], {})
        repaired = self.controller.dao.alias('moved alias')
        self.assertEqual(repaired[1], new_path)
        self.assertEqual(repaired[3:5], (4, 2_000_000_000))

    def test_repair_rejects_unrelated_directory(self):
        old_path = os.path.join(self.tmpdir.name, 'old')
        unrelated = os.path.join(self.tmpdir.name, 'unrelated')
        stored_old_path = self.save('old', old_path)
        os.makedirs(unrelated)
        os.chdir(self.tmpdir.name)
        os.rmdir(old_path)

        with self.assertRaisesRegex(ValueError, 'does not match'):
            self.controller.repair_moved(['old', unrelated], {})
        self.assertEqual(self.controller.dao.alias('old')[1], stored_old_path)

    def test_repair_rejects_inaccessible_target(self):
        old_path = os.path.join(self.tmpdir.name, 'old inaccessible')
        new_path = os.path.join(self.tmpdir.name, 'new inaccessible')
        self.save('private', old_path)
        os.chdir(self.tmpdir.name)
        os.rename(old_path, new_path)

        with mock.patch(
            'mydirs.mydirscontroller.os.access', return_value=False
        ):
            with self.assertRaisesRegex(ValueError, 'cannot be read or entered'):
                self.controller.repair_moved(['private', new_path], {})

    def test_doctor_cli_is_read_only_and_reports_healthy_database(self):
        path = os.path.join(self.tmpdir.name, 'healthy')
        self.save('healthy', path)
        before = self.controller.dao.alias('healthy')
        output = io.StringIO()

        with contextlib.redirect_stdout(output):
            self.controller.doctor([], {})

        self.assertIn('OK no stale', output.getvalue())
        self.assertEqual(self.controller.dao.alias('healthy'), before)


if __name__ == '__main__':
    unittest.main()
