#!/usr/bin/python3

import random
import sqlite3

import numpy as np

from scipy.sparse import isspmatrix, csr_matrix

from sklearn.metrics.pairwise import cosine_similarity

import vectorizer



# Open DB connection
conn = sqlite3.connect("./docs-train.db")
c = conn.cursor()

# Get vectorizer
c.execute("SELECT kwset FROM internal_filtered_methoddocs")
whole = [ row[0] for row in c.fetchall() ]

vect0 = vectorizer.get_vectorizer(whole, ('all',), 'ppmi', ('lsa', 200), False, 1.0, False, False, 1)
vect1 = vectorizer.get_vectorizer(whole, ('all',), 'ppmi', ('lsa', 150), False, 1.0, True, False, 1)
vect2 = vectorizer.get_vectorizer(whole, ('var', 0.0015), 'ppmi', ('lsa', 500), False, 0.7, True, True, 2)
vect3 = vectorizer.get_vectorizer(whole, ('all',), 'ppmi', ('none',), False, 1.0, True, False, 1)
vect4 = vectorizer.get_vectorizer(whole, ('var', 1e-08), 'ppmicds', ('none',), False, 0.9, False, False, 3)
vect5 = vectorizer.get_vectorizer(whole, ('all',), 'ppmi', ('lda', 350), False, 0.8, True, False, 3)

vects = [vect0, vect1, vect2, vect3, vect4, vect5]

c.execute("SELECT id FROM internal_filtered_methoddocs WHERE project_id != 7 AND project_id != 12")
id_list = [ r[0] for r in c.fetchall() ]
random.shuffle(id_list)

black = set()

found = 0
tested = 0
finish = False
for j in id_list:
    finish = True
    c.execute("""SELECT d1.file, d1.method, d1.kwset, d2.file, d2.method, d2.kwset
                 FROM internal_filtered_methoddocs d1, internal_filtered_methoddocs d2
                 WHERE d1.id = ? AND d1.project_id < d2.project_id AND d2.project_id != 7
                 AND d2.project_id != 12
                 ORDER BY RANDOM() LIMIT 10000""",
              (j, ))
    for (file1, method1, kwset1, file2, method2, kwset2) in c:
        finish = False
        if (file1, method1) not in black and (file2, method2) not in black:
            if (tested % 8) == 0:
                print("\r" + str(tested), end="")

            sims = list()
            for vect in vects:
                inp = np.asarray([kwset1, kwset2])
                outp = vect.transform(inp)
                if not isspmatrix(outp):
                    outp = csr_matrix(outp)
                sims.append(float(cosine_similarity(outp[0], outp[1])))

            tested += 1

            if min(sims) < 0.2 and max(sims) > 0.8:
                found += 1
                print("\r" + str(found) + ") " + file1 + "#" + method1 + " <-> " + file2 + "#" + method2)
                for i in range(0, len(sims)):
                    if sims[i] < 0.2:
                        print(str(i) + " ", end="")
                print("; ", end="")
                for i in range(0, len(sims)):
                    if sims[i] > 0.8:
                        print(str(i) + " ", end="")
                print("\n")
                black.add((file1, method1))
                black.add((file2, method2))
                break
