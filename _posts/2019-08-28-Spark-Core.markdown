---
layout: post
title: "Spark性能优化总结"
date: 2019-08-28 14:17:45 +0800
description: Spark # Add post description (optional)
img:  spark_logo.png # Add image post (optional)
tags: BigData
---

# Spark性能优化总结
- 配置调优
 1. `spark-submit` **overwrite** jar in the classpath of Spark cluster.
    ```bash
    spark-submit \
      --conf spark.master=yarn \ 
      --conf spark.submit.deployMode=cluster \ 
      --conf spark.yarn.maxAppAttempts=1 \ 
      --conf spark.yarn.queue=${YARN_QUEUE} \ 
      --conf spark.task.cpus=1 \ 
      --conf spark.executor.cores=1 \ 
      --conf spark.driver.memory=1g \ 
      --conf spark.yarn.tags=${USER_TAGS} \ 
      --conf spark.executor.instances=5 \ 
      --conf spark.executor.memory=4g \ 
      --conf spark.executor.memoryOverhead=1g
      --conf spark.sql.files.mergeSmallFile.enabled=true \
      --conf spark.sql.files.mergeSmallFile.maxBytes=268435456 \
      --packages com.google.protobuf:protobuf-java:3.6.0 \ 
      --conf spark.driver.extraClassPath=com.google.protobuf_protobuf-java-3.6.0.jar \ 
      --conf spark.executor.extraClassPath=com.google.protobuf_protobuf-java-3.6.0.jar \
      --conf ${MAIN_CLASS} \
      {SPARK_APP_JAR}
    ```
- 代码调优
- jvm调优
