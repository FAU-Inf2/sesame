#!/usr/bin/env python3

from pathlib import Path
from string import Template

import csv
import os.path
import random
import subprocess
import sys


#############################################################################
# HELPER CLASSES                                                            #
#############################################################################

TAG_NAMES = ["html", "head", "title", "link", "style", "script", "body", "h1",
        "h2", "h3", "h4", "h5", "h6", "div", "span", "p", "pre", "code", "ol",
        "ul", "li", "form", "input", "label"]

class HTMLGenerator:
    def __init__(self):
        self.__contents = ""
        for name in TAG_NAMES:
            self.__dict__[name] = lambda n = name, **a: self.__opentag(n, a)
            self.__dict__["_" + name] = lambda n = name: self.__closetag(n)
    
    def __opentag(self, name, attribs = None):
        self.__mktag(name, attribs)
        return self

    def __closetag(self, name):
        self.__mktag("/" + name)
        return self

    def __singletag(self, name, attribs = None):
        self.__mktag(name, attribs, "/")
        return self
    
    def __mktag(self, name, attribs=None, end=""):
        tag_template = Template("<$name$attribs$end>")
        attrib_template = Template(" $aname='$avalue'")
        attribstr = ""
        if attribs != None:
            for key in attribs:
                pkey = key[1:] if key.startswith("_") else key
                attribstr += attrib_template.substitute(aname=pkey, avalue=attribs[key])
        self.__contents += tag_template.substitute(name=name, attribs=attribstr, end=end)
    
    def text(self, text):
        self.__contents += text
        return self
    
    def comment(self, text):
        return self.text("<!-- " + text + "-->")

    def build(self):
        return self.__contents


SOURCEPATHS = {
    "caffeine": "repos/caffeine/caffeine/src/javaPoet/java:repos/caffeine/caffeine/src/jmh/java:repos/caffeine/caffeine/src/main/java:repos/caffeine/caffeine/src/test/java:repos/caffeine/examples/stats-metrics/src/main/java:repos/caffeine/examples/stats-metrics/src/test/java:repos/caffeine/examples/write-behind-rxjava/src/main/java:repos/caffeine/examples/write-behind-rxjava/src/test/java:repos/caffeine/guava/src/main/java:repos/caffeine/guava/src/test/java:repos/caffeine/jcache/src/main/java:repos/caffeine/jcache/src/test/java:repos/caffeine/simulator/src/jmh/java:repos/caffeine/simulator/src/main/java:repos/caffeine/simulator/src/test/java",
    "checkstyle": "repos/checkstyle/src/main/java:repos/checkstyle/src/it/java:repos/checkstyle/src/it/resources:repos/checkstyle/src/test/java:repos/checkstyle/src/test/resources",
    "commons-collections": "repos/commons-collections/src/main/java:repos/commons-collections/src/test/java",
    "commons-lang": "repos/commons-lang/src/main/java",
    "commons-math": "repos/commons-math/src/main/java:repos/commons-math/src/test/java:repos/commons-math/src/test/maxima:repos/commons-math/src/userguide/java",
    "deeplearning4j": "repos/deeplearning4j/rl4j/rl4j-core/src/test/java:repos/deeplearning4j/rl4j/rl4j-core/src/main/java:repos/deeplearning4j/rl4j/rl4j-malmo/src/main/java:repos/deeplearning4j/rl4j/rl4j-ale/src/main/java:repos/deeplearning4j/rl4j/rl4j-gym/src/main/java:repos/deeplearning4j/rl4j/rl4j-api/src/main/java:repos/deeplearning4j/rl4j/rl4j-doom/src/main/java:repos/deeplearning4j/gym-java-client/src/test/java:repos/deeplearning4j/gym-java-client/src/main/java:repos/deeplearning4j/datavec/datavec-geo/src/test/java:repos/deeplearning4j/datavec/datavec-geo/src/main/java:repos/deeplearning4j/datavec/datavec-local/src/test/java:repos/deeplearning4j/datavec/datavec-local/src/main/java:repos/deeplearning4j/datavec/datavec-spark/src/test/java:repos/deeplearning4j/datavec/datavec-spark/src/main/java:repos/deeplearning4j/datavec/datavec-api/src/test/java:repos/deeplearning4j/datavec/datavec-api/src/main/java:repos/deeplearning4j/datavec/datavec-arrow/src/test/java:repos/deeplearning4j/datavec/datavec-arrow/src/main/java:repos/deeplearning4j/datavec/datavec-perf/src/test/java:repos/deeplearning4j/datavec/datavec-perf/src/main/java:repos/deeplearning4j/datavec/datavec-camel/src/test/java:repos/deeplearning4j/datavec/datavec-camel/src/main/java:repos/deeplearning4j/datavec/datavec-excel/src/test/java:repos/deeplearning4j/datavec/datavec-excel/src/main/java:repos/deeplearning4j/datavec/datavec-spark-inference-parent/datavec-spark-inference-server/src/test/java:repos/deeplearning4j/datavec/datavec-spark-inference-parent/datavec-spark-inference-server/src/main/java:repos/deeplearning4j/datavec/datavec-spark-inference-parent/datavec-spark-inference-client/src/test/java:repos/deeplearning4j/datavec/datavec-spark-inference-parent/datavec-spark-inference-client/src/main/java:repos/deeplearning4j/datavec/datavec-spark-inference-parent/datavec-spark-inference-model/src/test/java:repos/deeplearning4j/datavec/datavec-spark-inference-parent/datavec-spark-inference-model/src/main/java:repos/deeplearning4j/datavec/datavec-data/datavec-data-image/src/test/java:repos/deeplearning4j/datavec/datavec-data/datavec-data-image/src/main/java:repos/deeplearning4j/datavec/datavec-data/datavec-data-audio/src/test/java:repos/deeplearning4j/datavec/datavec-data/datavec-data-audio/src/main/java:repos/deeplearning4j/datavec/datavec-data/datavec-data-codec/src/test/java:repos/deeplearning4j/datavec/datavec-data/datavec-data-codec/src/main/java:repos/deeplearning4j/datavec/datavec-data/datavec-data-nlp/src/test/java:repos/deeplearning4j/datavec/datavec-data/datavec-data-nlp/src/main/java:repos/deeplearning4j/datavec/datavec-hadoop/src/test/java:repos/deeplearning4j/datavec/datavec-hadoop/src/main/java:repos/deeplearning4j/datavec/datavec-jdbc/src/test/java:repos/deeplearning4j/datavec/datavec-jdbc/src/main/java:repos/deeplearning4j/nd4j/nd4j-instrumentation/src/main/java:repos/deeplearning4j/nd4j/nd4j-serde/nd4j-grpc/src/test/java:repos/deeplearning4j/nd4j/nd4j-serde/nd4j-grpc/src/main/java:repos/deeplearning4j/nd4j/nd4j-serde/nd4j-gson/src/test/java:repos/deeplearning4j/nd4j/nd4j-serde/nd4j-gson/src/main/java:repos/deeplearning4j/nd4j/nd4j-serde/nd4j-jackson/src/main/java:repos/deeplearning4j/nd4j/nd4j-serde/nd4j-kryo/src/test/java:repos/deeplearning4j/nd4j/nd4j-serde/nd4j-kryo/src/main/java:repos/deeplearning4j/nd4j/nd4j-serde/nd4j-base64/src/main/java:repos/deeplearning4j/nd4j/nd4j-serde/nd4j-camel-routes/nd4j-kafka/src/main/test/java:repos/deeplearning4j/nd4j/nd4j-serde/nd4j-camel-routes/nd4j-kafka/src/main/java:repos/deeplearning4j/nd4j/nd4j-serde/nd4j-arrow/src/test/java:repos/deeplearning4j/nd4j/nd4j-serde/nd4j-arrow/src/main/java:repos/deeplearning4j/nd4j/nd4j-serde/nd4j-aeron/src/test/java:repos/deeplearning4j/nd4j/nd4j-serde/nd4j-aeron/src/main/java:repos/deeplearning4j/nd4j/nd4j-parameter-server-parent/nd4j-parameter-server-node/src/test/java:repos/deeplearning4j/nd4j/nd4j-parameter-server-parent/nd4j-parameter-server-node/src/main/java:repos/deeplearning4j/nd4j/nd4j-parameter-server-parent/nd4j-parameterserver-model/src/main/java:repos/deeplearning4j/nd4j/nd4j-parameter-server-parent/nd4j-parameter-server/src/test/java:repos/deeplearning4j/nd4j/nd4j-parameter-server-parent/nd4j-parameter-server/src/main/java:repos/deeplearning4j/nd4j/nd4j-parameter-server-parent/nd4j-parameter-server-rocksdb-storage/src/test/java:repos/deeplearning4j/nd4j/nd4j-parameter-server-parent/nd4j-parameter-server-rocksdb-storage/src/main/java:repos/deeplearning4j/nd4j/nd4j-parameter-server-parent/nd4j-parameter-server-client/src/test/java:repos/deeplearning4j/nd4j/nd4j-parameter-server-parent/nd4j-parameter-server-client/src/main/java:repos/deeplearning4j/nd4j/nd4j-parameter-server-parent/nd4j-parameter-server-status/src/test/java:repos/deeplearning4j/nd4j/nd4j-parameter-server-parent/nd4j-parameter-server-status/src/main/java:repos/deeplearning4j/nd4j/nd4j-backends/nd4j-tests/src/test/java:repos/deeplearning4j/nd4j/nd4j-backends/nd4j-backend-impls/nd4j-cuda/src/test/java:repos/deeplearning4j/nd4j/nd4j-backends/nd4j-backend-impls/nd4j-cuda/src/main/java:repos/deeplearning4j/nd4j/nd4j-backends/nd4j-backend-impls/nd4j-native/src/test/java:repos/deeplearning4j/nd4j/nd4j-backends/nd4j-backend-impls/nd4j-native/src/main/java:repos/deeplearning4j/nd4j/nd4j-backends/nd4j-api-parent/nd4j-native-api/src/main/java:repos/deeplearning4j/nd4j/nd4j-backends/nd4j-api-parent/nd4j-api/src/main/protobuf/tf/google/protobuf/compiler/java:repos/deeplearning4j/nd4j/nd4j-backends/nd4j-api-parent/nd4j-api/src/main/java:repos/deeplearning4j/nd4j/nd4j-jdbc/nd4j-jdbc-api/src/main/java:repos/deeplearning4j/nd4j/nd4j-jdbc/nd4j-jdbc-hsql/src/test/java:repos/deeplearning4j/nd4j/nd4j-jdbc/nd4j-jdbc-hsql/src/main/java:repos/deeplearning4j/nd4j/nd4j-jdbc/nd4j-jdbc-mysql/src/test/java:repos/deeplearning4j/nd4j/nd4j-jdbc/nd4j-jdbc-mysql/src/main/java:repos/deeplearning4j/nd4j/nd4j-buffer/src/main/java:repos/deeplearning4j/nd4j/nd4j-common/src/test/java:repos/deeplearning4j/nd4j/nd4j-common/src/main/java:repos/deeplearning4j/nd4j/nd4j-context/src/main/java:repos/deeplearning4j/nd4j/nd4j-tensorflow/src/main/java:repos/deeplearning4j/deeplearning4j/deeplearning4j-zoo/src/test/java:repos/deeplearning4j/deeplearning4j/deeplearning4j-zoo/src/main/java:repos/deeplearning4j/deeplearning4j/deeplearning4j-manifold/deeplearning4j-tsne/src/test/java:repos/deeplearning4j/deeplearning4j/deeplearning4j-manifold/deeplearning4j-tsne/src/main/java:repos/deeplearning4j/deeplearning4j/dl4j-integration-tests/src/test/java:repos/deeplearning4j/deeplearning4j/deeplearning4j-common/src/main/java:repos/deeplearning4j/deeplearning4j/deeplearning4j-core/src/test/java:repos/deeplearning4j/deeplearning4j/deeplearning4j-core/src/main/java:repos/deeplearning4j/deeplearning4j/deeplearning4j-modelexport-solr/src/test/java:repos/deeplearning4j/deeplearning4j/deeplearning4j-modelexport-solr/src/main/java:repos/deeplearning4j/deeplearning4j/dl4j-perf/src/test/java:repos/deeplearning4j/deeplearning4j/dl4j-perf/src/main/java:repos/deeplearning4j/deeplearning4j/deeplearning4j-cuda/src/test/java:repos/deeplearning4j/deeplearning4j/deeplearning4j-cuda/src/main/java:repos/deeplearning4j/deeplearning4j/deeplearning4j-dataimport-solrj/src/test/java:repos/deeplearning4j/deeplearning4j/deeplearning4j-dataimport-solrj/src/main/java:repos/deeplearning4j/deeplearning4j/deeplearning4j-util/src/main/java:repos/deeplearning4j/deeplearning4j/deeplearning4j-data/deeplearning4j-utility-iterators/src/main/java:repos/deeplearning4j/deeplearning4j/deeplearning4j-data/deeplearning4j-datavec-iterators/src/main/java:repos/deeplearning4j/deeplearning4j/deeplearning4j-data/deeplearning4j-datasets/src/main/java:repos/deeplearning4j/deeplearning4j/deeplearning4j-nn/src/test/java:repos/deeplearning4j/deeplearning4j/deeplearning4j-nn/src/main/java:repos/deeplearning4j/deeplearning4j/deeplearning4j-modelimport/src/test/java:repos/deeplearning4j/deeplearning4j/deeplearning4j-modelimport/src/main/java:repos/deeplearning4j/deeplearning4j/deeplearning4j-graph/src/test/java:repos/deeplearning4j/deeplearning4j/deeplearning4j-graph/src/main/java:repos/deeplearning4j/deeplearning4j/deeplearning4j-nlp-parent/deeplearning4j-nlp-chinese/src/test/java:repos/deeplearning4j/deeplearning4j/deeplearning4j-nlp-parent/deeplearning4j-nlp-chinese/src/main/java:repos/deeplearning4j/deeplearning4j/deeplearning4j-nlp-parent/deeplearning4j-nlp-korean/src/test/java:repos/deeplearning4j/deeplearning4j/deeplearning4j-nlp-parent/deeplearning4j-nlp-korean/src/main/java:repos/deeplearning4j/deeplearning4j/deeplearning4j-nlp-parent/deeplearning4j-nlp-japanese/src/test/java:repos/deeplearning4j/deeplearning4j/deeplearning4j-nlp-parent/deeplearning4j-nlp-japanese/src/main/java:repos/deeplearning4j/deeplearning4j/deeplearning4j-nlp-parent/deeplearning4j-nlp/src/test/java:repos/deeplearning4j/deeplearning4j/deeplearning4j-nlp-parent/deeplearning4j-nlp/src/main/java:repos/deeplearning4j/deeplearning4j/deeplearning4j-nlp-parent/deeplearning4j-nlp-uima/src/test/java:repos/deeplearning4j/deeplearning4j/deeplearning4j-nlp-parent/deeplearning4j-nlp-uima/src/main/java:repos/deeplearning4j/deeplearning4j/deeplearning4j-nearestneighbors-parent/deeplearning4j-nearestneighbor-server/src/test/java:repos/deeplearning4j/deeplearning4j/deeplearning4j-nearestneighbors-parent/deeplearning4j-nearestneighbor-server/src/main/java:repos/deeplearning4j/deeplearning4j/deeplearning4j-nearestneighbors-parent/nearestneighbor-core/src/test/java:repos/deeplearning4j/deeplearning4j/deeplearning4j-nearestneighbors-parent/nearestneighbor-core/src/main/java:repos/deeplearning4j/deeplearning4j/deeplearning4j-nearestneighbors-parent/deeplearning4j-nearestneighbors-model/src/main/java:repos/deeplearning4j/deeplearning4j/deeplearning4j-nearestneighbors-parent/deeplearning4j-nearestneighbors-client/src/main/java:repos/deeplearning4j/deeplearning4j/deeplearning4j-ui-parent/deeplearning4j-ui/src/test/java:repos/deeplearning4j/deeplearning4j/deeplearning4j-ui-parent/deeplearning4j-ui/src/main/java:repos/deeplearning4j/deeplearning4j/deeplearning4j-ui-parent/deeplearning4j-ui-model/src/test/java:repos/deeplearning4j/deeplearning4j/deeplearning4j-ui-parent/deeplearning4j-ui-model/src/main/java:repos/deeplearning4j/deeplearning4j/deeplearning4j-ui-parent/deeplearning4j-ui-model/src/main/java/org/deeplearning4j/ui/stats/impl/java:repos/deeplearning4j/deeplearning4j/deeplearning4j-ui-parent/deeplearning4j-ui-components/src/test/java:repos/deeplearning4j/deeplearning4j/deeplearning4j-ui-parent/deeplearning4j-ui-components/src/main/java:repos/deeplearning4j/deeplearning4j/deeplearning4j-ui-parent/deeplearning4j-play/src/test/java:repos/deeplearning4j/deeplearning4j/deeplearning4j-ui-parent/deeplearning4j-play/src/main/java:repos/deeplearning4j/deeplearning4j/deeplearning4j-scaleout/deeplearning4j-scaleout-parallelwrapper/src/test/java:repos/deeplearning4j/deeplearning4j/deeplearning4j-scaleout/deeplearning4j-scaleout-parallelwrapper/src/main/java:repos/deeplearning4j/deeplearning4j/deeplearning4j-scaleout/deeplearning4j-scaleout-parallelwrapper-parameter-server/src/test/java:repos/deeplearning4j/deeplearning4j/deeplearning4j-scaleout/deeplearning4j-scaleout-parallelwrapper-parameter-server/src/main/java:repos/deeplearning4j/deeplearning4j/deeplearning4j-scaleout/deeplearning4j-aws/src/main/java:repos/deeplearning4j/deeplearning4j/deeplearning4j-scaleout/spark/dl4j-spark-nlp-java8/src/test/java:repos/deeplearning4j/deeplearning4j/deeplearning4j-scaleout/spark/dl4j-spark-nlp-java8/src/main/java:repos/deeplearning4j/deeplearning4j/deeplearning4j-scaleout/spark/dl4j-spark-ml/src/test/java:repos/deeplearning4j/deeplearning4j/deeplearning4j-scaleout/spark/dl4j-spark-nlp/src/test/java:repos/deeplearning4j/deeplearning4j/deeplearning4j-scaleout/spark/dl4j-spark-nlp/src/main/java:repos/deeplearning4j/deeplearning4j/deeplearning4j-scaleout/spark/dl4j-spark-parameterserver/src/test/java:repos/deeplearning4j/deeplearning4j/deeplearning4j-scaleout/spark/dl4j-spark-parameterserver/src/main/java:repos/deeplearning4j/deeplearning4j/deeplearning4j-scaleout/spark/dl4j-spark/src/test/java:repos/deeplearning4j/deeplearning4j/deeplearning4j-scaleout/spark/dl4j-spark/src/main/spark-1/java:repos/deeplearning4j/deeplearning4j/deeplearning4j-scaleout/spark/dl4j-spark/src/main/java:repos/deeplearning4j/deeplearning4j/deeplearning4j-scaleout/spark/dl4j-spark/src/main/spark-2/java:repos/deeplearning4j/arbiter/arbiter-deeplearning4j/src/test/java:repos/deeplearning4j/arbiter/arbiter-deeplearning4j/src/main/java:repos/deeplearning4j/arbiter/arbiter-server/src/test/java:repos/deeplearning4j/arbiter/arbiter-server/src/main/java:repos/deeplearning4j/arbiter/arbiter-ui/src/test/java:repos/deeplearning4j/arbiter/arbiter-ui/src/main/java:repos/deeplearning4j/arbiter/arbiter-core/src/test/java:repos/deeplearning4j/arbiter/arbiter-core/src/main/java",
    "eclipse.jdt.core": "repos/eclipse.jdt.core/org.eclipse.jdt.annotation/src:repos/eclipse.jdt.core/org.eclipse.jdt.apt.core/src:repos/eclipse.jdt.core/org.eclipse.jdt.apt.pluggable.core/src:repos/eclipse.jdt.core/org.eclipse.jdt.apt.pluggable.tests/src:repos/eclipse.jdt.core/org.eclipse.jdt.apt.tests/src:repos/eclipse.jdt.core/org.eclipse.jdt.apt.ui/src:repos/eclipse.jdt.core/org.eclipse.jdt.compiler.apt/src:repos/eclipse.jdt.core/org.eclipse.jdt.compiler.apt.tests/src:repos/eclipse.jdt.core/org.eclipse.jdt.compiler.apt.tests/processors:repos/eclipse.jdt.core/org.eclipse.jdt.core.tests.builder/src:repos/eclipse.jdt.core/org.eclipse.jdt.core.tests.compiler/src:repos/eclipse.jdt.core/org.eclipse.jdt.core.tests.model/src:repos/eclipse.jdt.core/org.eclipse.jdt.core.tests.model/workspace/Compiler/src:repos/eclipse.jdt.core/org.eclipse.jdt.core.tests.model/workspace/Converter/src:repos/eclipse.jdt.core/org.eclipse.jdt.core.tests.model/workspace/JavaSearch/src:repos/eclipse.jdt.core/org.eclipse.jdt.core/batch:repos/eclipse.jdt.core/org.eclipse.jdt.core/codeassist:repos/eclipse.jdt.core/org.eclipse.jdt.core/compiler:repos/eclipse.jdt.core/org.eclipse.jdt.core/dom:repos/eclipse.jdt.core/org.eclipse.jdt.core/eval:repos/eclipse.jdt.core/org.eclipse.jdt.core/formatter:repos/eclipse.jdt.core/org.eclipse.jdt.core/model:repos/eclipse.jdt.core/org.eclipse.jdt.core/search",
    "freemind": "repos/freemind",
    "guava": "repos/guava/guava/src:repos/guava/guava-testlib/src:repos/guava/guava-tests/benchmark:repos/guava/guava-tests/test",
    #"hsqldb": "repos/hsqldb/base-one/trunk/src:repos/hsqldb/base/trunk/doc-src/verbatim/src:repos/hsqldb/base/trunk/src:repos/hsqldb/base/trunk/test-src:repos/hsqldb/dotnet/trunk/System.Data.Hsqldb/Lib/Etc/hsqldb-glue/src",
    #"jEdit": "source_code/jEdit",
    #"openjdk8": "repos/openjdk8/make/src/classes:repos/openjdk8/src/macosx/classes:repos/openjdk8/src/macosx/native/jobjc/src/generator/java:repos/openjdk8/src/share/classes:repos/openjdk8/src/share/demo/applets:repos/openjdk8/src/share/demo/java2d:repos/openjdk8/src/share/demo/jfc:repos/openjdk8/src/share/sample/annotations/DependencyChecker/PluginChecker/src:repos/openjdk8/src/share/sample/annotations/DependencyChecker/Plugins/src:repos/openjdk8/src/share/sample/annotations/Validator/src:repos/openjdk8/src/share/sample/jmx/jmx-scandir/src:repos/openjdk8/src/share/sample/lambda/BulkDataOperations/src:repos/openjdk8/src/share/sample/lambda/DefaultMethods:repos/openjdk8/src/share/sample/nio/chatserver:repos/openjdk8/src/share/sample/nio/file:repos/openjdk8/src/share/sample/nio/multicast:repos/openjdk8/src/share/sample/nio/server:repos/openjdk8/src/share/sample/try-with-resources/src:repos/openjdk8/src/solaris/classes:repos/openjdk8/src/solaris/demo/jni/Poller:repos/openjdk8/src/windows/classes:repos/openjdk8/test:repos/openjdk8/test/tools/pack200",
    "openjdk11": "repos/openjdk11/src/jdk.jdi/windows/classes:repos/openjdk11/src/jdk.jdi/share/classes:repos/openjdk11/src/jdk.jartool/share/classes:repos/openjdk11/src/java.base/linux/classes:repos/openjdk11/src/java.base/windows/classes:repos/openjdk11/src/java.base/aix/classes:repos/openjdk11/src/java.base/solaris/classes:repos/openjdk11/src/java.base/share/classes:repos/openjdk11/src/java.base/unix/classes:repos/openjdk11/src/java.base/macosx/classes:repos/openjdk11/src/java.smartcardio/windows/classes:repos/openjdk11/src/java.smartcardio/share/classes:repos/openjdk11/src/java.smartcardio/unix/classes:repos/openjdk11/src/jdk.management.agent/windows/classes:repos/openjdk11/src/jdk.management.agent/share/classes:repos/openjdk11/src/jdk.management.agent/unix/classes:repos/openjdk11/src/java.net.http/share/classes:repos/openjdk11/src/jdk.crypto.cryptoki/share/classes:repos/openjdk11/src/java.prefs/windows/classes:repos/openjdk11/src/java.prefs/share/classes:repos/openjdk11/src/java.prefs/share/classes:repos/openjdk11/src/java.prefs/unix/classes:repos/openjdk11/src/java.prefs/macosx/classes:repos/openjdk11/src/jdk.net/linux/classes:repos/openjdk11/src/jdk.net/solaris/classes:repos/openjdk11/src/jdk.net/share/classes:repos/openjdk11/src/jdk.net/share/classes:repos/openjdk11/src/jdk.net/macosx/classes:repos/openjdk11/src/jdk.scripting.nashorn/share/classes:repos/openjdk11/src/sample/nashorn:repos/openjdk11/src/jdk.naming.dns/share/classes:repos/openjdk11/src/jdk.javadoc/share/classes:repos/openjdk11/src/jdk.xml.dom/share/classes:repos/openjdk11/src/jdk.jconsole/share/classes:repos/openjdk11/src/jdk.unsupported.desktop/share/classes:repos/openjdk11/src/jdk.accessibility/share/classes:repos/openjdk11/src/jdk.security.auth/share/classes:repos/openjdk11/src/jdk.security.jgss/share/classes:repos/openjdk11/src/jdk.management.jfr/share/classes:repos/openjdk11/src/java.naming/share/classes:repos/openjdk11/src/jdk.charsets/share/classes:repos/openjdk11/src/hotspot/share/prims:repos/openjdk11/src/jdk.aot/share/classes/jdk.tools.jaotc.binformat/src:repos/openjdk11/src/jdk.aot/share/classes/jdk.tools.jaotc/src:repos/openjdk11/src/jdk.aot/share/classes:repos/openjdk11/src/java.desktop/windows/classes:repos/openjdk11/src/java.desktop/aix/classes:repos/openjdk11/src/java.desktop/solaris/classes:repos/openjdk11/src/java.desktop/share/classes:repos/openjdk11/src/java.desktop/unix/classes:repos/openjdk11/src/java.desktop/macosx/classes:repos/openjdk11/src/jdk.jdwp.agent/share/classes:repos/openjdk11/src/jdk.jshell/share/classes:repos/openjdk11/src/java.security.jgss/windows/classes:repos/openjdk11/src/java.security.jgss/share/classes:repos/openjdk11/src/jdk.hotspot.agent/test/libproc:repos/openjdk11/src/jdk.hotspot.agent/share/classes:repos/openjdk11/src/java.xml/share/classes:repos/openjdk11/src/jdk.zipfs/share/classes:repos/openjdk11/src/java.datatransfer/share/classes:repos/openjdk11/src/jdk.jcmd/share/classes:repos/openjdk11/src/jdk.attach/linux/classes:repos/openjdk11/src/jdk.attach/windows/classes:repos/openjdk11/src/jdk.attach/aix/classes:repos/openjdk11/src/jdk.attach/solaris/classes:repos/openjdk11/src/jdk.attach/share/classes:repos/openjdk11/src/jdk.attach/macosx/classes:repos/openjdk11/src/jdk.jfr/share/classes:repos/openjdk11/src/utils/IdealGraphVisualizer/SelectionCoordinator/src:repos/openjdk11/src/utils/IdealGraphVisualizer/ServerCompiler/src:repos/openjdk11/src/utils/IdealGraphVisualizer/FilterWindow/src:repos/openjdk11/src/utils/IdealGraphVisualizer/Filter/src:repos/openjdk11/src/utils/IdealGraphVisualizer/HierarchicalLayout/src:repos/openjdk11/src/utils/IdealGraphVisualizer/Data/test/unit/src:repos/openjdk11/src/utils/IdealGraphVisualizer/Data/src:repos/openjdk11/src/utils/IdealGraphVisualizer/BatikSVGProxy/src:repos/openjdk11/src/utils/IdealGraphVisualizer/View/src:repos/openjdk11/src/utils/IdealGraphVisualizer/ControlFlow/src:repos/openjdk11/src/utils/IdealGraphVisualizer/Settings/src:repos/openjdk11/src/utils/IdealGraphVisualizer/NetworkConnection/src:repos/openjdk11/src/utils/IdealGraphVisualizer/Bytecodes/src:repos/openjdk11/src/utils/IdealGraphVisualizer/Util/src:repos/openjdk11/src/utils/IdealGraphVisualizer/Difference/src:repos/openjdk11/src/utils/IdealGraphVisualizer/Graph/src:repos/openjdk11/src/utils/IdealGraphVisualizer/Layout/src:repos/openjdk11/src/utils/IdealGraphVisualizer/Graal/src:repos/openjdk11/src/utils/IdealGraphVisualizer/Coordinator/src:repos/openjdk11/src/utils/src:repos/openjdk11/src/utils/LogCompilation/src/test/java:repos/openjdk11/src/utils/LogCompilation/src/main/java:repos/openjdk11/src/utils/reorder/tests:repos/openjdk11/src/utils/reorder/tools:repos/openjdk11/src/java.instrument/share/classes:repos/openjdk11/src/jdk.pack/share/classes:repos/openjdk11/src/java.sql.rowset/share/classes:repos/openjdk11/src/java.sql/share/classes:repos/openjdk11/src/jdk.internal.vm.ci/share/classes/jdk.vm.ci.code/src:repos/openjdk11/src/jdk.internal.vm.ci/share/classes/jdk.vm.ci.hotspot.amd64/src:repos/openjdk11/src/jdk.internal.vm.ci/share/classes/jdk.vm.ci.aarch64/src:repos/openjdk11/src/jdk.internal.vm.ci/share/classes/jdk.vm.ci.hotspot.sparc/src:repos/openjdk11/src/jdk.internal.vm.ci/share/classes:repos/openjdk11/src/jdk.internal.vm.ci/share/classes/jdk.vm.ci.hotspot/src:repos/openjdk11/src/jdk.internal.vm.ci/share/classes/jdk.vm.ci.sparc/src:repos/openjdk11/src/jdk.internal.vm.ci/share/classes/jdk.vm.ci.common/src:repos/openjdk11/src/jdk.internal.vm.ci/share/classes/jdk.vm.ci.services/src:repos/openjdk11/src/jdk.internal.vm.ci/share/classes/jdk.vm.ci.runtime/src:repos/openjdk11/src/jdk.internal.vm.ci/share/classes/jdk.vm.ci.meta/src:repos/openjdk11/src/jdk.internal.vm.ci/share/classes/jdk.vm.ci.hotspot.aarch64/src:repos/openjdk11/src/jdk.internal.vm.ci/share/classes/jdk.vm.ci.amd64/src:repos/openjdk11/src/java.rmi/share/classes:repos/openjdk11/src/java.se/share/classes:repos/openjdk11/src/jdk.internal.le/share/classes:repos/openjdk11/src/jdk.localedata/share/classes:repos/openjdk11/src/java.logging/share/classes:repos/openjdk11/src/jdk.management/share/classes:repos/openjdk11/src/jdk.unsupported/share/classes:repos/openjdk11/src/java.security.sasl/share/classes:repos/openjdk11/src/java.transaction.xa/share/classes:repos/openjdk11/src/java.compiler/share/classes:repos/openjdk11/src/jdk.internal.ed/share/classes:repos/openjdk11/src/demo/share/java2d/J2DBench/src:repos/openjdk11/src/demo/share/jfc/FileChooserDemo:repos/openjdk11/src/demo/share/jfc/TransparentRuler/transparentruler:repos/openjdk11/src/demo/share/jfc/Font2DTest:repos/openjdk11/src/demo/share/jfc/J2Ddemo/java2d:repos/openjdk11/src/demo/share/jfc/J2Ddemo/java2d/demos/Composite:repos/openjdk11/src/demo/share/jfc/J2Ddemo/java2d/demos/Paths:repos/openjdk11/src/demo/share/jfc/J2Ddemo/java2d/demos/Colors:repos/openjdk11/src/demo/share/jfc/J2Ddemo/java2d/demos/Images:repos/openjdk11/src/demo/share/jfc/J2Ddemo/java2d/demos/Lines:repos/openjdk11/src/demo/share/jfc/J2Ddemo/java2d/demos/Mix:repos/openjdk11/src/demo/share/jfc/J2Ddemo/java2d/demos/Paint:repos/openjdk11/src/demo/share/jfc/J2Ddemo/java2d/demos/Clipping:repos/openjdk11/src/demo/share/jfc/J2Ddemo/java2d/demos/Fonts:repos/openjdk11/src/demo/share/jfc/J2Ddemo/java2d/demos/Arcs_Curves:repos/openjdk11/src/demo/share/jfc/J2Ddemo/java2d/demos/Transforms:repos/openjdk11/src/demo/share/jfc/J2Ddemo/java2d:repos/openjdk11/src/demo/share/jfc/Stylepad:repos/openjdk11/src/demo/share/jfc/Metalworks:repos/openjdk11/src/demo/share/jfc/TableExample:repos/openjdk11/src/demo/share/jfc/SampleTree:repos/openjdk11/src/demo/share/jfc/Notepad:repos/openjdk11/src/demo/share/jfc/CodePointIM/com/sun/inputmethods/internal/codepointim:repos/openjdk11/src/demo/share/jfc/CodePointIM:repos/openjdk11/src/demo/share/jfc/SwingSet2:repos/openjdk11/src/jdk.jlink/share/classes:repos/openjdk11/src/jdk.crypto.ucrypto/solaris/classes:repos/openjdk11/src/jdk.scripting.nashorn.shell/share/classes:repos/openjdk11/src/jdk.internal.opt/share/classes:repos/openjdk11/src/jdk.httpserver/share/classes:repos/openjdk11/src/jdk.jdeps/share/classes:repos/openjdk11/src/jdk.editpad/share/classes:repos/openjdk11/src/jdk.crypto.ec/share/classes:repos/openjdk11/src/jdk.naming.rmi/share/classes:repos/openjdk11/src/jdk.sctp/windows/classes:repos/openjdk11/src/jdk.sctp/aix/classes:repos/openjdk11/src/jdk.sctp/share/classes:repos/openjdk11/src/jdk.sctp/unix/classes:repos/openjdk11/src/jdk.sctp/macosx/classes:repos/openjdk11/src/jdk.internal.vm.compiler/share/classes/org.graalvm.compiler.debug.test/src:repos/openjdk11/src/jdk.internal.vm.compiler/share/classes/org.graalvm.compiler.replacements.amd64/src:repos/openjdk11/src/jdk.internal.vm.compiler/share/classes/org.graalvm.compiler.core.sparc/src:repos/openjdk11/src/jdk.internal.vm.compiler/share/classes/org.graalvm.compiler.hotspot.amd64.test/src:repos/openjdk11/src/jdk.internal.vm.compiler/share/classes/org.graalvm.compiler.jtt/src:repos/openjdk11/src/jdk.internal.vm.compiler/share/classes/org.graalvm.micro.benchmarks/src:repos/openjdk11/src/jdk.internal.vm.compiler/share/classes/org.graalvm.compiler.lir.amd64/src:repos/openjdk11/src/jdk.internal.vm.compiler/share/classes/org.graalvm.compiler.debug/src:repos/openjdk11/src/jdk.internal.vm.compiler/share/classes/org.graalvm.compiler.replacements.test/src:repos/openjdk11/src/jdk.internal.vm.compiler/share/classes/org.graalvm.compiler.microbenchmarks/src:repos/openjdk11/src/jdk.internal.vm.compiler/share/classes/org.graalvm.compiler.nodeinfo.processor/src:repos/openjdk11/src/jdk.internal.vm.compiler/share/classes/org.graalvm.graphio/src:repos/openjdk11/src/jdk.internal.vm.compiler/share/classes/org.graalvm.compiler.loop.phases/src:repos/openjdk11/src/jdk.internal.vm.compiler/share/classes/org.graalvm.compiler.virtual.bench/src:repos/openjdk11/src/jdk.internal.vm.compiler/share/classes/org.graalvm.compiler.hotspot/src:repos/openjdk11/src/jdk.internal.vm.compiler/share/classes/org.graalvm.compiler.lir.sparc/src:repos/openjdk11/src/jdk.internal.vm.compiler/share/classes/jdk.internal.vm.compiler.collections/src:repos/openjdk11/src/jdk.internal.vm.compiler/share/classes/org.graalvm.compiler.replacements.processor/src:repos/openjdk11/src/jdk.internal.vm.compiler/share/classes/org.graalvm.compiler.hotspot.amd64/src:repos/openjdk11/src/jdk.internal.vm.compiler/share/classes/org.graalvm.compiler.runtime/src:repos/openjdk11/src/jdk.internal.vm.compiler/share/classes/org.graalvm.compiler.test/src:repos/openjdk11/src/jdk.internal.vm.compiler/share/classes/org.graalvm.compiler.api.replacements/src:repos/openjdk11/src/jdk.internal.vm.compiler/share/classes/org.graalvm.compiler.asm.amd64.test/src:repos/openjdk11/src/jdk.internal.vm.compiler/share/classes/org.graalvm.compiler.phases.common.test/src:repos/openjdk11/src/jdk.internal.vm.compiler/share/classes/org.graalvm.compiler.core.match.processor/src:repos/openjdk11/src/jdk.internal.vm.compiler/share/classes/org.graalvm.compiler.core/src:repos/openjdk11/src/jdk.internal.vm.compiler/share/classes/org.graalvm.compiler.virtual/src:repos/openjdk11/src/jdk.internal.vm.compiler/share/classes/org.graalvm.compiler.graph/src:repos/openjdk11/src/jdk.internal.vm.compiler/share/classes/org.graalvm.compiler.lir.aarch64/src:repos/openjdk11/src/jdk.internal.vm.compiler/share/classes/org.graalvm.compiler.code/src:repos/openjdk11/src/jdk.internal.vm.compiler/share/classes/org.graalvm.compiler.hotspot.aarch64/src:repos/openjdk11/src/jdk.internal.vm.compiler/share/classes/org.graalvm.compiler.asm.test/src:repos/openjdk11/src/jdk.internal.vm.compiler/share/classes/org.graalvm.compiler.replacements.jdk9.test/src:repos/openjdk11/src/jdk.internal.vm.compiler/share/classes/org.graalvm.compiler.core.aarch64/src:repos/openjdk11/src/jdk.internal.vm.compiler/share/classes:repos/openjdk11/src/jdk.internal.vm.compiler/share/classes/org.graalvm.compiler.lir.jtt/src:repos/openjdk11/src/jdk.internal.vm.compiler/share/classes/org.graalvm.compiler.api.directives/src:repos/openjdk11/src/jdk.internal.vm.compiler/share/classes/org.graalvm.compiler.api.runtime/src:repos/openjdk11/src/jdk.internal.vm.compiler/share/classes/jdk.internal.vm.compiler.word/src:repos/openjdk11/src/jdk.internal.vm.compiler/share/classes/org.graalvm.compiler.options.test/src:repos/openjdk11/src/jdk.internal.vm.compiler/share/classes/org.graalvm.compiler.asm.sparc.test/src:repos/openjdk11/src/jdk.internal.vm.compiler/share/classes/org.graalvm.compiler.hotspot.test/src:repos/openjdk11/src/jdk.internal.vm.compiler/share/classes/org.graalvm.compiler.nodes.test/src:repos/openjdk11/src/jdk.internal.vm.compiler/share/classes/jdk.internal.vm.compiler.collections.test/src:repos/openjdk11/src/jdk.internal.vm.compiler/share/classes/org.graalvm.compiler.bytecode/src:repos/openjdk11/src/jdk.internal.vm.compiler/share/classes/org.graalvm.compiler.phases.common/src:repos/openjdk11/src/jdk.internal.vm.compiler/share/classes/org.graalvm.compiler.phases/src:repos/openjdk11/src/jdk.internal.vm.compiler/share/classes/org.graalvm.compiler.core.amd64.test/src:repos/openjdk11/src/jdk.internal.vm.compiler/share/classes/org.graalvm.compiler.asm.amd64/src:repos/openjdk11/src/jdk.internal.vm.compiler/share/classes/org.graalvm.compiler.nodes/src:repos/openjdk11/src/jdk.internal.vm.compiler/share/classes/org.graalvm.compiler.hotspot.sparc/src:repos/openjdk11/src/jdk.internal.vm.compiler/share/classes/org.graalvm.compiler.api.test/src:repos/openjdk11/src/jdk.internal.vm.compiler/share/classes/org.graalvm.compiler.graph.test/src:repos/openjdk11/src/jdk.internal.vm.compiler/share/classes/org.graalvm.compiler.nodeinfo/src:repos/openjdk11/src/jdk.internal.vm.compiler/share/classes/org.graalvm.compiler.java/src:repos/openjdk11/src/jdk.internal.vm.compiler/share/classes/org.graalvm.compiler.replacements.aarch64/src:repos/openjdk11/src/jdk.internal.vm.compiler/share/classes/org.graalvm.compiler.hotspot.lir.test/src:repos/openjdk11/src/jdk.internal.vm.compiler/share/classes/org.graalvm.util/src:repos/openjdk11/src/jdk.internal.vm.compiler/share/classes/org.graalvm.compiler.core.amd64/src:repos/openjdk11/src/jdk.internal.vm.compiler/share/classes/org.graalvm.compiler.core.test/src:repos/openjdk11/src/jdk.internal.vm.compiler/share/classes/org.graalvm.compiler.options/src:repos/openjdk11/src/jdk.internal.vm.compiler/share/classes/org.graalvm.compiler.asm.sparc/src:repos/openjdk11/src/jdk.internal.vm.compiler/share/classes/org.graalvm.util.test/src:repos/openjdk11/src/jdk.internal.vm.compiler/share/classes/org.graalvm.compiler.hotspot.sparc.test/src:repos/openjdk11/src/jdk.internal.vm.compiler/share/classes/org.graalvm.compiler.asm/src:repos/openjdk11/src/jdk.internal.vm.compiler/share/classes/org.graalvm.compiler.loop.test/src:repos/openjdk11/src/jdk.internal.vm.compiler/share/classes/org.graalvm.compiler.asm.aarch64/src:repos/openjdk11/src/jdk.internal.vm.compiler/share/classes/org.graalvm.compiler.loop/src:repos/openjdk11/src/jdk.internal.vm.compiler/share/classes/org.graalvm.compiler.api.directives.test/src:repos/openjdk11/src/jdk.internal.vm.compiler/share/classes/org.graalvm.compiler.asm.aarch64.test/src:repos/openjdk11/src/jdk.internal.vm.compiler/share/classes/org.graalvm.compiler.serviceprovider.processor/src:repos/openjdk11/src/jdk.internal.vm.compiler/share/classes/org.graalvm.compiler.serviceprovider/src:repos/openjdk11/src/jdk.internal.vm.compiler/share/classes/org.graalvm.compiler.word/src:repos/openjdk11/src/jdk.internal.vm.compiler/share/classes/org.graalvm.compiler.lir/src:repos/openjdk11/src/jdk.internal.vm.compiler/share/classes/org.graalvm.compiler.options.processor/src:repos/openjdk11/src/jdk.internal.vm.compiler/share/classes/org.graalvm.compiler.replacements.sparc/src:repos/openjdk11/src/jdk.internal.vm.compiler/share/classes/org.graalvm.compiler.processor/src:repos/openjdk11/src/jdk.internal.vm.compiler/share/classes/org.graalvm.compiler.replacements/src:repos/openjdk11/src/jdk.internal.vm.compiler/share/classes/org.graalvm.compiler.core.common/src:repos/openjdk11/src/jdk.jstatd/share/classes:repos/openjdk11/src/jdk.dynalink/share/classes:repos/openjdk11/src/java.management.rmi/share/classes:repos/openjdk11/src/java.scripting/share/classes:repos/openjdk11/src/jdk.crypto.mscapi/windows/classes:repos/openjdk11/src/java.xml.crypto/share/classes:repos/openjdk11/src/jdk.internal.jvmstat/share/classes:repos/openjdk11/src/java.management/share/classes:repos/openjdk11/src/jdk.jsobject/share/classes:repos/openjdk11/src/jdk.compiler/share/classes:repos/openjdk11/src/jdk.internal.vm.compiler.management/share/classes/org.graalvm.compiler.hotspot.management/src:repos/openjdk11/src/jdk.internal.vm.compiler.management/share/classes:repos/openjdk11/src/jdk.rmic/share/classes:repos/openjdk11/make/hotspot/src/classes:repos/openjdk11/make/jdk/src/classes:repos/openjdk11/make/langtools/test/sym:repos/openjdk11/make/langtools/test/crules/MutableFieldsAnalyzer:repos/openjdk11/make/langtools/test/crules/CodingRulesAnalyzerPlugin:repos/openjdk11/make/langtools/test/crules/DefinedByAnalyzer:repos/openjdk11/make/langtools/test:repos/openjdk11/make/langtools/intellij/src:repos/openjdk11/make/langtools/tools/anttasks:repos/openjdk11/make/langtools/tools/propertiesparser/parser:repos/openjdk11/make/langtools/tools/propertiesparser/gen:repos/openjdk11/make/langtools/tools/propertiesparser:repos/openjdk11/make/langtools/tools/genstubs:repos/openjdk11/make/langtools/tools/crules:repos/openjdk11/make/langtools/tools/compileproperties:repos/openjdk11/make/langtools/src/classes/build/tools/symbolgenerator:repos/openjdk11/make/src/classes/build/tools/jfr:repos/openjdk11/make/idea/template/src:repos/openjdk11/make/nashorn/buildtools/nashorntask/src:repos/openjdk11/make/nashorn/buildtools/nasgen/src:repos/openjdk11/test/jdk/javax/swing/LookAndFeel/8145547:repos/openjdk11/test/hotspot/jtreg/vmTestbase:repos/openjdk11/test/langtools/tools/javac/generics/odersky:repos/openjdk11/test/jdk/com/sun/net/httpserver/bugs:repos/openjdk11/test/langtools/tools/javac/diags:repos/openjdk11/test/jdk/java/rmi/testlibrary:repos/openjdk11/test/jdk/lib/testlibrary/bytecode:repos/openjdk11/test/jdk/java/net/httpclient/http2/server:repos/openjdk11/test/lib:repos/openjdk11/test/jaxp/javax/xml/jaxp/libs:repos/openjdk11/test/hotspot/jtreg/gc/survivorAlignment:repos/openjdk11/test/jdk/sun/security/krb5/auto:repos/openjdk11/test/jdk/sanity/client/lib/jemmy/src:repos/openjdk11/test/jaxp/javax/xml/jaxp/functional:repos/openjdk11/test/jdk/java/nio/file/Files:repos/openjdk11/test/jdk/javax/swing/JList/6823603:repos/openjdk11/test/langtools/tools/lib:repos/openjdk11/test/hotspot/jtreg/runtime/SelectionResolution/classes:repos/openjdk11/test/langtools/tools/javadoc:repos/openjdk11/test/jdk/sun/util/calendar/zi:repos/openjdk11/test/hotspot/jtreg/testlibrary/ctw/src:repos/openjdk11/test/jdk/sun/net/www/protocol/http:repos/openjdk11/test/jdk/javax/xml/jaxp/testng:repos/openjdk11/test/langtools/tools/javac/4241573:repos/openjdk11/test/jdk/java/util/Collections:repos/openjdk11/test/jdk/tools/pack200/pack200-verifier/src:repos/openjdk11/test/jdk/tools/launcher:repos/openjdk11/test/jdk/java/rmi/activation/Activatable/checkAnnotations:repos/openjdk11/test/hotspot/jtreg/runtime/CommandLine/OptionsValidation/common:repos/openjdk11/test/jdk/java/lang/ProcessHandle:repos/openjdk11/test/langtools/tools/javac/classfiles/attributes/innerclasses:repos/openjdk11/test/jdk/java/util/Map:repos/openjdk11/test/jdk/java/text/Format/NumberFormat:repos/openjdk11/test/langtools/tools/javac/6917288:repos/openjdk11/test/langtools/tools/javac/doctree/dcapi:repos/openjdk11/test/jdk/java/util/concurrent/ConcurrentHashMap:repos/openjdk11/test/jdk/lib/testlibrary:repos/openjdk11/test/jdk/java/util/concurrent/forkjoin:repos/openjdk11/test/jaxp/javax/xml/jaxp/unittest:repos/openjdk11/test/langtools/tools/javac/api/file:repos/openjdk11/test/jdk/java/security/testlibrary:repos/openjdk11/test/jdk:repos/openjdk11/test/langtools/tools/javap/output",
    #"swt": "repos/eclipse.platform.swt/bundles/org.eclipse.swt/Eclipse SWT/cairo:repos/eclipse.platform.swt/bundles/org.eclipse.swt/Eclipse SWT/cocoa:repos/eclipse.platform.swt/bundles/org.eclipse.swt/Eclipse SWT Accessibility/cocoa:repos/eclipse.platform.swt/bundles/org.eclipse.swt/Eclipse SWT AWT/cocoa:repos/eclipse.platform.swt/bundles/org.eclipse.swt/Eclipse SWT Browser/cocoa:repos/eclipse.platform.swt/bundles/org.eclipse.swt/Eclipse SWT Drag and Drop/cocoa:repos/eclipse.platform.swt/bundles/org.eclipse.swt/Eclipse SWT Mozilla/cocoa:repos/eclipse.platform.swt/bundles/org.eclipse.swt/Eclipse SWT OpenGL/cocoa:repos/eclipse.platform.swt/bundles/org.eclipse.swt/Eclipse SWT PI/cocoa:repos/eclipse.platform.swt/bundles/org.eclipse.swt/Eclipse SWT Printing/cocoa:repos/eclipse.platform.swt/bundles/org.eclipse.swt/Eclipse SWT Program/cocoa:repos/eclipse.platform.swt/bundles/org.eclipse.swt/Eclipse SWT WebKit/cocoa:repos/eclipse.platform.swt/bundles/org.eclipse.swt/Eclipse SWT/common:repos/eclipse.platform.swt/bundles/org.eclipse.swt/Eclipse SWT Accessibility/common:repos/eclipse.platform.swt/bundles/org.eclipse.swt/Eclipse SWT AWT/common:repos/eclipse.platform.swt/bundles/org.eclipse.swt/Eclipse SWT Browser/common:repos/eclipse.platform.swt/bundles/org.eclipse.swt/Eclipse SWT Custom Widgets/common:repos/eclipse.platform.swt/bundles/org.eclipse.swt/Eclipse SWT Drag and Drop/common:repos/eclipse.platform.swt/bundles/org.eclipse.swt/Eclipse SWT Mozilla/common:repos/eclipse.platform.swt/bundles/org.eclipse.swt/Eclipse SWT OpenGL/common:repos/eclipse.platform.swt/bundles/org.eclipse.swt/Eclipse SWT PI/common:repos/eclipse.platform.swt/bundles/org.eclipse.swt/Eclipse SWT Printing/common:repos/eclipse.platform.swt/bundles/org.eclipse.swt/Eclipse SWT Program/common:repos/eclipse.platform.swt/bundles/org.eclipse.swt/Eclipse SWT/emulated/tooltip:repos/eclipse.platform.swt/bundles/org.eclipse.swt/Eclipse SWT/emulated/coolbar:repos/eclipse.platform.swt/bundles/org.eclipse.swt/Eclipse SWT/gtk:repos/eclipse.platform.swt/bundles/org.eclipse.swt/Eclipse SWT Accessibility/gtk:repos/eclipse.platform.swt/bundles/org.eclipse.swt/Eclipse SWT AWT/gtk:repos/eclipse.platform.swt/bundles/org.eclipse.swt/Eclipse SWT Browser/gtk:repos/eclipse.platform.swt/bundles/org.eclipse.swt/Eclipse SWT Drag and Drop/gtk:repos/eclipse.platform.swt/bundles/org.eclipse.swt/Eclipse SWT Mozilla/gtk:repos/eclipse.platform.swt/bundles/org.eclipse.swt/Eclipse SWT OpenGL/gtk:repos/eclipse.platform.swt/bundles/org.eclipse.swt/Eclipse SWT PI/gtk:repos/eclipse.platform.swt/bundles/org.eclipse.swt/Eclipse SWT Printing/gtk:repos/eclipse.platform.swt/bundles/org.eclipse.swt/Eclipse SWT Program/gtk:repos/eclipse.platform.swt/bundles/org.eclipse.swt/Eclipse SWT WebKit/gtk:repos/eclipse.platform.swt/bundles/org.eclipse.swt/Eclipse SWT/win32:repos/eclipse.platform.swt/bundles/org.eclipse.swt/Eclipse SWT Accessibility/win32:repos/eclipse.platform.swt/bundles/org.eclipse.swt/Eclipse SWT AWT/win32:repos/eclipse.platform.swt/bundles/org.eclipse.swt/Eclipse SWT Browser/win32:repos/eclipse.platform.swt/bundles/org.eclipse.swt/Eclipse SWT Drag and Drop/win32:repos/eclipse.platform.swt/bundles/org.eclipse.swt/Eclipse SWT Mozilla/win32:repos/eclipse.platform.swt/bundles/org.eclipse.swt/Eclipse SWT OLE Win32/win32:repos/eclipse.platform.swt/bundles/org.eclipse.swt/Eclipse SWT OpenGL/win32:repos/eclipse.platform.swt/bundles/org.eclipse.swt/Eclipse SWT PI/win32:repos/eclipse.platform.swt/bundles/org.eclipse.swt/Eclipse SWT Printing/win32:repos/eclipse.platform.swt/bundles/org.eclipse.swt/Eclipse SWT Program/win32:repos/eclipse.platform.swt/bundles/org.eclipse.swt/Eclipse SWT WebKit/win32",
    #"swt_cocoa": "repos/eclipse.platform.swt/bundles/org.eclipse.swt/Eclipse SWT/cocoa:repos/eclipse.platform.swt/bundles/org.eclipse.swt/Eclipse SWT Accessibility/cocoa:repos/eclipse.platform.swt/bundles/org.eclipse.swt/Eclipse SWT AWT/cocoa:repos/eclipse.platform.swt/bundles/org.eclipse.swt/Eclipse SWT Browser/cocoa:repos/eclipse.platform.swt/bundles/org.eclipse.swt/Eclipse SWT Drag and Drop/cocoa:repos/eclipse.platform.swt/bundles/org.eclipse.swt/Eclipse SWT Mozilla/cocoa:repos/eclipse.platform.swt/bundles/org.eclipse.swt/Eclipse SWT OpenGL/cocoa:repos/eclipse.platform.swt/bundles/org.eclipse.swt/Eclipse SWT PI/cocoa:repos/eclipse.platform.swt/bundles/org.eclipse.swt/Eclipse SWT Printing/cocoa:repos/eclipse.platform.swt/bundles/org.eclipse.swt/Eclipse SWT Program/cocoa:repos/eclipse.platform.swt/bundles/org.eclipse.swt/Eclipse SWT WebKit/cocoa",
    #"swt_gtk": "repos/eclipse.platform.swt/bundles/org.eclipse.swt/Eclipse SWT/gtk:repos/eclipse.platform.swt/bundles/org.eclipse.swt/Eclipse SWT Accessibility/gtk:repos/eclipse.platform.swt/bundles/org.eclipse.swt/Eclipse SWT AWT/gtk:repos/eclipse.platform.swt/bundles/org.eclipse.swt/Eclipse SWT Browser/gtk:repos/eclipse.platform.swt/bundles/org.eclipse.swt/Eclipse SWT Drag and Drop/gtk:repos/eclipse.platform.swt/bundles/org.eclipse.swt/Eclipse SWT Mozilla/gtk:repos/eclipse.platform.swt/bundles/org.eclipse.swt/Eclipse SWT OpenGL/gtk:repos/eclipse.platform.swt/bundles/org.eclipse.swt/Eclipse SWT PI/gtk:repos/eclipse.platform.swt/bundles/org.eclipse.swt/Eclipse SWT Printing/gtk:repos/eclipse.platform.swt/bundles/org.eclipse.swt/Eclipse SWT Program/gtk:repos/eclipse.platform.swt/bundles/org.eclipse.swt/Eclipse SWT WebKit/gtk",
    #"swt_win32": "repos/eclipse.platform.swt/bundles/org.eclipse.swt/Eclipse SWT/win32:repos/eclipse.platform.swt/bundles/org.eclipse.swt/Eclipse SWT Accessibility/win32:repos/eclipse.platform.swt/bundles/org.eclipse.swt/Eclipse SWT AWT/win32:repos/eclipse.platform.swt/bundles/org.eclipse.swt/Eclipse SWT Browser/win32:repos/eclipse.platform.swt/bundles/org.eclipse.swt/Eclipse SWT Drag and Drop/win32:repos/eclipse.platform.swt/bundles/org.eclipse.swt/Eclipse SWT Mozilla/win32:repos/eclipse.platform.swt/bundles/org.eclipse.swt/Eclipse SWT OLE Win32/win32:repos/eclipse.platform.swt/bundles/org.eclipse.swt/Eclipse SWT OpenGL/win32:repos/eclipse.platform.swt/bundles/org.eclipse.swt/Eclipse SWT PI/win32:repos/eclipse.platform.swt/bundles/org.eclipse.swt/Eclipse SWT Printing/win32:repos/eclipse.platform.swt/bundles/org.eclipse.swt/Eclipse SWT Program/win32:repos/eclipse.platform.swt/bundles/org.eclipse.swt/Eclipse SWT WebKit/win32",
    "trove": "repos/trove/core/src/main/java:repos/trove/experimental/src/main/java:repos/trove/core/src/test/java"}


def _getJavaMethods(htmlcache, project, filename, methodspec):
    key = (filename, methodspec)
    if key in htmlcache:
        return htmlcache[key]
    script_dir = os.path.dirname(os.path.abspath(__file__))
    ret = subprocess.run(["java", "-cp", os.path.join(script_dir, "./methodextracter/build/libs/methodextracter-all.jar"), "MethodExtracter", filename, methodspec, SOURCEPATHS[project]],
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, universal_newlines=True)
    if ret.returncode != 0:
        print("launched \'" + str(ret.args) + "\'")
        raise Exception("Failed to analyze " + filename + "; " + methodspec)
    htmlcache[key] = ret.stdout
    return ret.stdout


def _fromJavaFile(htmlcache, html, project, filename, methodspec):
    html.pre(_class="prettyprint").code(_class="language-java")
    html.text(_getJavaMethods(htmlcache, project, filename, methodspec))
    html._code()._pre()


def _mkHtmlFile(number, htmlcache, project1, filename1, methodspec1, project2, filename2, methodspec2, sim):
    html = HTMLGenerator()
    html.html()
    html.head()

    html.title().text(str(number) + ") Are these two methods semantically similar?")._title()
    html.script(_type="text/javascript", src="https://cdn.rawgit.com/google/code-prettify/master/loader/run_prettify.js")._script()
    html.script().text("""
        window.onload = function() {
            var output = document.getElementById("output");
            var radioButtonsA0 = document.getElementById("form0").r0;
            var radioButtonsA1 = document.getElementById("form1").r1;
            var radioButtonsA2 = document.getElementById("form2").r2;
            var radioButtonsC0 = document.getElementById("form0").r0c;
            var radioButtonsC1 = document.getElementById("form1").r1c;
            var radioButtonsC2 = document.getElementById("form2").r2c;
            var radioButtons = [radioButtonsA0, radioButtonsA1, radioButtonsA2,
                    radioButtonsC0, radioButtonsC1, radioButtonsC2];

            function recomputeOutput() {
                outStr = "";
                for (var j = 0; j < radioButtons.length; ++j) {
                    if (j > 0) {
                        outStr += ",";
                    }
                    for (var i = 0; i < radioButtons[j].length; ++i) {
                        if (radioButtons[j][i].checked) {
                            outStr += radioButtons[j][i].value;
                        }
                    }
                }
                output.value = outStr
            }

            for (var j = 0; j < radioButtons.length; ++j) {
                for (var i = 0; i < radioButtons[j].length; ++i) {
                    radioButtons[j][i].addEventListener("change", recomputeOutput);
                }
            }

            recomputeOutput();
        }
    """)._script()
    html.style().text("""
        label {
            margin-right: 1em;
        }
        li {
            margin-bottom: 2.5ex;
        }
        .option-table {
            display: grid;
            grid-template-columns: auto auto auto auto;
            width: 50em;
        }
    """)._style()

    html._head().body()

    html.comment("File1: " + filename1)
    html.comment("File2: " + filename2)
    html.comment("Similarity: " + str(sim))

    html.div(style="width: 99%; display: block; border: 1px solid #c20244; padding: 5px; border-radius: 10px; background-color: #fbf2f5; box-shadow: 3px 3px 5px 3px #AAAAAA;")
    html.p(style="font-weight: bold").text("How similar is the first method in the left column to the first method in the right column (including the called methods)? (ID: " + str(number) + ")")._p()

    # html.ol()
    # html.li(value="5").text("The methods provide equivalent functionality.")._li()
    # html.li(value="4").text("The methods implement the same algorithm but their behaviors differ for some (corner) cases.")._li()
    # html.li(value="3").text("The methods serve the same purpose but are implemented for different data structures, different backends etc.")._li()
    # html.li(value="2").text("One method provides a superset of the functionality of the other one.")._li()
    # html.li(value="1").text("The methods serve different purposes but are conceptually or topically related (e.g., implement graph algorithms or are network related).")._li()
    # html.li(value="0").text("The methods provide unrelated functionality.")._li()
    # html.li(value="-1").text("Unknown or unsure.")._li()
    # html._ol()

    html.ul()
    html.li().p(style="margin-bottom: 1ex").text("The goals the developers want to achieve with the respective methods are similar.")._p()
    html.form(id="form0")
    html.div(_class="option-table")
    html.div().text("Do you agree?")._div()
    html.div()
    html.input(_type="radio", name="r0", id="r02", value="2")._input()
    html.label(_for="r02").text("agree")._label()
    html._div()
    html.div()
    html.input(_type="radio", name="r0", id="r01", value="1")._input()
    html.label(_for="r01").text("conditionally agree")._label()
    html._div()
    html.div()
    html.input(_type="radio", name="r0", id="r00", value="0")._input()
    html.label(_for="r00").text("disagree")._label()
    html._div()
    html.div().text("How high is your confidence?")._div()
    html.div()
    html.input(_type="radio", name="r0c", id="r0c2", value="2")._input()
    html.label(_for="r0c2").text("high")._label()
    html._div()
    html.div()
    html.input(_type="radio", name="r0c", id="r0c1", value="1")._input()
    html.label(_for="r0c1").text("medium")._label()
    html._div()
    html.div()
    html.input(_type="radio", name="r0c", id="r0c0", value="0")._input()
    html.label(_for="r0c0").text("low")._label()
    html._div()
    html._div()._form()._li()

    html.li().p(style="margin-bottom: 1ex").text("The methods perform comparable operations on their respective data.")._p()
    html.form(id="form1")
    html.div(_class="option-table")
    html.div().text("Do you agree?")._div()
    html.div()
    html.input(_type="radio", name="r1", id="r12", value="2")._input()
    html.label(_for="r12").text("agree")._label()
    html._div()
    html.div()
    html.input(_type="radio", name="r1", id="r11", value="1")._input()
    html.label(_for="r11").text("conditionally agree")._label()
    html._div()
    html.div()
    html.input(_type="radio", name="r1", id="r10", value="0")._input()
    html.label(_for="r10").text("disagree")._label()
    html._div()
    html.div().text("How high is your confidence?")._div()
    html.div()
    html.input(_type="radio", name="r1c", id="r1c2", value="2")._input()
    html.label(_for="r1c2").text("high")._label()
    html._div()
    html.div()
    html.input(_type="radio", name="r1c", id="r1c1", value="1")._input()
    html.label(_for="r1c1").text("medium")._label()
    html._div()
    html.div()
    html.input(_type="radio", name="r1c", id="r1c0", value="0")._input()
    html.label(_for="r1c0").text("low")._label()
    html._div()
    html._div()._form()._li()

    html.li().p(style="margin-bottom: 1ex").text("The effects of both methods after their execution are similar on a technical level.")._p()
    html.form(id="form2")
    html.div(_class="option-table")
    html.div().text("Do you agree?")._div()
    html.div()
    html.input(_type="radio", name="r2", id="r22", value="2")._input()
    html.label(_for="r22").text("agree")._label()
    html._div()
    html.div()
    html.input(_type="radio", name="r2", id="r21", value="1")._input()
    html.label(_for="r21").text("conditionally agree")._label()
    html._div()
    html.div()
    html.input(_type="radio", name="r2", id="r20", value="0")._input()
    html.label(_for="r20").text("disagree")._label()
    html._div()
    html.div().text("How high is your confidence?")._div()
    html.div()
    html.input(_type="radio", name="r2c", id="r2c2", value="2")._input()
    html.label(_for="r2c2").text("high")._label()
    html._div()
    html.div()
    html.input(_type="radio", name="r2c", id="r2c1", value="1")._input()
    html.label(_for="r2c1").text("medium")._label()
    html._div()
    html.div()
    html.input(_type="radio", name="r2c", id="r2c0", value="0")._input()
    html.label(_for="r2c0").text("low")._label()
    html._div()
    html._div()._form()._li()
    html._ul()

    html.form()
    html.label(_for="output").text("Output: ")._label().input(_type="text", id="output")._input()
    html._form()

    html._div()

    html.div(style="width: 50%; float: left; overflow: auto")
    html.div(style="width: 99%")
    _fromJavaFile(htmlcache, html, project1, filename1, methodspec1)
    html._div()
    html._div()

    html.div(style="width: 50%; float: left; overflow: auto")
    html.div(style="width: 99%")
    _fromJavaFile(htmlcache, html, project2, filename2, methodspec2)
    html._div()
    html._div()

    html._body()
    html._html()
    return html.build()


#############################################################################
# PROGRAM                                                                   #
#############################################################################

def main():
    # Arguments: input.csv output_dir nparticipants-per-pair [npairs-per-participant...]
    # Parse input.csv
    with open(sys.argv[1], "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        input_list = [ row for row in reader ]
    output_dir = Path(sys.argv[2])
    # Read participants
    nparticipants_per_pair = int(sys.argv[3])
    participants = [ int(a) for a in sys.argv[4:] ]
    # Validate input
    if len(input_list) * nparticipants_per_pair != sum(participants):
        print("[E] length of %s (%d) times number of participants per pair (%d) has to equal sum of number of pairs per participant (%d)" %
            (sys.argv[1], len(input_list), nparticipants_per_pair, sum(participants)))
        sys.exit(1)
    # Distribute pairs
    htmlcache = dict()
    pidx = 0
    for i in range(0, nparticipants_per_pair):
        random.shuffle(input_list)
        pstart = pidx
        pairsaccum = participants[pidx]
        while pairsaccum < len(input_list) and pidx < len(participants):
            pidx += 1
            pairsaccum += participants[pidx]
        if pairsaccum != len(input_list):
            print("[E] cannot distribute pairs: sublist from %d to %d has only %d < %d pairs" %
                (pstart, pidx, pairsaccum, len(input_list)))
            sys.exit(2)
        pidx += 1
        inpidx = 0
        for p in range(pstart, pidx):
            part_dir = output_dir / ("p" + str(p))
            part_dir.mkdir()
            for j in range(0, participants[p]):
                pair = input_list[inpidx]
                with (part_dir / ("pair_" + str(j) + ".html")).open("w") as f:
                    if random.choice([True, False]):
                        print(_mkHtmlFile(j, htmlcache, pair["project1"], pair["file1"], pair["method1"],
                            pair["project2"], pair["file2"], pair["method2"], pair["sim"]), file=f)
                    else:
                        print(_mkHtmlFile(j, htmlcache, pair["project2"], pair["file2"], pair["method2"],
                            pair["project1"], pair["file1"], pair["method1"], pair["sim"]), file=f)
                print("%d,%d,%d" % (p, j, int(pair["pairid"])))
                inpidx += 1

if __name__ == "__main__":
    main()
