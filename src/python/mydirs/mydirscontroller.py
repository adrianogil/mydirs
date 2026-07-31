from mydirs.dao.mydirsdao import MyDirsDao

import sqlite3
import os
import os.path

import json


HISTORY_BACKUP_FORMAT = 'mydirs-history'
HISTORY_BACKUP_VERSION = 1


class MyDirsController:
    def __init__(self):

        self.dao = MyDirsDao()

        self.src_path = os.environ['MYDIRS_DIRECTORY']

        # Define database directory
        if 'MYDIRS_DB' in os.environ:
            self.db_directory = os.environ['MYDIRS_DB']
        else:
            self.db_directory = os.path.join(self.src_path, '..', 'db')

        if not os.path.exists(self.db_directory):
            os.makedirs(self.db_directory)

        # print("Loading db " + self.db_directory)
        self.db_file = os.path.join(self.db_directory, 'mydirs.sqlite')
        self.json_stats_filepath = os.path.join(
            self.db_directory,
            'mydirs_stats.json',
        )

        self.history_file = os.path.join(self.db_directory, 'mydirs.history')

        self.conn = sqlite3.connect(self.db_file);
        # Creating cursor
        self.c = self.conn.cursor()
        # Create table
        self.c.execute('''
            CREATE TABLE IF NOT EXISTS PathByKey (
                id_pathbykey INTEGER,
                path TEXT,
                path_key TEXT,
                PRIMARY KEY (id_pathbykey)
            )
        ''')

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

        self.c.execute("SELECT path FROM PathByKey WHERE path_key LIKE ?", (path_key,))
        row = self.c.fetchone()
        if row is None:
            # Save current path
            #print "Saving Current Path " + os.getcwd() + " string " + sys.argv[2]
            # dict_path = {":path" : os.getcwd(), ":key": sys.argv[2]}
            #print dict_path
            save_sql = "INSERT INTO PathByKey (path,path_key) VALUES (:path,:key)"
            save_data = {'path': current_dir, 'key': path_key}
            self.c.execute(save_sql, save_data)
            self.conn.commit()
        else:
            print("key '%s' already exists" % (path_key))


    def update(self, args, extra_args):

        current_dir = os.getcwd()
        path_key = args[0]

        # Remove a saved path
        print('Updating', path_key, 'to current path')
        self.c.execute("DELETE FROM PathByKey WHERE path_key = ?", (path_key,))
        self.conn.commit()

        self.c.execute("INSERT INTO PathByKey (path,path_key) VALUES (:path,:key)", (current_dir, path_key))
        self.conn.commit()
        print('.')

    def remove(self, args, extra_args):
        current_dir = os.getcwd()

        if len(args) == 0:
            path_key = os.path.basename(current_dir).lower()
        else:
            path_key = args[0]

        print('deleting', path_key)
        self.c.execute("DELETE FROM PathByKey WHERE path_key = ?", (path_key,))
        self.conn.commit()

    def read_history_entries(self):
        if not os.path.isfile(self.history_file):
            return []

        with open(self.history_file, 'r', encoding='utf-8') as history_handler:
            return [line.rstrip('\n') for line in history_handler]

    def write_history_entries(self, entries):
        with open(self.history_file, 'w', encoding='utf-8') as history_handler:
            for entry in entries:
                history_handler.write(entry + '\n')

    def save_history(self, path_to_save):
        history_entries = self.read_history_entries()
        if history_entries and os.path.realpath(history_entries[-1]) == os.path.realpath(path_to_save):
            return

        with open(self.history_file, 'a', encoding='utf-8') as history_handler:
            history_handler.write(path_to_save + '\n')

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
        self.c.execute("SELECT path FROM PathByKey WHERE path_key LIKE ?", (path_key,))
        row = self.c.fetchone()
        if row is None:
            print('.')
        else:
            next_dir = row[0]
            print(next_dir)

            self.save_history(os.getcwd())
            self.save_history(next_dir)
            self.save_stats(next_dir)

    def list(self, args, extra_args):
        # List all saved path
        self.c.execute("SELECT * from PathByKey ORDER BY path_key")
        for row in self.c:
            print(str(row[2]) + ":" + str(row[1]))

    def path(self, args, extra_args):

        path_key = args[0]

        # Return saved path
        self.c.execute("SELECT path FROM PathByKey WHERE path_key LIKE ?", (path_key,))
        row = self.c.fetchone()
        if row is None:
            print('.')
        else:
            print(row[0])

    def find(self, args, extra_args):
        target_path_key = args[0]

        print('Searching for', target_path_key, 'in bookmarked directories\n')
        self.c.execute("SELECT * FROM PathByKey WHERE path_key LIKE ?", ("%" + target_path_key + "%",))
        for row in self.c:
            print(str(row[2]) + ":" + str(row[1]))

    def clean(self, args, extra_args):
        # List all saved path
        self.c.execute("SELECT * from PathByKey ORDER BY path_key")
        rows = self.c.fetchall()
        for row in rows:
            file_path = row[1]
            # print file_path
            if not os.path.exists(file_path):
                print("Removing " + str(row[2]) + ":" + str(row[1]))
                self.c.execute("DELETE FROM PathByKey WHERE path_key = ?", (row[2],))
                self.conn.commit()

    def save_stats(self, path):
        if os.path.isfile(self.json_stats_filepath):
            with open(self.json_stats_filepath, 'r') as f:
                stats = json.load(f)
            if path in stats:
                stats[path] = stats[path] + 1
            else:
                stats[path] = 1
        else:
            stats = {}
            stats[path] = 1
        # Writing JSON data
        with open(self.json_stats_filepath, 'w') as f:
            json.dump(stats, f)

    def show_stats(self, args, extra_args):
        if os.path.isfile(self.json_stats_filepath):
            with open(self.json_stats_filepath, 'r') as f:
                stats = json.load(f)
            paths = []
            for s in stats:
                paths.append(s)

            paths = sorted(paths, key=lambda x: stats[x], reverse=True)

            for s in paths:
                print("%s: %s" % (s, stats[s]))

    def show_db_path(self, args, extra_args):
        print(os.path.abspath(self.db_file))

    def show_history(self, args, extra_args):
        path_list = self.read_history_entries()

        if len(args) == 1:
            path_list = path_list[-int(args[0]):]

        for i in reversed(path_list):
            print(i)

    def go_back(self, args, extra_args):
        while True:
            history_entries = self.read_history_entries()
            if not history_entries:
                return

            last_path = history_entries.pop()
            self.write_history_entries(history_entries)
            current_dir = os.getcwd()

            if os.path.realpath(current_dir.strip()) == os.path.realpath(last_path):
                continue
            else:
                print(last_path)
                return

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
        print("      --stats              Show usage stats")
        print("      --db                 Show database path")
        print("      --list-args           List all supported flags")
        print("      --auto-list           List aliases for autocomplete")
        print("  -h, --help               Show this help message")

    def auto_list(self, args, extra_args):
        # Auto List all saved path for Autocomplete use
        self.c.execute("SELECT * from PathByKey")
        strList = ''
        for row in self.c:
            strList = strList + ' ' +  str(row[2])
        print(strList)

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
        # We can also close the cursor if we are done with it
        self.c.close()
