#!/usr/bin/env python3

import time
import sqlite3
import sys

from math import sqrt
from multiprocessing import Pool
from pathlib import Path

import numpy as np

from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

import vectorizer



def mk_vecs(words1, words2):
	wd = dict()
	for w in words1:
		if w not in wd:
			wd[w] = len(wd)
	for w in words2:
		if w not in wd:
			wd[w] = len(wd)
	res1 = [ 0 for i in range(0, len(wd)) ]
	for w in words1:
		res1[wd[w]] += 1
	res2 = [ 0 for i in range(0, len(wd)) ]
	for w in words2:
		res2[wd[w]] += 1
	return (res1, res2)



def calc_proj_sim(input_pair):
	(project, projwordslist, otherwordslist) = input_pair
	result = list()
	for (id1, words1) in projwordslist:
		for (id2, words2) in otherwordslist:
			sim_cs = float(cosine_similarity(words1, words2))
			if sim_cs > 0.0:
				result.append((id1, id2, sim_cs))
	return (project, result)



conn = sqlite3.connect('./docs.db')
c = conn.cursor()

# Create table
c.execute('''CREATE TABLE IF NOT EXISTS internal_methodsim
		(first_id INT, second_id INT, sim_cs REAL, sim_tok REAL DEFAULT -1,
			PRIMARY KEY (first_id, second_id))''')

c.execute('''CREATE VIEW IF NOT EXISTS methodsim
		(project1, project2, file1, file2, method1, method2, sim_cs, sim_tok) AS
			SELECT p1.name, p2.name, d1.file, d2.file, d1.method, d2.method, s.sim_cs, s.sim_tok
				FROM internal_methodsim s JOIN internal_filtered_methoddocs d1 ON s.first_id = d1.id
					JOIN projects p1 ON d1.project_id = p1.id
					JOIN internal_filtered_methoddocs d2 ON s.second_id = d2.id
					JOIN projects p2 ON d2.project_id = p2.id''')

print("Build corpus")
c.execute("SELECT kwset FROM internal_filtered_methoddocs")

vect = vectorizer.get_vectorizer([ row[0] for row in c.fetchall() ], ('var', 1e-08), 'ppmicds', ('none',), False, 0.9, False, False, 3)

print("Calculate similarity")
pool = Pool()

c.execute('SELECT coalesce(max(first_id), -1) FROM internal_methodsim')
max_proc_id = int(c.fetchone()[0])

# Iterate over projects
c.execute('''SELECT id, name FROM projects''')
for tpproject in c.fetchall():
	project_id = tpproject[0]
	project = tpproject[1]
	start_time = time.time()
	print("Begin project " + project, file=sys.stderr)
	# Check whether project has already been processed
	c.execute('''SELECT count(*) FROM internal_filtered_methoddocs
		WHERE project_id = ? AND id > ?''', (project_id, max_proc_id))
	if int(c.fetchone()[0]) == 0:
		print("Skipping project " + project)
		sys.stdout.flush()
		continue

	# Get all methods from the project
	c.execute('''SELECT id, project_id, file, method, kwset FROM internal_filtered_methoddocs
			WHERE project_id = ? AND id > ?''', (project_id, max_proc_id))
	projmethods = c.fetchall()

	c.execute('''SELECT id, project_id, file, method, kwset FROM internal_filtered_methoddocs
			WHERE project_id >= ?''', (project_id, ))
	othermethods = c.fetchall()

	projwordslist = list()
	for projmethodrow in projmethods:
		words1 = vect.transform(np.asarray([projmethodrow[4]]))
		projwordslist.append((projmethodrow[0], words1))

	inputs = list()
	current = list()
	for othermethodrow in othermethods:
		words2 = vect.transform(np.asarray([othermethodrow[4]]))
		current.append((othermethodrow[0], words2))
		if len(current) >= 64:
			inputs.append((project, projwordslist, current))
			current = list()
		
	if len(current) > 0:
		inputs.append((project, projwordslist, current))

	counter = 0
	for (pr, result) in pool.imap_unordered(calc_proj_sim, inputs):
		c.executemany('''INSERT INTO internal_methodsim VALUES (?, ?, ?, -1)''', result)
		counter += 1
		if counter > 100:
			conn.commit()
			counter = 0

	conn.commit()
	end_time = time.time()
	print("Finished " + project + " in " + str(end_time - start_time) + " s")
	sys.stdout.flush()

conn.close()
