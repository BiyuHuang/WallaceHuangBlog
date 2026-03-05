---
title: "Spark Performance Tuning: A Practical Guide"
date: 2019-08-28 14:17:45 +0800
description: Hands-on Spark performance optimization covering configuration, code patterns, memory management, shuffle, data skew, and PySpark deployment.
image: /assets/img/spark_logo.png
tags: [BigData, Spark]
categories: [Tech]
---

*Written by Biyu Huang, with [Cursor](https://www.cursor.com/) as co-author.*

---

Spark performance tuning isn't magic — it's about understanding how the engine works and removing the bottlenecks that slow it down. This guide covers the techniques I've used in production over years of running Spark at scale.

---

## 1. Configuration Tuning

### Resource Allocation

The most impactful configs are the ones that control how much compute you get:

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
  --conf spark.sql.files.minPartitionNum=1 \
  --conf spark.executor.instances=5 \
  --conf spark.executor.memory=4g \
  --conf spark.executor.memoryOverhead=1g \
  --conf spark.sql.files.mergeSmallFile.enabled=true \
  --conf spark.sql.files.mergeSmallFile.maxBytes=268435456 \
  --packages com.google.protobuf:protobuf-java:3.6.0 \
  --conf spark.driver.extraClassPath=com.google.protobuf_protobuf-java-3.6.0.jar \
  --conf spark.executor.extraClassPath=com.google.protobuf_protobuf-java-3.6.0.jar \
  ${MAIN_CLASS} ${SPARK_APP_JAR}
```

**Full Configuration Reference:**

| Config | Value | Purpose |
|--------|-------|---------|
| `spark.master` | `yarn` | Run on YARN cluster |
| `spark.submit.deployMode` | `cluster` | Driver runs on cluster node, not client |
| `spark.yarn.maxAppAttempts` | `1` | Don't retry failed apps (fail fast for debugging) |
| `spark.yarn.queue` | `${YARN_QUEUE}` | Target YARN queue |
| `spark.yarn.tags` | `${USER_TAGS}` | Tags for job tracking and filtering |
| `spark.executor.instances` | `5` | Starting executor count |
| `spark.executor.cores` | `1` | Cores per executor (1 for I/O heavy, 4-5 for CPU heavy) |
| `spark.executor.memory` | `4g` | Heap memory per executor (2g-8g per core) |
| `spark.executor.memoryOverhead` | `1g` | Off-heap memory for Netty, buffers. OOM kills often mean this is too low |
| `spark.driver.memory` | `1g` | Driver heap. Increase if `collect()`-ing large datasets |
| `spark.task.cpus` | `1` | CPU cores per task |
| `spark.dynamicAllocation.enabled` | `true` | Auto-scale executors based on workload |
| `spark.dynamicAllocation.minExecutors` | `1` | Minimum executors to keep |
| `spark.dynamicAllocation.maxExecutors` | `20` | Upper bound for scaling |
| `spark.dynamicAllocation.initialExecutors` | `1` | Start small, scale up as needed |
| `spark.files.maxPartitionBytes` | `128m` | Max partition size for file reads |
| `spark.sql.files.maxPartitionBytes` | `128m` | Max partition size for SQL file reads |
| `spark.sql.files.minPartitionNum` | `1` | Minimum partitions for file reads |
| `spark.sql.files.mergeSmallFile.enabled` | `true` | Merge small files into larger partitions |
| `spark.sql.files.mergeSmallFile.maxBytes` | `268435456` | Max bytes (256MB) for merged partitions |
| `spark.driver.extraClassPath` | `protobuf-java-3.6.0.jar` | Override driver classpath for dependency conflicts |
| `spark.executor.extraClassPath` | `protobuf-java-3.6.0.jar` | Override executor classpath for dependency conflicts |

### Dynamic Allocation

Dynamic allocation lets YARN scale your executors based on actual workload. Your job starts small and scales up only when it needs more parallelism, then releases resources when idle. Essential for shared clusters.

**Gotcha:** Dynamic allocation requires `spark.shuffle.service.enabled=true` on the cluster. Without the external shuffle service, executors can't be removed because they might hold shuffle data.

### Partition Sizing

The rule of thumb: **each partition should be 100-200MB**. Too small → task scheduling overhead dominates. Too large → GC pressure and potential OOM. The `mergeSmallFile` config helps when reading many small files from HDFS/S3.

### Classpath Override

The `--packages` and `extraClassPath` configs solve dependency conflicts (e.g., Protobuf version mismatch between your app and the cluster). This ensures your JAR version takes precedence over the cluster default.

---

## 2. Code-Level Optimization

### Avoid `collect()` on Large Datasets

```scala
// BAD: pulls entire dataset to driver
val allRows = df.collect()

// GOOD: use take() or limit()
val sample = df.take(100)
// GOOD: write to storage instead
df.write.parquet("/output/path")
```

`collect()` serializes every row to the driver. If your dataset is larger than driver memory, you get an OOM. If it fits but is large, you waste time on serialization.

### Use `mapPartitions` Over `map`

When you need an expensive resource (DB connection, HTTP client) per record:

```scala
// BAD: creates a connection per row
rdd.map { row =>
  val conn = createConnection()
  val result = conn.query(row.key)
  conn.close()
  result
}

// GOOD: creates one connection per partition
rdd.mapPartitions { iter =>
  val conn = createConnection()
  val results = iter.map(row => conn.query(row.key))
  conn.close()
  results
}
```

### Broadcast Small Datasets

When joining a large table with a small lookup table:

```scala
import org.apache.spark.sql.functions.broadcast

// Forces broadcast join — small table sent to all executors
val result = largeDF.join(broadcast(smallDF), "key")
```

Broadcast join eliminates shuffle entirely for the small table. Use it when the small side fits in executor memory (default threshold: 10MB, configurable via `spark.sql.autoBroadcastJoinThreshold`).

### Cache Strategically

```scala
val frequently_used = df
  .filter($"status" === "active")
  .cache()

// Use it multiple times
frequently_used.groupBy("region").count().show()
frequently_used.groupBy("category").agg(sum("amount")).show()

// Release when done
frequently_used.unpersist()
```

**When to cache:** A DataFrame is reused 2+ times AND is expensive to recompute.
**When NOT to cache:** One-time use, or the DataFrame is too large to fit in memory.

Storage levels:

| Level | When |
|-------|------|
| `MEMORY_ONLY` | Default. Data fits in memory. |
| `MEMORY_AND_DISK` | Data might spill. Better than recomputation. |
| `MEMORY_ONLY_SER` | Memory-tight. Serialized format uses less space but more CPU. |

### Avoid UDFs When Built-in Functions Exist

```scala
// BAD: UDF breaks Catalyst optimizer
val myUpper = udf((s: String) => s.toUpperCase)
df.withColumn("name_upper", myUpper($"name"))

// GOOD: uses built-in, fully optimized
df.withColumn("name_upper", upper($"name"))
```

UDFs are black boxes to Spark's optimizer. They prevent predicate pushdown, column pruning, and code generation. Always check if a built-in function exists first.

---

## 3. Memory Management

### Understanding Spark's Memory Model

```
Executor Memory (spark.executor.memory)
├── Reserved Memory (300MB, fixed)
├── User Memory (1 - spark.memory.fraction) × usable
│   └── Your data structures, accumulators
└── Unified Memory (spark.memory.fraction × usable, default 0.6)
    ├── Storage (cache/persist)
    └── Execution (shuffle, sort, join buffers)
```

Storage and Execution share the unified region and can borrow from each other. When both need space, execution evicts cached data (execution always wins).

### Common OOM Patterns and Fixes

**Driver OOM:**
- Cause: `collect()`, large broadcast variables, too many small tasks creating metadata
- Fix: Increase `spark.driver.memory` or avoid pulling data to driver

**Executor OOM (on-heap):**
- Cause: Large partitions, data skew, excessive caching
- Fix: Repartition, increase `spark.executor.memory`, or reduce `spark.memory.fraction`

**Executor OOM (off-heap / killed by YARN):**
- Cause: Netty buffers, native memory from compression/serialization
- Fix: Increase `spark.executor.memoryOverhead`

---

## 4. Shuffle Optimization

Shuffle is the most expensive operation in Spark. It involves disk I/O, network transfer, and serialization.

### Reduce Shuffle Data Volume

```scala
// BAD: shuffles entire row
df.groupBy("key").agg(collect_list("*"))

// GOOD: select only needed columns before groupBy
df.select("key", "value")
  .groupBy("key")
  .agg(sum("value"))
```

### Tune Shuffle Partitions

```properties
spark.sql.shuffle.partitions=200  # default, often too high or too low
```

Rule of thumb: target **100-200MB per shuffle partition**. If your shuffled data is 20GB, you want ~100-200 partitions, not the default 200 which might be fine or might not.

For Spark 3.0+, use **Adaptive Query Execution (AQE)**:

```properties
spark.sql.adaptive.enabled=true
spark.sql.adaptive.coalescePartitions.enabled=true
spark.sql.adaptive.skewJoin.enabled=true
```

AQE automatically adjusts partition count and handles skew at runtime based on actual data statistics. This is the single most impactful Spark 3.x feature for performance.

### Prefer `reduceByKey` Over `groupByKey`

```scala
// BAD: shuffles all values, then reduces
rdd.groupByKey().mapValues(_.sum)

// GOOD: reduces locally first, then shuffles partial results
rdd.reduceByKey(_ + _)
```

`reduceByKey` performs a map-side combine, dramatically reducing shuffle data.

---

## 5. Handling Data Skew

Data skew is when a few keys have disproportionately more data than others, causing some tasks to run much longer than the rest.

### Detect Skew

Check the Spark UI → Stages → look for tasks where the max duration is 10x+ the median, or where one task processes significantly more data than others.

### Salting Technique

```scala
import org.apache.spark.sql.functions._

val saltBuckets = 10

// Add random salt to skewed key
val saltedLeft = skewedDF
  .withColumn("salt", (rand() * saltBuckets).cast("int"))
  .withColumn("salted_key", concat($"key", lit("_"), $"salt"))

// Explode the small side to match all salts
val explodedRight = smallDF
  .withColumn("salt", explode(array((0 until saltBuckets).map(lit(_)): _*)))
  .withColumn("salted_key", concat($"key", lit("_"), $"salt"))

// Join on salted key — distributes skewed data across buckets
val result = saltedLeft.join(explodedRight, "salted_key")
  .drop("salt", "salted_key")
```

### Isolate Hot Keys

```scala
// Split the skewed key out, broadcast-join it separately
val hotKeyDF = largeDF.filter($"key" === "hot_value")
val normalDF = largeDF.filter($"key" =!= "hot_value")

val hotResult = hotKeyDF.join(broadcast(lookupDF), "key")
val normalResult = normalDF.join(lookupDF, "key")

val result = hotResult.union(normalResult)
```

---

## 6. Serialization

### Use Kryo Over Java Serialization

```properties
spark.serializer=org.apache.spark.serializer.KryoSerializer
spark.kryo.registrationRequired=false
```

Kryo is 10x faster and more compact than Java serialization. Register your classes for best performance:

```scala
val conf = new SparkConf()
  .set("spark.serializer", "org.apache.spark.serializer.KryoSerializer")
  .registerKryoClasses(Array(
    classOf[MyClass],
    classOf[AnotherClass]
  ))
```

---

## 7. PySpark: Virtual Environments

When you need specific Python libraries on the cluster:

```bash
# Create and package virtual environment
python3 -m venv /path/to/pyspark_venv
source /path/to/pyspark_venv/bin/activate
pip3 install pyarrow pandas venv-pack
venv-pack -o pyspark_venv.tar.gz
```

### Submit with Virtual Environment

```bash
# Cluster mode
spark-submit --queue ${YOUR_QUEUE} \
  --deploy-mode cluster \
  --archives "/path/to/pyspark_venv.tar.gz#environment" \
  --conf spark.pyspark.python=./environment/bin/python3 \
  user_job.py

# Client mode (spark-submit)
spark-submit --queue ${YOUR_QUEUE} \
  --deploy-mode client \
  --archives "/path/to/pyspark_venv.tar.gz#environment" \
  --conf spark.pyspark.python=./environment/bin/python3 \
  --conf spark.pyspark.driver.python=/path/to/pyspark_venv/bin/python3 \
  user_job.py

# Client mode (pyspark shell)
pyspark --queue ${YOUR_QUEUE} \
  --conf spark.pyspark.driver.python=/path/to/pyspark_venv/bin/python3 \
  --conf spark.pyspark.python=./environment/bin/python3 \
  --archives "/path/to/pyspark_venv.tar.gz#environment"
```

---

## 8. Useful Commands

### Partition Metadata Sync (Trino/Presto)

When Spark writes new partitions that Trino/Presto doesn't see yet:

```sql
CALL system.sync_partition_metadata(
  schema_name => 'data_base',
  table_name  => 'table_name',
  mode        => 'DROP',
  case_sensitive => false
)
```

---

## Quick Reference Checklist

Before submitting a Spark job, verify:

- [ ] **Partitions**: Target 100-200MB each. Check `spark.sql.shuffle.partitions`.
- [ ] **Memory**: `executor.memory` + `memoryOverhead` fits in YARN container.
- [ ] **Broadcast**: Small tables (< 10MB) use broadcast join.
- [ ] **Skew**: Check if any key dominates. Use salting or hot key isolation.
- [ ] **Caching**: Only cache DataFrames used 2+ times. Unpersist when done.
- [ ] **AQE**: Enable for Spark 3.0+. Free performance improvement.
- [ ] **Serializer**: Use Kryo for RDD-based workloads.
- [ ] **UDFs**: Replace with built-in functions wherever possible.

---

*These tips come from years of running Spark on production YARN clusters processing terabytes daily. The specifics may vary by Spark version and cluster configuration, but the principles hold.*
