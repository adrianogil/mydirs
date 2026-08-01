import contextlib
import io
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import tempfile
import unittest

from mydirs.mydirscontroller import MyDirsController


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class MyDirsPathSafetyTest(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.original_cwd = os.getcwd()
        self.previous_mydirs_directory = os.environ.get('MYDIRS_DIRECTORY')
        self.previous_mydirs_db = os.environ.get('MYDIRS_DB')

        self.db_directory = os.path.join(self.tmpdir.name, 'database')
        os.environ['MYDIRS_DIRECTORY'] = self.tmpdir.name
        os.environ['MYDIRS_DB'] = self.db_directory
        self.controller = MyDirsController()

    def tearDown(self):
        os.chdir(self.original_cwd)
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

    def shell_environment(self):
        environment = os.environ.copy()
        python_path = str(PROJECT_ROOT / 'src' / 'python')
        if environment.get('PYTHONPATH'):
            python_path += os.pathsep + environment['PYTHONPATH']
        environment['PYTHONPATH'] = python_path
        return environment

    def run_wrapper(self, arguments, cwd):
        return subprocess.run(
            [
                'bash',
                '--noprofile',
                '--norc',
                '-c',
                'source "$1" "${@:2}"; printf "__PWD__%s\\n" "$PWD"',
                'bash',
                str(PROJECT_ROOT / 'src' / 'mydirs.sh'),
                *arguments,
            ],
            cwd=cwd,
            env=self.shell_environment(),
            check=True,
            capture_output=True,
            text=True,
        )

    def assert_wrapper_pwd(self, result, expected_path):
        pwd_lines = [
            line.removeprefix('__PWD__')
            for line in result.stdout.splitlines()
            if line.startswith('__PWD__')
        ]
        self.assertEqual(pwd_lines, [expected_path])

    def test_data_files_are_joined_to_db_directory(self):
        self.assertEqual(
            self.controller.db_file,
            os.path.join(self.db_directory, 'mydirs.sqlite'),
        )
        self.assertEqual(
            self.controller.history_file,
            os.path.join(self.db_directory, 'mydirs.history'),
        )
        self.assertEqual(
            self.controller.json_stats_filepath,
            os.path.join(self.db_directory, 'mydirs_stats.json'),
        )

    def test_alias_wildcards_are_matched_literally(self):
        aliases_and_paths = [
            ('project-one', 'ordinary percent match'),
            ('project%', 'literal percent alias'),
            ('fileXname', 'ordinary underscore match'),
            ('file_name', 'literal underscore alias'),
        ]
        expected_paths = {}

        for path_alias, directory_name in aliases_and_paths:
            directory = os.path.join(self.tmpdir.name, directory_name)
            os.makedirs(directory)
            os.chdir(directory)
            expected_paths[path_alias] = os.getcwd()
            self.controller.save([path_alias], {})

        self.controller.c.execute(
            'SELECT path_key, path FROM PathByKey ORDER BY path_key',
        )
        self.assertEqual(dict(self.controller.c.fetchall()), expected_paths)

        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.controller.path(['project%'], {})
        self.assertEqual(output.getvalue().strip(), expected_paths['project%'])

    def test_alias_identity_is_case_sensitive(self):
        aliases_and_directories = (
            ('Work', 'uppercase alias path'),
            ('work', 'lowercase alias path'),
        )
        for path_alias, directory_name in aliases_and_directories:
            directory = os.path.join(self.tmpdir.name, directory_name)
            os.makedirs(directory)
            os.chdir(directory)
            self.controller.save([path_alias], {})

        self.controller.c.execute(
            'SELECT path_key FROM PathByKey ORDER BY path_key COLLATE BINARY',
        )
        self.assertEqual(
            [row[0] for row in self.controller.c.fetchall()],
            ['Work', 'work'],
        )

    def test_database_rejects_duplicate_aliases(self):
        os.chdir(self.tmpdir.name)
        self.controller.save(['unique-alias'], {})

        try:
            with self.assertRaises(sqlite3.IntegrityError):
                self.controller.c.execute(
                    'INSERT INTO PathByKey (path, path_key) VALUES (?, ?)',
                    ('/another/path', 'unique-alias'),
                )
        finally:
            self.controller.conn.rollback()

    def test_existing_database_receives_unique_alias_index(self):
        legacy_directory = os.path.join(self.tmpdir.name, 'legacy database')
        legacy_db_file = os.path.join(legacy_directory, 'mydirs.sqlite')
        os.makedirs(legacy_directory)
        with sqlite3.connect(legacy_db_file) as connection:
            connection.execute('''
                CREATE TABLE PathByKey (
                    id_pathbykey INTEGER PRIMARY KEY,
                    path TEXT,
                    path_key TEXT
                )
            ''')
            connection.execute(
                'INSERT INTO PathByKey (path, path_key) VALUES (?, ?)',
                ('/original/path', 'legacy-alias'),
            )

        original_db_directory = os.environ['MYDIRS_DB']
        os.environ['MYDIRS_DB'] = legacy_directory
        legacy_controller = MyDirsController()
        try:
            with self.assertRaises(sqlite3.IntegrityError):
                legacy_controller.c.execute(
                    'INSERT INTO PathByKey (path, path_key) VALUES (?, ?)',
                    ('/duplicate/path', 'legacy-alias'),
                )
        finally:
            legacy_controller.conn.rollback()
            legacy_controller.finish()
            legacy_controller.conn.close()
            os.environ['MYDIRS_DB'] = original_db_directory

    def test_save_list_and_open_preserve_path_with_spaces_and_unicode(self):
        saved_path = os.path.join(
            self.tmpdir.name,
            'projetos com espaços',
            'ação_日本語',
        )
        starting_path = os.path.join(self.tmpdir.name, 'diretório inicial')
        os.makedirs(saved_path)
        os.makedirs(starting_path)

        os.chdir(saved_path)
        saved_cwd = os.getcwd()
        self.controller.save(['unicode-path'], {})

        list_output = io.StringIO()
        with contextlib.redirect_stdout(list_output):
            self.controller.list([], {})

        os.chdir(starting_path)
        starting_cwd = os.getcwd()
        open_output = io.StringIO()
        with contextlib.redirect_stdout(open_output):
            self.controller.open(['unicode-path'], {})

        self.assertEqual(
            list_output.getvalue().splitlines(),
            ['unicode-path:' + saved_cwd],
        )
        self.assertEqual(open_output.getvalue().splitlines(), [saved_cwd])
        self.assertEqual(
            self.controller.read_history_entries(),
            [starting_cwd, saved_cwd],
        )

    def test_shell_wrapper_changes_to_literal_space_and_unicode_path(self):
        saved_path = os.path.join(
            self.tmpdir.name,
            'destino com espaços; $(touch invadido) — 東京',
        )
        starting_path = os.path.join(self.tmpdir.name, 'origem segura')
        unexpected_file = os.path.join(starting_path, 'invadido')
        os.makedirs(saved_path)
        os.makedirs(starting_path)

        os.chdir(saved_path)
        saved_cwd = os.getcwd()
        self.controller.save(['shell-safe'], {})
        os.chdir(starting_path)

        result = self.run_wrapper(['--open', 'shell-safe'], starting_path)

        self.assert_wrapper_pwd(result, saved_cwd)
        self.assertFalse(os.path.exists(unexpected_file))

    def test_shell_wrapper_opens_alias_with_spaces_and_unicode(self):
        saved_path = os.path.join(self.tmpdir.name, 'destino salvo')
        starting_path = os.path.join(self.tmpdir.name, 'origem')
        path_alias = 'meus projetos_日本語'
        os.makedirs(saved_path)
        os.makedirs(starting_path)

        os.chdir(saved_path)
        saved_cwd = os.getcwd()
        self.controller.save([path_alias], {})
        os.chdir(starting_path)

        result = self.run_wrapper(['--open', path_alias], starting_path)

        self.assert_wrapper_pwd(result, saved_cwd)

    def test_shell_wrapper_goes_back_to_space_and_unicode_path(self):
        previous_path = os.path.join(
            self.tmpdir.name,
            'anterior com espaços; $(touch invadido) — 東京',
        )
        current_path = os.path.join(self.tmpdir.name, 'diretório atual')
        unexpected_file = os.path.join(current_path, 'invadido')
        os.makedirs(previous_path)
        os.makedirs(current_path)

        os.chdir(previous_path)
        previous_cwd = os.getcwd()
        os.chdir(current_path)
        current_cwd = os.getcwd()
        self.controller.write_history_entries([previous_cwd, current_cwd])

        result = self.run_wrapper(['--back'], current_path)

        self.assert_wrapper_pwd(result, previous_cwd)
        self.assertEqual(self.controller.read_history_entries(), [])
        self.assertFalse(os.path.exists(unexpected_file))

    def test_bashrc_loads_from_space_and_unicode_install_path(self):
        install_directory = os.path.join(
            self.tmpdir.name,
            'instalação do mydirs_日本語',
        )
        shutil.copytree(PROJECT_ROOT / 'src', install_directory)

        environment = self.shell_environment()
        environment['MYDIRS_DIRECTORY'] = install_directory
        environment.pop('MYDIRS_PYTHON_PATH', None)
        environment.pop('PYTHONPATH', None)

        result = subprocess.run(
            [
                'bash',
                '--noprofile',
                '--norc',
                '-c',
                'set -e; shopt -s expand_aliases; '
                'source "$1/bashrc.sh"; eval "mydirs --help"',
                'bash',
                install_directory,
            ],
            env=environment,
            check=True,
            capture_output=True,
            text=True,
        )

        self.assertIn('mydirs - bookmark directories', result.stdout)


if __name__ == '__main__':
    unittest.main()
