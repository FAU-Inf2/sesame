# SeSaMe

This is the source code we used to generate the data set presented in our
publication

Kamp, M., Kreutzer P., Philippsen M.: SeSaMe: A Data Set of Semantically
Similar Java Methods. 16th International Conference on Mining Software
Repositories (MSR 2019), Montreal, QC, Canada. 2019

The following description assumes knowledge of our methodology, which is
described in the paper.


## Requirements

To build the data set, the following software is required:

* Some unixoid operating system (we ran the tools on Fedora 28, but other Linux
  distributions with compatible software should also work)
* GNU make
* Java (at least version 8)
* Python 3 and Pip
* Python VirtualEnv
* SQLite 3
* Git
* Mercurial

The necessary Java and Python dependencies are automatically
downloaded/installed from remote repositories (except for the Eclipse JDT
libraries, which were not present in Maven Central at the time of the data set
creation).


## Training a Language Model

`make simopt` starts the particle swarm optimization to find a transformation
of the JavaDoc comments into a vector.

We performed the particle swarm optimization on older versions and a slightly
different selection of the projects. This is automatically cloned by `make
simopt`.

Finally, `make crossopt` compares a preconfigured selection of similarity
computation pipelines by sampling the database. These must be put manually into
the file crossopt.py.


## Creating the Data Set

Theoretically it is sufficient to just run `make` in this directory. Please
note that the similarity computation, however, takes **very** long (depending
on your hardware, it could take a month or longer). The sampling process also
requires a lot of memory (we set the maximal heap size to 32 GB, so pay
attention if you have less memory). To reduce memory consumption, you may
increase the constant `Sample.SIM_THRSH` to cut off similarity values below
that threshold. Note that this could alter the results! Also note that the
sampling is non-deterministic! Near the end, the `Makefile` asks you for the
number of method pairs each rater should classify.

Although its execution takes very long, the `Makefile` is a documentation of
the steps we've taken to gather the data for SeSaMe and to prepare the manual
classification. 
