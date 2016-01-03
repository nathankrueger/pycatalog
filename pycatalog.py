#!/usr/bin/python

import sqlite3
import sys
import glob
import os
import re
import hashlib
import shlex
import subprocess
import shutil
import argparse
import collections

### Constants ###
PYCATALOG_DIR = '/Users/nathankrueger/Documents/Programming/Python/pycatalog/'
DEFAULT_DB = '{0}catalog.db'.format(PYCATALOG_DIR)
DEFAULT_PLAYLIST = '{0}default.m3u'.format(PYCATALOG_DIR)
DEFAULT_NEW_FOLDER = '/Users/nathankrueger/NAS/CACHEDEV1_DATA/Documents/Work'
DEFAULT_HIDE_FILE = '{0}.hide'.format(PYCATALOG_DIR)
OBFUSCATION_MARKER_FILE = '{0}.obfuscated'.format(PYCATALOG_DIR)

VLC_COMMAND = '/Applications/VLC.app/Contents/MacOS/VLC'
SINGLE_VLC_COMMAND = 'open -a VLC' # Use this to keep one instance of VLC, instead of spawning many

TITLES_TABLENAME = 'titles'
TITLES_TABLEDEF = '''titles
					(filename text, actor text, keywords text)'''

# Returns '/User/admin/Documents/' from '/User/admin/Documents/foo.avi'
def getFilePath(filename):
	match = re.search(r'(.+\/).+\..+', filename)
	if match:
		return match.group(1)
	else:
		return None

# Returns 'foo.avi' from '/User/admin/Documents/foo.avi'
def getBasename(filename):
	match = re.search(r'.+\/(.+\..+)', filename)
	if match:
		return match.group(1)
	else:
		return None

def isObfuscated():
	return os.path.isfile(OBFUSCATION_MARKER_FILE)

# This will do the right thing iff the dictionary is 1:1, i.e. no two keys have the same value (and vice-versa)
def getInverseDict(dictionary):
	result = {}
	for k,v in dictionary.items():
		result[v] = k

	return result

def touch(filename):
	open(filename, 'a').close()	

# Return the MD5
def getObfuscatedName(filename):
	m = hashlib.md5()
	m.update(filename)
	return m.hexdigest()

# Get a dict of key: filename, value: md5(filename)
def getObfuscatedDict(files):
	result = {}
	# To Do -- assert there are no duplicate filenames OR obfuscated names
	for filename in files:
		result[filename] = "{0}{1}".format(getFilePath(filename), getObfuscatedName(filename))

	return result

def serializeObfuscatedDict(obsDict, filename):
	result = True
	try:
		f = open(filename, 'w')
		for key in obsDict.keys():
			f.write("{0} {1}\n".format(key, obsDict[key]))

		f.close()
	except Exception as err:
		print err
		result = False

	return result

# An empty result dictionary should be treated as an error condition
def deserializeObfuscatedDict(filename):
	result = {}
	success = True

	try:
		f = open(filename, 'r')
		contents = f.read()
		f.close()
	except Exception as err:
		print err
		success = False

	if success:
		for line in contents.split('\n'):
			if len(line) > 0:
				items = line.split(' ')
				result[items[0]] = items[1]

	return result


def moveFile(filename, target, dry):
	print "Moving file {0} to {1}".format(filename, target)
	if not dry:
		shutil.move(filename, target)

def tableExists(cursor, tableName):
	t = (tableName,)
	cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", t)
	result = cursor.fetchone()
	return result

def makeTable(cursor, value):
	cursor.execute("CREATE TABLE {0}".format(value))

def timeSortFiles(files):
	timeDict = {} # A dictionary with (key: timestamp, value: file [])
	result = []
	for filename in files:
		timestamp = os.path.getmtime(filename) # Numeric timestamp
		if not timestamp in timeDict.keys():
			timeDict[timestamp] = [filename]
		else:
			timeDict[timestamp].append(filename)

	timestamps = timeDict.keys()
	timestamps.sort(reverse=True) # For descending order (newest first)

	for timestamp in timestamps:
		for filename in timeDict[timestamp]:
			result.append(filename)

	return result

def limitFiles(files, limit):
	result = []
	count = 0
	for filename in files:
		if(count < limit):
			result.append(filename)
		else:
			break
		count = count + 1

	return result

def makePlaylist(files, name, ext, hide_file, timesort):
	f = open(name, 'w')

	obs = isObfuscated()
	obsDict = deserializeObfuscatedDict(hide_file)
	inverseDict = {}
	fileTupleList = []
	if obs:
		# Get obfuscation dictionary
		inverseDict = getInverseDict(obsDict)

		# If timesorted, we don't want to sort based on display name
		if timesort:
			for filename in files:
				disp_name = getBasename(inverseDict[filename])
				fileTupleList.append((filename, disp_name))

		# Sort alphabetically based on display name
		else:
			dispFileDict = {}

			for filename in files:
				disp_name = getBasename(inverseDict[filename])
				dispFileDict[disp_name] = filename
		
			dispFileDictKeys = dispFileDict.keys()
			dispFileDictKeys.sort()
			for dispName in dispFileDictKeys:
				fileTupleList.append((dispFileDict[dispName], dispName))

	else:
		for filename in files:
			fileTupleList.append((filename, getBasename(filename)))

	if ext:
		f.write("#EXTM3U\n\n")

	for fileTuple in fileTupleList:
		filename = fileTuple[0]
		disp_name = fileTuple[1]
		if ext:
			f.write("#EXTINF:-1,{0}\n".format(disp_name))
		f.write('{0}\n\n'.format(filename))

	f.close()

def playPlaylist(filename, single):
	command = '{0} {1}'.format(SINGLE_VLC_COMMAND if single else VLC_COMMAND, filename)
	args = shlex.split(command)
	p = subprocess.Popen(args)

def updateFile(newFolder, textFile):
	fileList = []
	for filename in glob.glob('{0}/*.*'.format(newFolder)):
		fileList.append(filename)

	infile = open(textFile, 'r')
	contents = infile.read()
	infile.close()

	outputDict = {}

	for line in contents.split('\n'):
		items = line.split(' ')
		if len(items) == 3:
			entry_tuple = (items[1], items[2])
			outputDict[items[0]] = entry_tuple
		elif len(items) <= 3:
			entry_tuple = ("", "")
			outputDict[items[0]] = entry_tuple

	for filename in fileList:
		if not filename in outputDict.keys():
			match = re.search(r'.+\/([A-Za-z]+)\d+\.[A-Za-z0-9]+', filename)
			if match:
				outputDict[filename] = (match.group(1), "")
			else:
				outputDict[filename] = ("", "")
			print 'Adding {0}'.format(filename)

	orderedOutputDict = collections.OrderedDict(sorted(outputDict.items()))	

	outfile = open(textFile, 'w')
	first = True
	for key in orderedOutputDict.keys():
		if first:
			first = False
		else:
			outfile.write('\n')
			
		outfile.write('{0} {1} {2}'.format(key, orderedOutputDict[key][0], orderedOutputDict[key][1]))

	outfile.close()

# Get a dictionary of key: keyword, value: list(tuple(filename, actor)) 
def genKeywordDict(cursor):
	q = "SELECT * FROM '{0}'".format(TITLES_TABLENAME)
	cursor.execute(q)
	kdict = {}
	for row in cursor.fetchall():
		filename = str(row[0])
		actor = str(row[1])
		keywords = str(row[2])
		for keyword in keywords.split(','):
			if keyword in kdict.keys():
				kdict[keyword].append((filename, actor))
			else:
				tup = (filename, actor)
				kdict[keyword] = [tup]

	return kdict

def sqlQuery(cursor, query):
	q = ''
	for word in query:
		q += word + ' '
	fileList = []
	try:
		cursor.execute(q)
		for row in cursor.fetchall():
			fileList.append(row[0])
	except Exception as err:
		print err
	
	return fileList

def query(cursor, actor=None, keywords=None, all_keywords=False):
	fileList = []
	allRows = []
	q = ''

	kdict = genKeywordDict(cursor)

	# Yikes...
	if keywords and actor:
		if all_keywords:
			fileDict = {}
			for key in keywords:
				for tup in kdict[key]:
					if(tup[1] == actor):
						if not tup[0] in fileDict:
							fileDict[tup[0]] = [key]
						else:
							fileDict[tup[0]].append(key)
			
			for filename in fileDict.keys():
				if len(fileDict[filename]) == len(keywords):
					fileList.append(filename)
			
		else:
			for key in keywords:
				try:
					tup_list = kdict[key]
					for tup in tup_list:
						if(tup[1] == actor):
							if not tup[0] in fileList:
								fileList.append(tup[0])
				except KeyError:
					print "Key {0} not present in database.".format(key)

	elif actor:
		q = "SELECT * FROM {0} WHERE actor='{1}'".format(TITLES_TABLENAME, actor)
		cursor.execute(q)
		for row in cursor.fetchall():
			fileList.append(row[0])
			
	elif keywords:
		if all_keywords:
			fileDict = {}
			for key in keywords:
				for tup in kdict[key]:
					if not tup[0] in fileDict:
						fileDict[tup[0]] = [key]
					else:
						fileDict[tup[0]].append(key)
			
			for filename in fileDict.keys():
				if len(fileDict[filename]) == len(keywords):
					fileList.append(filename)
					
		else:
			for key in keywords:
				try:
					tup_list = kdict[key]
					for tup in tup_list:
						if not tup[0] in fileList:
							fileList.append(tup[0])
				except KeyError:
					print "Key {0} not present in database.".format(key)

	return fileList

def removeRow(cursor, filename):
	cursor.execute("DELETE FROM titles WHERE filename='{0}'".format(filename))

def addRow(cursor, filename, actor, keywords):
	cursor.execute("INSERT INTO titles VALUES ('{0}', '{1}', '{2}')".format(filename, actor, keywords))

def processAdd(cursor, add_statement):
	if add_statement:
		arglist = add_statement.split(' ')
		filename = arglist[0]
		actor = arglist[1]
		keywords = arglist[2]
		addRow(cursor, filename, actor, keywords)
		
def parseInputFile(cursor, filename):
	f = open(filename, 'r')
	contents = f.read()
	f.close()
	
	for line in contents.split('\n'):
		items = line.split(' ')
		if len(items) == 3:
			addRow(cursor, items[0], items[1], items[2])

def getAllFiles(cursor):
	return sqlQuery(cursor, 'SELECT * FROM {0}'.format(TITLES_TABLENAME).split(' '))

def getAllRows(cursor):
	cursor.execute("SELECT * FROM titles ORDER BY actor")
	return cursor.fetchall()

def dump_db(cursor):
	rows = getAllRows(cursor)
	for row in rows:
		print "Actor: {0:20} Filename: {1:75} Keywords: {2}".format(row[1], row[0], row[2])
		
def dump_text(cursor):
	rows = getAllRows(cursor)
	for row in rows:
		print "{0} {1} {2}".format(row[0], row[1], row[2])
		
def dump_keywords(cursor):
	keyDict = genKeywordDict(cursor)
	keys = keyDict.keys()
	keys.sort()
	for key in keys:
		if len(key.strip('\s')) > 0:
			print '{0:20} {1}'.format(key, len(keyDict[key]))

def hideFiles(cursor, hideFile, dry):
	allFiles = getAllFiles(cursor)
	obsDict = getObfuscatedDict(allFiles)
	if serializeObfuscatedDict(obsDict, hideFile):
		if isObfuscated():
			print "Error: files are already hidden."
		else:
			rows = getAllRows(cursor)
			touch(OBFUSCATION_MARKER_FILE)
			for row in rows:
				filename = row[0]
				actor = row[1]
				keywords = row[2]
				print "Hiding file: {0}...".format(filename)

				target = obsDict[filename]
				moveFile(filename, target, dry)
				removeRow(cursor, filename)
				addRow(cursor, target, actor, keywords)

def unhideFiles(cursor, hideFile, dry):
	obsDict = deserializeObfuscatedDict(hideFile)
	if len(obsDict) > 0:
		if isObfuscated():
			inverse_dict = getInverseDict(obsDict)
			rows = getAllRows(cursor)
			os.remove(OBFUSCATION_MARKER_FILE)

			for row in rows:
				filename = row[0]
				actor = row[1]
				keywords = row[2]
				print "Unhiding file: {0}...".format(filename)

				target = inverse_dict[filename]
				moveFile(filename, target, dry)
				removeRow(cursor, filename)
				addRow(cursor, target, actor, keywords)
		else:
			print "Error: files aren't hidden."

def audit_text(text_file):
	f = open(text_file, 'r')
	contents = f.read()
	f.close()

	bad_lines = []

	lines = contents.split('\n')
	for line in lines:
		# Make sure the file has 
		match = re.search(r'.+\s.+\s.+', line)
		if not match:
			bad_lines.append(line)
		else:
			items = line.split(' ')
			filename = items[0]

			# Make sure the file exists on disk
			if not os.path.isfile(filename):
				bad_lines.append(filename)
			else:
				# Make sure the filename is in the standard format
				match = re.search(r'.+\/([A-Za-z]+)\d+\.[A-Za-z0-9]+', filename)			
				if not match:
					bad_lines.append(filename)

	for line in bad_lines:
		print line

def audit_db(cursor):
	rows = getAllRows(cursor)
	badRows = []
	for row in rows:
		filename = row[0]
		actor = row[1]
		keys = row[2]
		if not os.path.isfile(filename):
			badRows.append(row)
			continue
		if (len(actor) < 1) or (len(keys) < 1):
			badRows.append(row)
			continue

	for row in badRows:
		print "Bad database entry: {0} {1} {2}".format(row[0], row[1], row[2])

def main():
	# Grab command-line arguments
	parser = argparse.ArgumentParser(description='Add an entry, query an entry.')
	parser.add_argument('keywords', metavar='K', type=str, nargs='*', help='Keywords to look for.')
	parser.add_argument('--sql', type=str, nargs='*', help='Use SQL directly.')
	parser.add_argument('--actor', type=str, help='Filter on an actor.')
	parser.add_argument('--database', type=str, help='Specify the name of the database to create / load.')
	parser.add_argument('--playlist', type=str, help='Specify the name of the playlist to save for this query.')
	parser.add_argument('--add', type=str, help='Specify an entry to add <FILENAME> <ACTOR> <KEYWORDS comma separated>')
	parser.add_argument('--input', type=str, help='An input file to load into the database.')
	parser.add_argument('--remove_file', type=str, help='Remove the specified file from the database.')
	parser.add_argument('--update', type=str, help='Add new file entries found in the given directory.')
	parser.add_argument('--dump_db', action='store_true', help='Dump the database to stdout in a human readable form.')
	parser.add_argument('--dump_text', action='store_true', help='Dump the database to stdout in a form suitable for import.')
	parser.add_argument('--list', action='store_true', help='List the items matching your query.')
	parser.add_argument('--dump_keywords', action='store_true', help='Dump all keywords currently in the database.')
	parser.add_argument('--combine', action='store_true', help='Match on entries that specify all keywords as opposed to combining the results of seperate queries for each keyword.')
	parser.add_argument('--all', action='store_true', help='Match all titles.')
	parser.add_argument('--no_play', action='store_true', help='Prevents loading the media player if the current query had > 0 results.')
	parser.add_argument('--timesort', action='store_true', help='Sorts matches by their file timestamp.')
	parser.add_argument('--audit_text', type=str, help='Audit poorly formed input file entries.')
	parser.add_argument('--audit_db', action='store_true', help='Audit database entries.')
	parser.add_argument('--limit', type=int, help='Limit the total number of results.')
	parser.add_argument('--single_inst', action='store_true', help='Load matched titles into a single instance of the specified media player.')
	parser.add_argument('--obs_file', type=str, help='Specify a non-default obfuscation file.')
	parser.add_argument('--hide', action='store_true', help='Obfuscate files on disk.')
	parser.add_argument('--unhide', action='store_true', help='Remove obfuscation of files on disk.')
	parser.add_argument('--basic_m3u', action='store_true', help='Use minimal playlist format.')
	parser.add_argument('--dry_run', action='store_true', help='Update the database without moving files for hide operations.')
	parser.add_argument('--count', action='store_true', help='Count the number of file entries in the database.')
	args = parser.parse_args()

	# Default variables that can be overridden
	fileList = []
	ext = True
	dry = False
	timesort = False
	playlist_name = DEFAULT_PLAYLIST
	database_name = DEFAULT_DB
	new_folder = DEFAULT_NEW_FOLDER
	hide_file = DEFAULT_HIDE_FILE

	if args.dry_run:
		dry = True

	if args.obs_file:
		hide_file = args.obs_file
	
	# Don't use the EXTM3U format
	if args.basic_m3u:
		ext = False

	# Get the playlist filename
	if args.playlist:
		playlist_name = args.playlist
		
	# Get the database filename	
	if args.database:
		database_name = args.database
	
	if args.update:
		updateFile(new_folder, args.update)
		
	# Create the database objects
	conn = sqlite3.connect(database_name)
	cursor = conn.cursor()

	# Make a default table if none exists already
	if not tableExists(cursor, TITLES_TABLENAME):
		makeTable(cursor, TITLES_TABLEDEF)

	# Populate db from text file
	if args.input:
		parseInputFile(cursor, args.input)

	# Add entry
	processAdd(cursor, args.add)
	
	# Remove entry
	if args.remove_file:
		removeRow(cursor, args.remove_file)
	
	# Count entries in the database
	if args.count:
		print len(getAllRows(cursor))

	# Obfuscate filenames
	if args.hide:
		hideFiles(cursor, hide_file, dry)

	# Remove filename obfuscation
	if args.unhide:
		unhideFiles(cursor, hide_file, dry)
	
	# Do the query if requested
	if args.all:
		fileList = getAllFiles(cursor)
	else:
		# Run a query
		if args.sql:
			fileList=sqlQuery(cursor, args.sql)
		else:
			if args.keywords:
				if len(args.keywords) == 1 and args.keywords[0] == 'all':
					fileList = getAllFiles(cursor)
				else:
					fileList=query(cursor, args.actor, list(args.keywords), args.combine)
			elif args.actor:
				fileList=query(cursor, args.actor)
				
	# Sort files alphabetically
	fileList.sort()
	
	# Dump the db formatted for viewing
	if args.dump_db:
		dump_db(cursor)

	# Dump the db in a raw format suitable for re-import
	if args.dump_text:
		dump_text(cursor)
		
	# Dump keywords in db	
	if args.dump_keywords:
		dump_keywords(cursor)
	
	# Print out poorly formed file entries
	if args.audit_text:
		audit_text(args.audit_text)

	if args.audit_db:
		audit_db(cursor)

	if len(fileList) > 0:
		# Sort files by timestamp if requested
		if args.timesort:
			fileList = timeSortFiles(fileList)
			timesort = True
		
		if args.limit:
			fileList = limitFiles(fileList, args.limit)

		# Make and play playlist
		makePlaylist(fileList, playlist_name, ext, hide_file, timesort)
		if not args.no_play:
			playPlaylist(playlist_name, args.single_inst)
		
		# List the queried files
		if args.list:
			for filename in fileList:
				print filename

	# Save everything
	conn.commit()
	conn.close()

if __name__ == "__main__":
    main()
