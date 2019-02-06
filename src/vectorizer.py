import re
import tempfile

from typing import *

import numpy as np

from gensim.sklearn_api import D2VTransformer
from gensim.sklearn_api import W2VTransformer

from sklearn.base import BaseEstimator
from sklearn.decomposition import FastICA
from sklearn.decomposition import LatentDirichletAllocation
from sklearn.decomposition import KernelPCA
from sklearn.decomposition import NMF
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.feature_selection import VarianceThreshold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import FunctionTransformer
from sklearn.preprocessing import Normalizer
from sklearn.random_projection import SparseRandomProjection
from sklearn.svm import LinearSVC

import ppmi


def _tokenize(X, y=None):
    return [ re.compile(r"(?u)\b\w\w+\b").findall(doc) for doc in X.tolist() ]


def get_vectorizer(dataset: List[str], fselect: Tuple[str, ...], vsm: str, tsim: Tuple[str, ...], use_stop_words: bool, max_df: float, lowercase: bool, use_normalizer: bool, ngram: int) -> BaseEstimator:
    try:
        def get_vsmvec(vsm):
            if vsm == "tfidf":
                return TfidfVectorizer
            elif vsm == "ppmi":
                return ppmi.PPMIVectorizer
            elif vsm == "ppmicds":
                return lambda **kwargs: ppmi.PPMIVectorizer(0.75, **kwargs)
            else:
                raise Exception("Unknown vsm: " + vsm)

        pretrans = None # No preprocessing used here

        tid = tsim[0]
        if tid in ["none", "lsa", "kpca", "lda", "ica", "nmf", "srp"]:
            if use_stop_words:
                tfidf = get_vsmvec(vsm)(stop_words = "english", lowercase = lowercase, ngram_range=(ngram, ngram))
            else:
                tfidf = get_vsmvec(vsm)(max_df = max_df, lowercase = lowercase, ngram_range=(ngram, ngram))
            if pretrans != None:
                tfidf = make_pipeline(pretrans, tfidf)

            if fselect[0] == "var":
                tfidf = make_pipeline(tfidf, VarianceThreshold(threshold=fselect[1]))
            elif fselect[0] != "all":
                raise Exception("Unknown feature selector: " + fselect[0])

            inp = np.asarray(dataset)
            if tid == "none":
                tfidf.fit(inp)
                if use_normalizer:
                    return make_pipeline(tfidf, Normalizer())
                else:
                    return tfidf
            elif tid == "lsa":
                lsa = TruncatedSVD(n_components = tsim[1], random_state = 410)
                out = tfidf.fit_transform(inp)
                lsa.fit(out)
                if use_normalizer:
                    return make_pipeline(tfidf, lsa, Normalizer())
                else:
                    return make_pipeline(tfidf, lsa)
            elif tid == "kpca":
                kpca = KernelPCA(n_components = tsim[1], copy_X = False)
                out = tfidf.fit_transform(inp)
                kpca.fit(out)
                if use_normalizer:
                    return make_pipeline(tfidf, kpca, Normalizer())
                else:
                    return make_pipeline(tfidf, kpca)
            elif tid == "lda":
                lda = LatentDirichletAllocation(n_topics = tsim[1], learning_method = "online", batch_size = 16384, learning_decay = 0.8, random_state = 410)
                out = tfidf.fit_transform(inp)
                lda.fit(out)
                if use_normalizer:
                    return make_pipeline(tfidf, lda, Normalizer())
                else:
                    return make_pipeline(tfidf, lda)
            elif tid == "ica":
                ica = FastICA(n_components = tsim[1])
                out = tfidf.fit_transform(inp).todense()
                ica.fit(out)
                if use_normalizer:
                    return make_pipeline(tfidf, ica, Normalizer())
                else:
                    return make_pipeline(tfidf, lda)
            elif tid == "nmf":
                nmf = NMF(n_components = tsim[1], alpha = 0.75, random_state = 410)
                out = tfidf.fit_transform(inp)
                nmf.fit(out)
                if use_normalizer:
                    return make_pipeline(tfidf, nmf, Normalizer())
                else:
                    return make_pipeline(tfidf, nmf)
            elif tid == "srp":
                srp = SparseRandomProjection(n_components = tsim[1], random_state = 410)
                out = tfidf.fit_transform(inp)
                srp.fit(out)
                if use_normalizer:
                    return make_pipeline(tfidf, srp, Normalizer())
                else:
                    return make_pipeline(tfidf, srp)
            else:
                raise Exception("Unknown tid: " + tid)
        elif tid == "word2vec":
            basict = W2VTransformer(size=tsim[1], min_count=1, seed=410, sample=0.0 if max_df >= 1.0 else max_df, workers=1, sg=0 if use_normalizer else 1, window=10 if use_normalizer else 5, hs=1 if ngram <= 2 else 0, negative=0 if ngram < 2 else 10)
            w2vt = FunctionTransformer(func=lambda X, y=None, basict=basict: np.asarray([ sum(basict.transform(doc)) for doc in X ]), validate=False)
            if pretrans != None:
                w2vf = make_pipeline(pretrans, FunctionTransformer(func=_tokenize, validate=False), basict)
                w2vt = make_pipeline(pretrans, FunctionTransformer(func=_tokenize, validate=False), w2vt)
            else:
                w2vf = make_pipeline(FunctionTransformer(func=_tokenize, validate=False), basict)
                w2vt = make_pipeline(FunctionTransformer(func=_tokenize, validate=False), w2vt)
            w2vf.fit(np.asarray(dataset))
            return w2vt
            #return TransformerWrapper(lambda doc, model=model: model[re.sub(r",\s*", "_", doc)])
        elif tid == "doc2vec":
            d2vt = D2VTransformer(size=tsim[1], min_count=1, seed=410, sample=0.0 if max_df >= 1.0 else max_df, workers=1, dm=0 if use_normalizer else 1, window=5, hs=1 if ngram <= 2 else 0, negative=0 if ngram < 2 else 10)
            tokt = FunctionTransformer(func=_tokenize, validate=False)
            if pretrans != None:
                d2vt = make_pipeline(pretrans, tokt, d2vt)
            else:
                d2vt = make_pipeline(tokt, d2vt)
            d2vt.fit(np.asarray(dataset))
            return d2vt
        else:
            raise Exception("Unknown tid: " + str(tid))
    except MemoryError as e:
        print("[E] out of memory on configuration " + vsm + ", " + str(tsim) + ", " + str(use_stop_words) + ", " + str(max_df) + ", " + str(lowercase) + ", " + str(use_normalizer) + ", " + str(ngram))
        raise
