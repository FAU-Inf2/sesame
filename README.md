# SeSaMe

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.2558378.svg)](https://doi.org/10.5281/zenodo.2558378)

This repository contains the data set described in the paper

Kamp, M., Kreutzer P., Philippsen M.: SeSaMe: A Data Set of Semantically
Similar Java Methods. 16th International Conference on Mining Software
Repositories (MSR 2019), Montreal, QC, Canada. 2019

The data set is licenced under a [Creative Commons Attribution 4.0
International Licence](http://creativecommons.org/licenses/by/4.0/).

The repository consists of the following files:

* dataset.json : The final data set in the format described in the paper.
* dataset-unfiltered.json : The data set including the pairs we removed due to disagreement.
* sampled-pairs.csv : The 900 sampled method pairs.
* src : The source code of the tools we used to create the data set.

The relevant data are stored in a single JSON file (dataset.json) that contains
an object describing the used Java projects and a list holding the classified
method pairs. Each list element consists of four components: The pairid that
identifies the method pair, information regarding the first and second method
that this pair consists of, and the goals, operations, and effects rating and
confidence assigned by the participants of the manual classification. A method
is identified by its project, the file it is defined in, and the method
signature.

The database containing the mined methods, their JavaDoc comments and the
computed similarity values is not included in this repository. Use the Zenodo
link above to retrieve it.
