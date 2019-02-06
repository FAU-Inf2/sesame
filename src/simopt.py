#!/usr/bin/env python3

import csv
import itertools
import math
import re
import sqlite3
import sys
import tempfile

import numpy as np

from scipy.sparse import isspmatrix, csr_matrix

from sklearn.metrics.pairwise import cosine_similarity

import pso
import vectorizer

# Configuration
FSELECT_VALUES = [("all",), ("var", 1E-8), ("var", 1E-7), ("var", 1E-6), ("var", 1E-5), ("var", 1E-4), ("var", 1E-3)]
VSM_VALUES = ["tfidf", "ppmi", "ppmicds"]
TSIM_VALUES = [
    ("none", ),
    ("lsa", 25), ("lsa", 50), ("lsa", 75), ("lsa", 100), ("lsa", 150), ("lsa", 200), ("lsa", 300), ("lsa", 400), ("lsa", 500), ("lsa", 750), ("lsa", 1000),
    ("srp", 25), ("srp", 50), ("srp", 75), ("srp", 100), ("srp", 150), ("srp", 200), ("srp", 300), ("srp", 400), ("srp", 500), ("srp", 750), ("srp", 1000),
    ("lda", 25), ("lda", 50), ("lda", 75), ("lda", 100), ("lda", 125), ("lda", 150), ("lda", 200), ("lda", 250), ("lda", 300), #("lda", 400), ("lda", 500), ("lda", 750), ("lda", 1000),                             #(Too long)
    #("kpca", 25), ("kpca", 50), ("kpca", 75), ("kpca", 100), ("kpca", 150), ("kpca", 200), ("kpca", 300), ("kpca", 400), ("kpca", 500), ("kpca", 750), ("kpca", 1000), ("kpca", None),  #(Too much memory)
    #("ica", 25), ("ica", 50), ("ica", 75), ("ica", 100), ("ica", 150), ("ica", 200), ("ica", 300), ("ica", 400), ("ica", 500), ("ica", 750), ("ica", 1000), ("ica", None),              #(Too much memory)
    ("nmf", 25), ("nmf", 50), ("nmf", 75), ("nmf", 100), ("nmf", 150), ("nmf", 200),#, ("nmf", 300), ("nmf", 400), ("nmf", 500), ("nmf", 750), ("nmf", 1000), ("nmf", None)               #(Too long)
    ("word2vec", 50), ("word2vec", 100), ("word2vec", 150), ("word2vec", 200), ("word2vec", 300), ("word2vec", 500),
    ("doc2vec", 50), ("doc2vec", 100), ("doc2vec", 150), ("doc2vec", 200), ("doc2vec", 300), ("doc2vec", 500),
    ]
STOP_WORDS_VALUES = [False]
MAX_DF_VALUES = [0.7, 0.8, 0.9, 1.0]
LOWERCASE_VALUES = [True, False]
NORMALIZER_VALUES = [True, False]
NGRAM_VALUES = [1, 2, 3]


# Helper

dataset = None

def get_filename(classname):
    dotpos = classname.find(".")
    if dotpos < 0:
        return classname + ".java"
    return classname[:dotpos] + ".java"

# Open DB connection
conn = sqlite3.connect("./docs-train.db")
c = conn.cursor()

# Get dataset
c.execute("SELECT kwset FROM internal_filtered_methoddocs")
dataset = [ row[0] for row in c.fetchall() ]

# Parse input sample
samples = list()
with open(sys.argv[1], "r", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        filename1 = get_filename(row["class1"])
        c.execute("""SELECT kwset
                FROM internal_filtered_methoddocs d JOIN projects p ON d.project_id = p.id
                WHERE p.name = ? AND d.file like ? AND method = ?""",
            (row["project1"], "%/" + filename1, row["class1"] + "." + row["method1"]))
        try:
            kwset1 = c.fetchone()[0]
        except:
            print(row["project1"] + ":" + row["class1"] + "#" + row["method1"])
            raise
        filename2 = get_filename(row["class2"])
        c.execute("""SELECT kwset
                FROM internal_filtered_methoddocs d JOIN projects p ON d.project_id = p.id
                WHERE p.name = ? AND d.file like ? AND method = ?""",
            (row["project2"], "%/" + filename2, row["class2"] + "." + row["method2"]))
        try:
            kwset2 = c.fetchone()[0]
        except:
            print(row["project2"] + ":" + row["class2"] + "#" + row["method2"])
            raise
        samples.append((kwset1, kwset2, float(row["cat"])))


# OPTIMIZATION
def exhaustive_opt(samples):
    best = None
    best_val = float("inf")
    for (fselect, vsm, tsim, stop_words, max_df, lowercase, normalizer, ngram) in itertools.product(FSELECT_VALUES, VSM_VALUES, TSIM_VALUES, STOP_WORDS_VALUES, MAX_DF_VALUES, LOWERCASE_VALUES, NORMALIZER_VALUES, NGRAM_VALUES):
        vect = vectorizer.get_vectorizer(dataset, fselect, vsm, tsim, stop_words, max_df, lowercase, normalizer, ngram)
        sse = 0
        for (w1, w2, cat) in samples:
            inp = np.asarray([w1, w2])
            outp = vect.transform(inp)
            if not isspmatrix(outp):
                outp = csr_matrix(outp)
            sim = float(cosine_similarity(outp[0], outp[1]))
            sse += (sim - cat) * (sim - cat)
        print("(" + str(vsm) + ", " + str(tsim) + ", " + str(stop_words) + ", " + str(max_df) + ", " + str(lowercase) + ", " + str(normalizer) + ", " + str(ngram) + "): " + str(sse))
        if sse < best_val:
            best = (tsim, stop_words, max_df, lowercase, normalizer, ngram)
            best_val = sse
    return best


def pso_opt(samples):
    def pso_qual(p):
        (fselect, vsm, tsim, stop_words, max_df, lowercase, normalizer, ngram) = p
        try:
            vect = vectorizer.get_vectorizer(dataset, fselect, vsm, tsim, stop_words, max_df, lowercase, normalizer, ngram)
        except ValueError:
            return float("-inf")
        tp = 0
        tn = 0
        fp = 0
        fn = 0
        for (w1, w2, cat) in samples:
            inp = np.asarray([w1, w2])
            outp = vect.transform(inp)
            if not isspmatrix(outp):
                outp = csr_matrix(outp)
            sim = float(cosine_similarity(outp[0], outp[1]))
            if cat < 0.5:
                if sim < 0.2:
                    tn += 1
                else:
                    fp += 1
            else:
                if sim > 0.8:
                    tp += 1
                else:
                    fn += 1
        assert tp + fp + tn + fn == len(samples)
        ### Precision ###
        if tp + fp == 0:
            return 0.0
        return float(tp) / (tp + fp)

    opt = pso.ParticleSwarmAdapter(pso.ParticleSwarmOptimizer,
        [ FSELECT_VALUES, VSM_VALUES, TSIM_VALUES, STOP_WORDS_VALUES, MAX_DF_VALUES, LOWERCASE_VALUES, NORMALIZER_VALUES, NGRAM_VALUES ],
        pso.CacheQuality(pso_qual),
        pso.OrTermination(pso.NoBestChangeForNIterations(25), pso.FixedQualityReached(1.0)),
        0.729, 2.05, 2.05,
        pso.StretchingAdapterBuilder(pso.RingTopologyBestPosition, 100, 1, 1e-9))
    return opt.optimize(20)


best = pso_opt(samples)
print("BEST: " + str(best))
