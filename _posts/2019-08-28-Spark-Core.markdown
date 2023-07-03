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
      --conf spark.dynamicAllocation.enabled=true \
      --conf spark.dynamicAllocation.maxExecutors=20 \
      --conf spark.dynamicAllocation.minExecutors=1 \
      --conf spark.dynamicAllocation.initialExecutors=1 \ 
      --conf spark.task.cpus=1 \ 
      --conf spark.executor.cores=1 \ 
      --conf spark.driver.memory=1g \ 
      --conf spark.yarn.tags=${USER_TAGS} \ 
      --conf spark.files.maxPartitionBytes=128m \
      --conf spark.sql.files.maxPartitionBytes=128m \
      --conf spark.sql.files.minPartitionNum= 1 \
      --conf spark.executor.instances=5 \ 
      --conf spark.executor.memory=4g \ 
      --conf spark.executor.memoryOverhead=1g \
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

- 命令提示

  - sync_partition_metadata 
    ```bash 
    CALL system.sync_partition_metadata(schema_name => 'data_base', table_name => 'table_name', mode => 'DROP', case_sensitive => false)
    ```
  - __pyspark__ related
      - ___virtual env___
        ```bash
        // Create virtual env under path /path/to/your/pyspark_venv
        python3 -m venv /path/to/your/pyspark_venv
        // Activate the virtual env
        source /path/to/your/pyspark_venv/bin/activate
        // Install library that user needed
        pip3 install pyarrow pandas venv-pack
        // package the venv
        venv-pack -o pyspark_venv.tar.gz
        ```
      - ___pyspark submit___
        ```bash
        # cluster mode(spark-submit)
        spark-submit --queue {YOUR_QUEUE} \
        --deploy-mode cluster \
        --archives "/path/to/your/pyspark_venv.tar.gz#environment" \
        --conf spark.pyspark.python=./environment/bin/python3 \
        user_job.py
        
        # client mode(spark-submit)
        spark-submit --queue {YOUR_QUEUE} \
        --deploy-mode client \
        --archives "/path/to/your/pyspark_venv.tar.gz#environment" \
        --conf spark.pyspark.python=./environment/bin/python3 \
        --conf spark.pyspark.driver.python=/path/to/your/pyspark_venv/bin/python3 \
        user_job.py
        
        # client mode(pyspark)
        pyspark --queue {YOUR_QUEUE} \
        --conf spark.pyspark.driver.python=/path/to/your/pyspark_venv/bin/python3 \
        --conf spark.pyspark.python=./environment/bin/python3 \
        --archives "/path/to/your/pyspark_venv.tar.gz#environment" \
        user_job.py   
        ```