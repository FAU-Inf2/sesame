from math import log

import numpy as np
from scipy.sparse import coo_matrix, find

from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.feature_extraction.text import CountVectorizer

class PPMIVectorizer(BaseEstimator, TransformerMixin):
    """A PPMI vectorizer that is compatible with scikit-learn."""

    def __init__(self, alpha=1.0, **kwargs):
        self.__cv = CountVectorizer(**kwargs)
        self.__col_sums = None
        self.__total_sum = None
        self.__alpha = alpha

    def fit(self, X, y=None, **fit_params):
        c_matrix = self.__cv.fit_transform(X).tocsc()
        if self.__alpha == 1.0:
            self.__col_sums = c_matrix.sum(0)
        else:
            self.__col_sums = np.power(c_matrix.sum(0), self.__alpha)
        self.__total_sum = self.__col_sums.sum()

    def transform(self, X, y=None, **fit_params):
        matrix = self.__cv.transform(X)
        data = np.empty(matrix.getnnz())
        rowsums = matrix.sum(1)
        (I, J, V) = find(matrix)
        for i in range(0, matrix.getnnz()):
            v = (self.__total_sum * V[i]) / (rowsums[I[i], 0] * self.__col_sums[0, J[i]])
            data[i] = max(0, log(max(1, v)))
        return coo_matrix((data, (I, J)), shape=matrix.get_shape()).tocsr()

    def fit_transform(self, X, y=None, **fit_params):
        self.fit(X)
        return self.transform(X)


