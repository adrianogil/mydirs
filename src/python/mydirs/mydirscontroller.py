from mydirs.dao.mydirsdao import MyDirsDao

import os
import os.path

import json
import contextlib
import errno
import fcntl
import stat
import tempfile
import time


HISTORY_BACKUP_FORMAT = 'mydirs-history'
HISTORY_BACKUP_VERSION = 1
LEGACY_STATS_MIGRATION_KEY = 'legacy_stats_imported_v2'
FRECENCY_GRACE_DAYS = 30
SECONDS_PER_DAY = 86400


class MyDirsController:
    def __init__(self, clock=None):

        self.clock = clock or time.time

        self.src_path = os.environ['MYDIRS_DIRECTORY']

        # Define database directory
        if 'MYDIRS_DB' in os.environ:
            self.db_directory = os.environ['MYDIRS_DB']
        else:
            self.db_directory = os.path.join(self.src_path, '..', 'db')

        os.makedirs(self.db_directory, exist_ok=True)

        # print("Loading db " + self.db_directory)
        self.db_file = os.path.join(self.db_directory, 'mydirs.sqlite')
        self.json_stats_filepath = os.path.join(
            self.db_directory,
            'mydirs_stats.json',
        )

        self.history_file = os.path.join(self.db_directory, 'mydirs.history')

        self.dao = MyDirsDao(self.db_file)
        # Keep these public attributes for integrations which used them before
        # the DAO was implemented.
        self.conn = self.dao.conn
        self.c = self.dao.c
        self.import_legacy_stats_once()

    def import_legacy_stats_once(self):
        if self.dao.get_metadata(LEGACY_STATS_MIGRATION_KEY) is not None:
            return

        counts = {}
        if os.path.isfile(self.json_stats_filepath):
            try:
                with open(self.json_stats_filepath, 'r', encoding='utf-8') as f:
                    legacy_stats = json.load(f)
                if isinstance(legacy_stats, dict):
                    counts = {
                        path: count
                        for path, count in legacy_stats.items()
                        if isinstance(path, str)
                        and type(count) is int
                        and count >= 0
                    }
            except (OSError, ValueError):
                counts = {}

        self.dao.import_legacy_path_counts_once(
            LEGACY_STATS_MIGRATION_KEY, counts
        )

    @staticmethod
    def frecency_score(usage_count, last_used_at, now):
        """Integer score: count * 30000 // (age_days + 30)."""
        if usage_count <= 0:
            return 0
        if last_used_at is None:
            age_days = FRECENCY_GRACE_DAYS
        else:
            age_days = max(
                0, (int(now) - int(last_used_at)) // SECONDS_PER_DAY
            )
        return usage_count * 30000 // (age_days + FRECENCY_GRACE_DAYS)

    def ranked_aliases(self, rows=None, now=None):
        if rows is None:
            rows = self.dao.aliases()
        if now is None:
            now = self.clock()

        def ranking(row):
            usage_count = row[3]
            last_used_at = row[4]
            score = self.frecency_score(usage_count, last_used_at, now)
            return (
                -score,
                -(last_used_at if last_used_at is not None else -1),
                -usage_count,
                row[2].encode('utf-8'),
                row[0],
            )

        return sorted(rows, key=ranking)

    def handle_no_args(self):
        print("Default mode: Update and Move HEAD to upstream\n")
        commands.update_batch_command.execute([], [], self)
        commands.move_head_command.execute([], [], self)

    def save(self, args, extra_args):
        current_dir = os.getcwd()

        if len(args) == 0:
            path_key = os.path.basename(current_dir).lower()
        else:
            path_key = args[0]

        row = self.dao.alias(path_key)
        if row is None:
            self.dao.add_alias(path_key, current_dir)
        else:
            print("key '%s' already exists" % (path_key))


    def update(self, args, extra_args):

        current_dir = os.getcwd()
        path_key = args[0]

        print('Updating', path_key, 'to current path')
        self.dao.replace_alias(path_key, current_dir)
        print('.')

    def remove(self, args, extra_args):
        current_dir = os.getcwd()

        if len(args) == 0:
            path_key = os.path.basename(current_dir).lower()
        else:
            path_key = args[0]

        print('deleting', path_key)
        self.dao.remove_alias(path_key)

    def read_history_entries(self):
        with self.history_lock():
            return self._read_history_entries_unlocked()

    def _read_history_entries_unlocked(self):
        if not os.path.isfile(self.history_file):
            return []
        with open(self.history_file, 'r', encoding='utf-8') as history_handler:
            return [line.rstrip('\n') for line in history_handler]

    @contextlib.contextmanager
    def history_lock(self):
        lock_path = self.history_file + '.lock'
        with open(lock_path, 'a', encoding='utf-8') as lock_handler:
            fcntl.flock(lock_handler.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(lock_handler.fileno(), fcntl.LOCK_UN)

    def write_history_entries(self, entries):
        with self.history_lock():
            self._write_history_entries_unlocked(entries)

    def _write_history_entries_unlocked(self, entries):
        descriptor, temporary_path = tempfile.mkstemp(
            prefix='.mydirs-history-', dir=self.db_directory
        )
        try:
            with os.fdopen(descriptor, 'w', encoding='utf-8') as handler:
                for entry in entries:
                    handler.write(entry + '\n')
                handler.flush()
                os.fsync(handler.fileno())
            os.replace(temporary_path, self.history_file)
        except BaseException:
            try:
                os.unlink(temporary_path)
            except FileNotFoundError:
                pass
            raise

    def save_history(self, path_to_save):
        with self.history_lock():
            history_entries = self._read_history_entries_unlocked()
            if history_entries and (
                os.path.realpath(history_entries[-1])
                == os.path.realpath(path_to_save)
            ):
                return
            with open(self.history_file, 'a', encoding='utf-8') as handler:
                handler.write(path_to_save + '\n')
                handler.flush()
                os.fsync(handler.fileno())

    def save_navigation(self, source_path, target_path):
        """Record a complete jump without interleaving concurrent shell jumps."""
        with self.history_lock():
            history_entries = self._read_history_entries_unlocked()
            for path in (source_path, target_path):
                if history_entries and (
                    os.path.realpath(history_entries[-1])
                    == os.path.realpath(path)
                ):
                    continue
                history_entries.append(path)
            self._write_history_entries_unlocked(history_entries)

    def history_backup_filepath(self, args, command):
        if len(args) != 1:
            raise ValueError("%s requires one JSON file path" % command)

        return os.path.abspath(os.path.expanduser(args[0]))

    def export_history(self, args, extra_args):
        backup_filepath = self.history_backup_filepath(args, '--export-history')
        backup = {
            'format': HISTORY_BACKUP_FORMAT,
            'version': HISTORY_BACKUP_VERSION,
            'entries': self.read_history_entries(),
        }
        self.validate_history_backup(backup)

        with open(backup_filepath, 'w', encoding='utf-8') as backup_handler:
            json.dump(backup, backup_handler, ensure_ascii=False, indent=2)
            backup_handler.write('\n')

        print("Exported %d history entries to %s" % (
            len(backup['entries']),
            backup_filepath,
        ))

    def validate_history_backup(self, backup):
        if not isinstance(backup, dict):
            raise ValueError('history backup must be a JSON object')
        if backup.get('format') != HISTORY_BACKUP_FORMAT:
            raise ValueError("history backup format must be '%s'" % HISTORY_BACKUP_FORMAT)
        if type(backup.get('version')) is not int:
            raise ValueError('history backup version must be an integer')
        if backup['version'] != HISTORY_BACKUP_VERSION:
            raise ValueError("unsupported history backup version: %s" % backup['version'])

        entries = backup.get('entries')
        if not isinstance(entries, list):
            raise ValueError('history backup entries must be a JSON array')

        for entry in entries:
            if not isinstance(entry, str):
                raise ValueError('history backup entries must contain only strings')
            if not entry or '\n' in entry or '\r' in entry or '\0' in entry:
                raise ValueError('history backup contains an invalid path entry')

        return entries

    def import_history(self, args, extra_args):
        backup_filepath = self.history_backup_filepath(args, '--import-history')

        try:
            with open(backup_filepath, 'r', encoding='utf-8') as backup_handler:
                backup = json.load(backup_handler)
        except json.JSONDecodeError as error:
            raise ValueError("invalid history backup JSON: %s" % error.msg)

        entries = self.validate_history_backup(backup)
        imported_entries = []
        for entry in entries:
            if imported_entries and (
                os.path.realpath(imported_entries[-1]) == os.path.realpath(entry)
            ):
                continue
            imported_entries.append(entry)

        self.write_history_entries(imported_entries)
        print("Imported %d history entries from %s" % (
            len(imported_entries),
            backup_filepath,
        ))

    def open(self, args, extra_args):

        path_key = args[0]

        # Open saved path
        row = self.dao.alias(path_key)
        if row is None:
            print('.')
        else:
            next_dir = row[1]
            print(next_dir)

    def record_open(self, args, extra_args):
        if len(args) != 3:
            raise ValueError(
                '--record-open requires an alias, source path, and target path'
            )
        path_key, source_path, target_path = args
        row = self.dao.alias(path_key)
        if row is None:
            raise ValueError("unknown alias: %s" % path_key)
        if os.path.realpath(row[1]) != os.path.realpath(target_path):
            raise ValueError('navigation target does not match the saved alias')
        self.save_navigation(source_path, target_path)
        self.dao.record_use(path_key, self.clock())

    def list(self, args, extra_args):
        rows = sorted(
            self.dao.aliases(), key=lambda row: row[2].encode('utf-8')
        )
        for row in rows:
            print(str(row[2]) + ":" + str(row[1]))

    def rank(self, args, extra_args):
        for row in self.ranked_aliases():
            print(str(row[2]) + ":" + str(row[1]))

    def path(self, args, extra_args):

        path_key = args[0]

        # Return saved path
        row = self.dao.alias(path_key)
        if row is None:
            print('.')
        else:
            print(row[1])

    def find(self, args, extra_args):
        target_path_key = args[0]

        print('Searching for', target_path_key, 'in bookmarked directories\n')
        rows = self.c.execute(
            "SELECT id_pathbykey, path, path_key, usage_count, last_used_at, "
            "device_id, inode FROM PathByKey WHERE path_key LIKE ?",
            ("%" + target_path_key + "%",),
        ).fetchall()
        for row in self.ranked_aliases(rows):
            print(str(row[2]) + ":" + str(row[1]))

    def _moved_candidates(self, stored_path):
        candidates = []
        candidates.extend(row[1] for row in self.dao.aliases())
        candidates.extend(self.read_history_entries())

        parent = os.path.dirname(stored_path)
        try:
            with os.scandir(parent) as entries:
                candidates.extend(entry.path for entry in entries)
        except OSError:
            pass

        unique = []
        seen = set()
        for candidate in candidates:
            if candidate == stored_path or candidate in seen:
                continue
            seen.add(candidate)
            unique.append(candidate)
        return unique

    def doctor_records(self):
        """Return read-only health findings for all saved directory records."""
        rows = sorted(self.dao.aliases(), key=lambda row: row[2].encode('utf-8'))
        identities = {}
        findings = []

        for row in rows:
            path = row[1]
            path_key = row[2]
            finding = {
                'alias': path_key,
                'path': path,
                'status': 'ok',
                'reason': '',
                'duplicate_of': None,
                'suggestions': [],
            }
            try:
                path_stat = os.stat(path)
            except OSError as error:
                if error.errno in (errno.EACCES, errno.EPERM):
                    finding['status'] = 'inaccessible'
                    finding['reason'] = error.strerror or 'permission denied'
                elif error.errno in (errno.ENOENT, errno.ENOTDIR):
                    finding['status'] = 'missing'
                    finding['reason'] = 'path does not exist'
                    stored_identity = (row[5], row[6])
                    if None not in stored_identity:
                        suggestions = []
                        for candidate in self._moved_candidates(path):
                            candidate_identity = self.dao.filesystem_identity(candidate)
                            if candidate_identity == stored_identity:
                                suggestions.append(candidate)
                        if suggestions:
                            finding['status'] = 'moved'
                            finding['reason'] = 'filesystem identity found elsewhere'
                            finding['suggestions'] = sorted(
                                suggestions, key=lambda item: item.encode('utf-8')
                            )
                else:
                    finding['status'] = 'inaccessible'
                    finding['reason'] = error.strerror or 'cannot inspect path'
            else:
                if not stat.S_ISDIR(path_stat.st_mode):
                    finding['status'] = 'not-directory'
                    finding['reason'] = 'saved path is not a directory'
                elif not os.access(path, os.R_OK | os.X_OK):
                    finding['status'] = 'inaccessible'
                    finding['reason'] = 'directory cannot be read or entered'
                else:
                    identity = (str(path_stat.st_dev), str(path_stat.st_ino))
                    if identity in identities:
                        finding['status'] = 'duplicate'
                        finding['reason'] = 'same directory as another alias'
                        finding['duplicate_of'] = identities[identity]
                    else:
                        identities[identity] = path_key
            findings.append(finding)
        return findings

    def doctor(self, args, extra_args):
        problems = 0
        for finding in self.doctor_records():
            if finding['status'] == 'ok':
                continue
            problems += 1
            details = finding['reason']
            if finding['duplicate_of'] is not None:
                details += "; duplicate of '%s'" % finding['duplicate_of']
            if finding['suggestions']:
                details += '; suggested path: ' + finding['suggestions'][0]
            print('%s %s:%s (%s)' % (
                finding['status'].upper(),
                finding['alias'],
                finding['path'],
                details,
            ))
        if problems == 0:
            print('OK no stale or duplicate directory records found')

    def repair_moved(self, args, extra_args):
        if len(args) != 2:
            raise ValueError('--repair-moved requires an alias and a new path')
        path_key = args[0]
        target = os.path.abspath(os.path.expanduser(args[1]))
        row = self.dao.alias(path_key)
        if row is None:
            raise ValueError("unknown alias: %s" % path_key)
        try:
            target_stat = os.stat(target)
        except OSError as error:
            raise ValueError("cannot inspect repair path: %s" % error)
        if not stat.S_ISDIR(target_stat.st_mode):
            raise ValueError('repair path is not a directory')
        if not os.access(target, os.R_OK | os.X_OK):
            raise ValueError('repair path cannot be read or entered')
        stored_identity = (row[5], row[6])
        target_identity = (str(target_stat.st_dev), str(target_stat.st_ino))
        if None in stored_identity:
            raise ValueError(
                'saved alias has no filesystem identity; use --update from '
                'the target directory instead'
            )
        if stored_identity != target_identity:
            raise ValueError('repair path does not match the saved filesystem identity')
        self.dao.replace_alias(path_key, target)
        print("Repaired '%s' to %s" % (path_key, target))

    def clean(self, args, extra_args):
        # List all saved path
        rows = self.dao.aliases()
        for row in rows:
            file_path = row[1]
            # print file_path
            if not os.path.exists(file_path):
                print("Removing " + str(row[2]) + ":" + str(row[1]))
                self.dao.remove_alias(row[2])

    def save_stats(self, path):
        """Compatibility shim for callers of the old path-based API."""
        row = self.c.execute(
            'SELECT path_key FROM PathByKey WHERE path = ? '
            'ORDER BY path_key COLLATE BINARY LIMIT 1',
            (path,),
        ).fetchone()
        if row is not None:
            self.dao.record_use(row[0], self.clock())

    def show_stats(self, args, extra_args):
        stats = {}
        for row in self.dao.aliases():
            stats[row[1]] = stats.get(row[1], 0) + row[3]
        for path in sorted(stats, key=lambda item: (-stats[item], item)):
            print("%s: %s" % (path, stats[path]))

    def show_db_path(self, args, extra_args):
        print(os.path.abspath(self.db_file))

    def show_history(self, args, extra_args):
        path_list = self.read_history_entries()

        if len(args) == 1:
            path_list = path_list[-int(args[0]):]

        for i in reversed(path_list):
            print(i)

    def go_back(self, args, extra_args):
        with self.history_lock():
            history_entries = self._read_history_entries_unlocked()
            current_dir = os.getcwd()
            destination = None
            while history_entries:
                last_path = history_entries.pop()
                if (
                    os.path.realpath(current_dir.strip())
                    != os.path.realpath(last_path)
                ):
                    destination = last_path
                    break
            self._write_history_entries_unlocked(history_entries)
        if destination is not None:
            print(destination)

    def current(self, args, extra_args):

        if len(args) == 1:
            current_path = args[0]
        elif len(args) == 0:
            current_path = os.getcwd()
        found = False
        attempts = 0

        while current_path != "" and found is False:
            self.c.execute("SELECT path_key, path  FROM PathByKey WHERE path LIKE ?", (current_path + "%",))
            results = self.c.fetchall()
            if len(results) <= 0:
                found = False

                current_folder = os.path.basename(current_path)
                # print(current_folder)
                current_path = current_path[:-(len(current_folder) + 1)]
                # print("Testing path: " + current_path)
                attempts += 1
            else:
                if len(results) > 1:
                    print("Found %d directories" % (len(results),))
                for row in results:
                    print('"' + row[1] + '" was saved as "' + str(row[0]) + '"')
                found = True

        if found is False:
            print("Current directory wasn't saved")

    def list_args(self, args, extra_args):
        mydirs_args = ''
        commands = self.get_commands()
        for k in commands.keys():
            mydirs_args = mydirs_args + k + " "
        print(mydirs_args)

    def show_help(self, args, extra_args):
        print("mydirs - bookmark directories and jump quickly\n")
        print("Usage:")
        print("  mydirs [options] [args]\n")
        print("Options:")
        print("  -s, --save <alias>       Save current directory under alias")
        print("  -o, --open <alias>       Print saved directory for alias")
        print("  -r, --remove <alias>     Remove saved alias")
        print("  -u, --update <alias>     Update saved alias to current directory")
        print("  -l, --list               List saved directories")
        print("  -f, --find <search>      Find aliases containing search string")
        print("  -p, --path <alias>       Print the saved path for alias")
        print("  -q, --current            Check whether current directory is saved")
        print("  -bh, --history <number>  Show last N entries from history")
        print("  -bk, --back              Go back to previous directory")
        print("      --export-history <file>  Export history to a JSON backup")
        print("      --import-history <file>  Replace history from a JSON backup")
        print("  -c, --clean              Remove entries that no longer exist")
        print("      --rank               List aliases by frecency")
        print("      --doctor             Report stale and duplicate records")
        print("      --repair-moved <alias> <path>  Repair an identity-matched move")
        print("      --stats              Show usage stats")
        print("      --db                 Show database path")
        print("      --list-args           List all supported flags")
        print("      --auto-list           List aliases for autocomplete")
        print("  -h, --help               Show this help message")

    def auto_list(self, args, extra_args):
        # Auto List all saved path for Autocomplete use
        print('\n'.join(row[2] for row in self.ranked_aliases()))

    def get_commands(self):
        commands_parse = {
            '-s'           : self.save,
            '-r'           : self.remove,
            '-u'           : self.update,
            '-o'           : self.open,
            '-l'           : self.list,
            '-p'           : self.path,
            '-c'           : self.clean,
            '-f'           : self.find,
            '-q'           : self.current,
            '-bk'          : self.go_back,
            '-bh'          : self.show_history,
            '--stats'      : self.show_stats,
            '--db'         : self.show_db_path,
            '--back'       : self.go_back,
            '--clean'      : self.clean,
            '--save'       : self.save,
            '--open'       : self.open,
            '--list'       : self.list,
            '--find'       : self.find,
            '--path'       : self.path,
            '--remove'     : self.remove,
            '--update'     : self.update,
            '--current'    : self.current,
            '--history'    : self.show_history,
            '--doctor'     : self.doctor,
            '--repair-moved': self.repair_moved,
            '--rank'       : self.rank,
            '--record-open': self.record_open,
            '--export-history': self.export_history,
            '--import-history': self.import_history,
            '--list-args'  : self.list_args,
            '--auto-list'  : self.auto_list,
            '-h'           : self.show_help,
            '--help'       : self.show_help,
            # 'no-args'      : self.handle_no_args,
        }
        return commands_parse

    def finish(self):
        self.dao.close()
