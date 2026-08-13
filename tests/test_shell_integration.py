import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from mydirs.mydirscontroller import MyDirsController


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class MyDirsShellIntegrationTest(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.original_cwd = os.getcwd()
        self.previous_directory = os.environ.get('MYDIRS_DIRECTORY')
        self.previous_db = os.environ.get('MYDIRS_DB')
        os.environ['MYDIRS_DIRECTORY'] = str(PROJECT_ROOT / 'src')
        os.environ['MYDIRS_DB'] = os.path.join(self.tmpdir.name, 'db')
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

    def environment(self):
        environment = os.environ.copy()
        python_path = str(PROJECT_ROOT / 'src' / 'python')
        if environment.get('PYTHONPATH'):
            python_path += os.pathsep + environment['PYTHONPATH']
        environment['PYTHONPATH'] = python_path
        return environment

    def save(self, alias, name):
        path = os.path.join(self.tmpdir.name, name)
        os.makedirs(path)
        os.chdir(path)
        self.controller.save([alias], {})
        return os.getcwd()

    def test_bash_completion_preserves_space_and_unicode_alias(self):
        self.save('meus projetos_日本語', 'completion target')
        result = subprocess.run(
            [
                'bash', '--noprofile', '--norc', '-c',
                'source "$1"; '
                'COMP_WORDS=(mydirs --open "meus"); COMP_CWORD=2; '
                '_mydirs; printf "<%s>\\n" "${COMPREPLY[@]}"',
                'bash', str(PROJECT_ROOT / 'src' / 'autocompletion_mydirs.sh'),
            ],
            env=self.environment(),
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.stdout.splitlines(), ['<meus projetos_日本語>'])

    def test_completion_and_help_expose_new_and_legacy_commands(self):
        result = subprocess.run(
            [
                'bash', '--noprofile', '--norc', '-c',
                'source "$1"; COMP_WORDS=(mydirs --); COMP_CWORD=1; '
                '_mydirs; printf "%s\\n" "${COMPREPLY[@]}"',
                'bash', str(PROJECT_ROOT / 'src' / 'autocompletion_mydirs.sh'),
            ],
            env=self.environment(),
            check=True,
            capture_output=True,
            text=True,
        )
        for option in ('--open', '--rank', '--doctor', '--repair-moved'):
            self.assertIn(option, result.stdout.splitlines())

        help_result = subprocess.run(
            ['python3', '-m', 'mydirs', '--help'],
            env=self.environment(),
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertIn('--doctor', help_result.stdout)
        self.assertIn('--repair-moved', help_result.stdout)

    @unittest.skipUnless(shutil.which('zsh'), 'zsh is not installed')
    def test_zsh_wrapper_opens_space_and_unicode_path(self):
        target = self.save('zsh alias_日本語', 'zsh target with spaces — ação')
        start = os.path.join(self.tmpdir.name, 'zsh start')
        os.makedirs(start)
        result = subprocess.run(
            [
                'zsh', '-f', '-c',
                'source "$1" --open "$2"; printf "__PWD__%s\\n" "$PWD"',
                'zsh', str(PROJECT_ROOT / 'src' / 'mydirs.sh'),
                'zsh alias_日本語',
            ],
            cwd=start,
            env=self.environment(),
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertIn('__PWD__' + target, result.stdout.splitlines())

    def test_failed_shell_navigation_does_not_record_usage_or_history(self):
        target = self.save('deleted', 'deleted before jump')
        start = os.path.join(self.tmpdir.name, 'failed start')
        os.makedirs(start)
        os.rmdir(target)
        result = subprocess.run(
            [
                'bash', '--noprofile', '--norc', '-c',
                'source "$1" --open deleted',
                'bash', str(PROJECT_ROOT / 'src' / 'mydirs.sh'),
            ],
            cwd=start,
            env=self.environment(),
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.controller.dao.alias('deleted')[3], 0)
        self.assertEqual(self.controller.read_history_entries(), [])

    def test_installer_is_idempotent_and_profile_loads(self):
        profile = os.path.join(self.tmpdir.name, 'profile with spaces')
        environment = self.environment()
        environment['MYDIRS_PROFILE'] = profile
        for _ in range(2):
            subprocess.run(
                ['bash', str(PROJECT_ROOT / 'install.sh')],
                env=environment,
                check=True,
                capture_output=True,
                text=True,
            )
        with open(profile, 'r', encoding='utf-8') as handler:
            profile_text = handler.read()
        self.assertEqual(profile_text.count('# MyDirs managed setup'), 1)
        result = subprocess.run(
            [
                'bash', '--noprofile', '--norc', '-c',
                'shopt -s expand_aliases; source "$1"; eval "mydirs --help"',
                'bash', profile,
            ],
            env=environment,
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertIn('mydirs - bookmark directories', result.stdout)

    def test_shell_files_pass_bash_and_zsh_syntax_checks(self):
        shell_files = [
            PROJECT_ROOT / 'install.sh',
            PROJECT_ROOT / 'src' / 'bashrc.sh',
            PROJECT_ROOT / 'src' / 'mydirs.sh',
            PROJECT_ROOT / 'src' / 'autocompletion_mydirs.sh',
        ]
        subprocess.run(
            ['bash', '-n', *map(str, shell_files)],
            check=True,
            capture_output=True,
            text=True,
        )
        if shutil.which('zsh'):
            # Bash completion is intentionally Bash-only, but it should still
            # parse cleanly when repositories are inspected from Zsh.
            subprocess.run(
                ['zsh', '-n', *map(str, shell_files)],
                check=True,
                capture_output=True,
                text=True,
            )


if __name__ == '__main__':
    unittest.main()
