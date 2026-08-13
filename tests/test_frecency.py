import contextlib
import io
import json
import os
import sqlite3
import tempfile
import threading
import unittest

from mydirs.dao.mydirsdao import SCHEMA_VERSION
from mydirs.mydirscontroller import MyDirsController, SECONDS_PER_DAY


class MyDirsFrecencyTest(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.original_cwd = os.getcwd()
        self.previous_directory = os.environ.get('MYDIRS_DIRECTORY')
        self.previous_db = os.environ.get('MYDIRS_DB')
        os.environ['MYDIRS_DIRECTORY'] = self.tmpdir.name
        os.environ['MYDIRS_DB'] = os.path.join(self.tmpdir.name, 'db')
        self.now = 2_000_000_000
        self.controller = MyDirsController(clock=lambda: self.now)

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

    def add_alias(self, alias, directory_name=None):
        path = os.path.join(self.tmpdir.name, directory_name or alias)
        os.makedirs(path, exist_ok=True)
        os.chdir(path)
        self.controller.save([alias], {})
        return os.getcwd()

    def set_usage(self, alias, count, last_used_at):
        with self.controller.conn:
            self.controller.conn.execute('''
                UPDATE PathByKey SET usage_count = ?, last_used_at = ?
                WHERE path_key = ? COLLATE BINARY
            ''', (count, last_used_at, alias))

    def test_clock_controlled_formula_combines_count_and_recency(self):
        self.assertEqual(
            self.controller.frecency_score(1, self.now, self.now), 1000
        )
        self.assertEqual(
            self.controller.frecency_score(
                2, self.now - 30 * SECONDS_PER_DAY, self.now
            ),
            1000,
        )
        self.assertEqual(
            self.controller.frecency_score(99, None, self.now), 49500
        )
        self.assertEqual(
            self.controller.frecency_score(1, self.now + 100, self.now), 1000
        )

    def test_rank_is_stable_across_score_recency_count_and_binary_alias(self):
        for alias in ('recent', 'frequent', 'A', 'a', 'ação'):
            self.add_alias(alias)
        self.set_usage('recent', 2, self.now)
        self.set_usage('frequent', 11, self.now - 300 * SECONDS_PER_DAY)
        for alias in ('A', 'a', 'ação'):
            self.set_usage(alias, 1, self.now - SECONDS_PER_DAY)

        aliases = [row[2] for row in self.controller.ranked_aliases()]

        self.assertEqual(aliases, ['recent', 'frequent', 'A', 'a', 'ação'])

    def test_open_records_count_and_monotonic_timestamp_atomically(self):
        path = self.add_alias('work')
        os.chdir(self.tmpdir.name)
        with contextlib.redirect_stdout(io.StringIO()):
            self.controller.open(['work'], {})
        self.controller.record_open(['work', self.tmpdir.name, path], {})
        self.now -= 100
        with contextlib.redirect_stdout(io.StringIO()):
            self.controller.open(['work'], {})
        self.controller.record_open(['work', self.tmpdir.name, path], {})

        row = self.controller.dao.alias('work')
        self.assertEqual(row[1], path)
        self.assertEqual(row[3], 2)
        self.assertEqual(row[4], 2_000_000_000)

    def test_rank_and_autocomplete_are_ranked_and_list_stays_compatible(self):
        cold_path = self.add_alias('cold')
        hot_path = self.add_alias('hot')
        self.set_usage('cold', 1, self.now - 100 * SECONDS_PER_DAY)
        self.set_usage('hot', 1, self.now)

        list_output = io.StringIO()
        rank_output = io.StringIO()
        auto_output = io.StringIO()
        with contextlib.redirect_stdout(list_output):
            self.controller.list([], {})
        with contextlib.redirect_stdout(rank_output):
            self.controller.rank([], {})
        with contextlib.redirect_stdout(auto_output):
            self.controller.auto_list([], {})

        self.assertEqual(
            list_output.getvalue().splitlines(),
            ['cold:' + cold_path, 'hot:' + hot_path],
        )
        self.assertEqual(
            rank_output.getvalue().splitlines(),
            ['hot:' + hot_path, 'cold:' + cold_path],
        )
        self.assertEqual(auto_output.getvalue().splitlines(), ['hot', 'cold'])

    def test_concurrent_connections_do_not_lose_usage_increments(self):
        self.add_alias('shared')
        errors = []

        def increment_many():
            controller = None
            try:
                controller = MyDirsController(clock=lambda: self.now)
                for _ in range(40):
                    controller.dao.record_use('shared', self.now)
            except BaseException as error:
                errors.append(error)
            finally:
                if controller is not None:
                    controller.finish()

        threads = [threading.Thread(target=increment_many) for _ in range(4)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        self.assertEqual(errors, [])
        self.assertEqual(self.controller.dao.alias('shared')[3], 160)

    def test_update_preserves_alias_usage_metadata(self):
        self.add_alias('moving')
        self.set_usage('moving', 8, self.now)
        replacement = os.path.join(self.tmpdir.name, 'replacement')
        os.makedirs(replacement)
        os.chdir(replacement)

        with contextlib.redirect_stdout(io.StringIO()):
            self.controller.update(['moving'], {})

        row = self.controller.dao.alias('moving')
        self.assertEqual(row[1], os.getcwd())
        self.assertEqual(row[3:5], (8, self.now))


class MyDirsMigrationTest(unittest.TestCase):
    def test_legacy_database_and_json_stats_migrate_once(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_directory = os.path.join(tmpdir, 'legacy db')
            os.makedirs(db_directory)
            db_file = os.path.join(db_directory, 'mydirs.sqlite')
            path = os.path.join(tmpdir, 'café path')
            os.makedirs(path)
            with sqlite3.connect(db_file) as connection:
                connection.execute('''
                    CREATE TABLE PathByKey (
                        id_pathbykey INTEGER PRIMARY KEY,
                        path TEXT,
                        path_key TEXT
                    )
                ''')
                connection.execute(
                    'INSERT INTO PathByKey(path, path_key) VALUES (?, ?)',
                    (path, 'legacy'),
                )
            with open(
                os.path.join(db_directory, 'mydirs_stats.json'),
                'w',
                encoding='utf-8',
            ) as handler:
                json.dump({path: 7}, handler, ensure_ascii=False)

            previous_directory = os.environ.get('MYDIRS_DIRECTORY')
            previous_db = os.environ.get('MYDIRS_DB')
            os.environ['MYDIRS_DIRECTORY'] = tmpdir
            os.environ['MYDIRS_DB'] = db_directory
            first = MyDirsController()
            try:
                self.assertEqual(first.dao.alias('legacy')[3], 7)
                self.assertIsNone(first.dao.alias('legacy')[4])
                self.assertEqual(
                    first.conn.execute('PRAGMA user_version').fetchone()[0],
                    SCHEMA_VERSION,
                )
                with first.conn:
                    first.conn.execute(
                        'UPDATE PathByKey SET usage_count = 9 '
                        'WHERE path_key = ?',
                        ('legacy',),
                    )
            finally:
                first.finish()

            second = MyDirsController()
            try:
                self.assertEqual(second.dao.alias('legacy')[3], 9)
            finally:
                second.finish()
                if previous_directory is None:
                    os.environ.pop('MYDIRS_DIRECTORY', None)
                else:
                    os.environ['MYDIRS_DIRECTORY'] = previous_directory
                if previous_db is None:
                    os.environ.pop('MYDIRS_DB', None)
                else:
                    os.environ['MYDIRS_DB'] = previous_db

    def test_invalid_legacy_stats_do_not_block_legacy_database(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_directory = os.path.join(tmpdir, 'db')
            os.makedirs(db_directory)
            with sqlite3.connect(
                os.path.join(db_directory, 'mydirs.sqlite')
            ) as connection:
                connection.execute('''
                    CREATE TABLE PathByKey (
                        id_pathbykey INTEGER PRIMARY KEY,
                        path TEXT,
                        path_key TEXT
                    )
                ''')
                connection.execute(
                    'INSERT INTO PathByKey(path, path_key) VALUES (?, ?)',
                    (tmpdir, 'legacy'),
                )
            with open(
                os.path.join(db_directory, 'mydirs_stats.json'),
                'w', encoding='utf-8'
            ) as handler:
                handler.write('{invalid JSON')

            previous_directory = os.environ.get('MYDIRS_DIRECTORY')
            previous_db = os.environ.get('MYDIRS_DB')
            os.environ['MYDIRS_DIRECTORY'] = tmpdir
            os.environ['MYDIRS_DB'] = db_directory
            controller = MyDirsController()
            try:
                self.assertEqual(controller.dao.alias('legacy')[3], 0)
            finally:
                controller.finish()
                if previous_directory is None:
                    os.environ.pop('MYDIRS_DIRECTORY', None)
                else:
                    os.environ['MYDIRS_DIRECTORY'] = previous_directory
                if previous_db is None:
                    os.environ.pop('MYDIRS_DB', None)
                else:
                    os.environ['MYDIRS_DB'] = previous_db

    def test_missing_legacy_path_is_not_backfilled_after_path_reuse(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_directory = os.path.join(tmpdir, 'db')
            os.makedirs(db_directory)
            missing_path = os.path.join(tmpdir, 'later reused')
            with sqlite3.connect(
                os.path.join(db_directory, 'mydirs.sqlite')
            ) as connection:
                connection.execute('''
                    CREATE TABLE PathByKey (
                        id_pathbykey INTEGER PRIMARY KEY,
                        path TEXT,
                        path_key TEXT
                    )
                ''')
                connection.execute(
                    'INSERT INTO PathByKey(path, path_key) VALUES (?, ?)',
                    (missing_path, 'legacy'),
                )

            previous_directory = os.environ.get('MYDIRS_DIRECTORY')
            previous_db = os.environ.get('MYDIRS_DB')
            os.environ['MYDIRS_DIRECTORY'] = tmpdir
            os.environ['MYDIRS_DB'] = db_directory
            first = MyDirsController()
            first.finish()
            os.makedirs(missing_path)
            second = MyDirsController()
            try:
                self.assertEqual(second.dao.alias('legacy')[5:7], (None, None))
            finally:
                second.finish()
                if previous_directory is None:
                    os.environ.pop('MYDIRS_DIRECTORY', None)
                else:
                    os.environ['MYDIRS_DIRECTORY'] = previous_directory
                if previous_db is None:
                    os.environ.pop('MYDIRS_DB', None)
                else:
                    os.environ['MYDIRS_DB'] = previous_db


if __name__ == '__main__':
    unittest.main()
