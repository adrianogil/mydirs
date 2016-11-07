#!/usr/bin/env python
import sys, sqlite3, os, commands

list_args = '--save -s --open -o --remove -r --list -l'

# Open Connection
mydirs_directory = '/Users/gil/workspace/python/mydirs/db/'
conn = sqlite3.connect(mydirs_directory + 'mydirs.sqlite');

# Creating cursor
c = conn.cursor()

# Create table
c.execute('''
	CREATE TABLE IF NOT EXISTS PathByKey (
		id_pathbykey INTEGER,
		path TEXT,
		path_key TEXT,
		PRIMARY KEY (id_pathbykey)
	)
''')

if len(sys.argv) == 3:
	if (sys.argv[1] == '--save' or sys.argv[1] == '-s'):
		# Save current path
		#print "Saving Current Path " + os.getcwd() + " string " + sys.argv[2]
		dict_path = {":path" : os.getcwd(), ":key": sys.argv[2]}
		#print dict_path
		c.execute("INSERT INTO PathByKey (path,path_key) VALUES (:path,:key)", (os.getcwd(), sys.argv[2]))
		conn.commit()
		print '.'
	elif (sys.argv[1] == '--open' or sys.argv[1] == '-o'):
		# Open saved path
		c.execute("SELECT path FROM PathByKey WHERE path_key LIKE ?", (sys.argv[2],))
		row = c.fetchone()
		print row[0]
		# print os.chdir(row[0])
		# print commands.getoutput('cd ' + row[0])
	elif (sys.argv[1] == "--remove" or sys.argv[1] == '-r'):
		# Remove a saved path
		print 'deleting', sys.argv[2]
		c.execute("DELETE FROM PathByKey WHERE path_key = ?", (sys.argv[2],))
		conn.commit()
elif len(sys.argv) == 2:
	if (sys.argv[1] == '--list' or sys.argv[1] == '-l'):
		# List all saved path
		c.execute("SELECT * from PathByKey ORDER BY path_key")
		for row in c:
			print str(row[2]) + ":" + str(row[1])
	elif (sys.argv[1] == '--auto-list'):
		# Auto List all saved path for Autocomplete use
		c.execute("SELECT * from PathByKey")
		strList = ''
		for row in c:
			strList = strList + ' ' +  str(row[2])
		print strList
	elif (sys.argv[1] == '--list-args'):
		print list_args
	if (sys.argv[1] == '--clean' or sys.argv[1] == '-c'):
		# List all saved path
		c.execute("SELECT * from PathByKey ORDER BY path_key")
		rows = c.fetchall()
		for row in rows:
			file_path = row[1]
			print file_path
			if not os.path.exists(file_path):
				print "Removing " + str(row[2]) + ":" + str(row[1])
				c.execute("DELETE FROM PathByKey WHERE path_key = ?", (row[2],))
				conn.commit()


# We can also close the cursor if we are done with it
c.close()