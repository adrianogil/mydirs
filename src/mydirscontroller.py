from dao.mydirsdao import MyDirsDao

import subprocess
import sqlite3
import os
import os.path

import json


class MyDirsController:
    def __init__(self):

        self.dao = MyDirsDao()

        self.src_path = os.environ['MYDIRS_DIRECTORY']

        # Define database directory
        if 'MYDIRS_DB' in os.environ:
            self.db_directory = os.environ['MYDIRS_DB']
        else:
            self.db_directory = self.src_path + '/../db/'

        if not os.path.exists(self.db_directory):
            os.makedirs(self.db_directory)

        # print("Loading db " + self.db_directory)
        self.db_file = self.db_directory + 'mydirs.sqlite'
        self.json_stats_filepath = self.db_directory + 'mydirs_stats.json'

        self.history_file = self.db_directory + 'mydirs.history'

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
            save_data = (current_dir, path_key)
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

    def save_history(self, path_to_save):
        total_path_cmd = 'cat "' + self.history_file + '" | wc -l'
        total_path = subprocess.check_output(total_path_cmd, shell=True)

        total_path = int(total_path.strip())

        # print(str(total_path))

        if total_path > 0:
            # Get last path in history file
            get_last_path_cmd = 'cat "' + self.history_file + '" | tail -1'
            last_path = subprocess.check_output(get_last_path_cmd, shell=True)
            last_path = last_path.strip()

            if last_path != path_to_save:
                # Save path in history file
                save_path_cmd = 'echo "' + path_to_save + '" >> "' + self.history_file + '"'
                subprocess.check_output(save_path_cmd, shell=True)
        else:
            # Save path in history file
            save_path_cmd = 'echo "' + path_to_save + '" >> "' + self.history_file + '"'
            subprocess.check_output(save_path_cmd, shell=True)

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

    def show_history(self, args, extra_args):

        if len(args) == 0:
            get_path_history_cmd = 'cat "' + self.history_file + '"'
            path_history = subprocess.check_output(get_path_history_cmd, shell=True)
            path_history = path_history.strip()

            path_list = path_history.split('\n')

            for i in reversed(path_list):
                print(i)
        elif len(args) == 1:
            get_path_history_cmd = 'cat "' + self.history_file + '" | tail -' + \
                str(args[0]) + ''
            path_history = subprocess.check_output(get_path_history_cmd, shell=True)
            path_history = path_history.strip()

            path_list = path_history.split('\n')

            for i in reversed(path_list):
                print(i)

    def go_back(self, args, extra_args):

        total_path_cmd = 'cat "' + self.history_file + '" | wc -l'
        total_path = subprocess.check_output(total_path_cmd, shell=True)

        total_path = int(total_path.strip())

        # print(str(total_path))

        # Get last path in history file
        get_last_path_cmd = 'cat "' + self.history_file + '" | tail -1'
        last_path = subprocess.check_output(get_last_path_cmd, shell=True)
        last_path = last_path.strip()

        # print(last_path)

        if total_path > 0:
            update_path_cmd = 'cat "' + self.history_file + '" | head -' + str(total_path-1) + \
                ' > tmp.history'
            subprocess.check_output(update_path_cmd, shell=True)

            update_path_cmd = 'cat tmp.history > "' + self.history_file + '" && rm tmp.history'
            subprocess.check_output(update_path_cmd, shell=True)

            current_dir = os.getcwd()

            if current_dir.strip() == last_path:
                self.go_back(args, extra_args)
            else:
                print(last_path)

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
            '--list-args'  : self.list_args,
            '--auto-list'  : self.auto_list,
            # 'no-args'      : self.handle_no_args,
        }
        return commands_parse

    def finish(self):
        # We can also close the cursor if we are done with it
        self.c.close()