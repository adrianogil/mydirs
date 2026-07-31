import contextlib
import io
import os
from pathlib import Path
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
        os.environ['MYDIRS_DB'] = self.db_directory + os.sep
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

        environment = os.environ.copy()
        python_path = str(PROJECT_ROOT / 'src' / 'python')
        if environment.get('PYTHONPATH'):
            python_path += os.pathsep + environment['PYTHONPATH']
        environment['PYTHONPATH'] = python_path

        result = subprocess.run(
            [
                'bash',
                '--noprofile',
                '--norc',
                '-c',
                'source "$1" --open "$2"; printf "__PWD__%s\\n" "$PWD"',
                'bash',
                str(PROJECT_ROOT / 'src' / 'mydirs.sh'),
                'shell-safe',
            ],
            cwd=starting_path,
            env=environment,
            check=True,
            capture_output=True,
            text=True,
        )

        pwd_lines = [
            line.removeprefix('__PWD__')
            for line in result.stdout.splitlines()
            if line.startswith('__PWD__')
        ]
        self.assertEqual(pwd_lines, [saved_cwd])
        self.assertFalse(os.path.exists(unexpected_file))


if __name__ == '__main__':
    unittest.main()
