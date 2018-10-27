
import sqlite3, os

class MyDirsController:
    def __init__(self, db_directory):
        list_args = '--save -s --open -o --remove -r --list -l -u --update -f --find -q --current'
        self.conn = sqlite3.connect(db_directory);
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
    
        # Save current path
        #print "Saving Current Path " + os.getcwd() + " string " + sys.argv[2]
        # dict_path = {":path" : os.getcwd(), ":key": sys.argv[2]}
        #print dict_path
        save_sql = "INSERT INTO PathByKey (path,path_key) VALUES (:path,:key)"
        save_data = (current_dir, path_key)
        self.c.execute(save_sql, save_data)
        self.conn.commit()
        print('.')

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

    def open(self, args, extra_args):

        path_key = args[0]

        # Open saved path
        self.c.execute("SELECT path FROM PathByKey WHERE path_key LIKE ?", (path_key,))
        row = self.c.fetchone()
        if row is None:
            print('.')
        else:
            print(row[0])

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

    def current(self, args, extra_args):
        self.c.execute("SELECT path_key FROM PathByKey WHERE path LIKE ?", (os.getcwd() + "%",))
        results = self.c.fetchall()
        if len(results) <= 0 :
            print("Current directory wasn't saved")
        else:
            if len(results) > 1:
                print("Found %d directories" % (len(results),))
            for row in results:
                print('Current directory was saved as "' + str(row[0]) + '"')

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
            '--clean'      : self.clean,
            '--save'       : self.save,
            '--open'       : self.open,
            '--list'       : self.list,
            '--find'       : self.find,
            '--path'       : self.path,
            '--remove'     : self.remove,
            '--update'     : self.update,
            '--current'    : self.current,
            '--list-args'  : self.list_args,
            '--auto-list'  : self.auto_list,
            # 'no-args'      : self.handle_no_args,
        }
        return commands_parse

    def finish(self):
        # We can also close the cursor if we are done with it
        self.c.close()