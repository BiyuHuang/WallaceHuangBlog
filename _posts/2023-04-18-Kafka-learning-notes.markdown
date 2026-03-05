---
title: "Kafka: A Practical Reference Guide"
date: 2023-04-18 10:30:05 +0800
description: Practical Kafka reference covering CLI commands, SASL authentication, producer/consumer patterns, topic management, and operational troubleshooting.
image: /assets/img/kafka_logo.png
tags: [BigData, Kafka]
categories: [Tech]
---

*Written by Biyu Huang, with [Cursor](https://www.cursor.com/) as co-author.*

---

A working reference for Kafka operations — the commands and patterns I use regularly in production.

---

## 1. SASL Authentication

Most production Kafka clusters use SASL for authentication. Create a properties file for both producer and consumer:

```properties
# producer.properties / consumer.properties
sasl.mechanism=SCRAM-SHA-512
security.protocol=SASL_PLAINTEXT
sasl.jaas.config=org.apache.kafka.common.security.scram.ScramLoginModule required \
  username="XXXXX" \
  password="XXXXX";
```

### Console Producer with SASL

```bash
kafka-console-producer.sh \
  --broker-list BROKERS \
  --topic TOPIC \
  --producer.config producer.properties
```

### Console Consumer with SASL

```bash
kafka-console-consumer.sh \
  --bootstrap-server BROKERS \
  --topic TOPIC \
  --group GROUP_ID \
  --consumer.config consumer.properties
```

---

## 2. Topic Management

### List Topics

```bash
kafka-topics.sh --bootstrap-server BROKERS --list

# With SASL
kafka-topics.sh --bootstrap-server BROKERS \
  --command-config consumer.properties --list
```

### Create a Topic

```bash
kafka-topics.sh --bootstrap-server BROKERS \
  --create \
  --topic my-topic \
  --partitions 6 \
  --replication-factor 3
```

**Partition count guidelines:**
- Target **1MB/s per partition** throughput
- More partitions = more parallelism but more overhead
- Partitions can be increased later, but **never decreased**

### Describe a Topic

```bash
kafka-topics.sh --bootstrap-server BROKERS \
  --describe --topic my-topic
```

Shows partition count, replication factor, leader assignment, and ISR (in-sync replicas) for each partition.

### Delete a Topic

```bash
kafka-topics.sh --bootstrap-server BROKERS \
  --delete --topic my-topic
```

Requires `delete.topic.enable=true` on the broker.

### Alter Partitions

```bash
kafka-topics.sh --bootstrap-server BROKERS \
  --alter --topic my-topic --partitions 12
```

---

## 3. Consumer Group Operations

### List Consumer Groups

```bash
kafka-consumer-groups.sh --bootstrap-server BROKERS --list
```

### Describe a Consumer Group

```bash
kafka-consumer-groups.sh --bootstrap-server BROKERS \
  --describe --group my-group
```

Shows per-partition: current offset, log-end offset, and **lag**. Lag is the key metric — it tells you how far behind the consumer is.

### Reset Consumer Offsets

```bash
# Reset to earliest (reprocess all data)
kafka-consumer-groups.sh --bootstrap-server BROKERS \
  --group my-group --topic my-topic \
  --reset-offsets --to-earliest --execute

# Reset to latest (skip to current end)
kafka-consumer-groups.sh --bootstrap-server BROKERS \
  --group my-group --topic my-topic \
  --reset-offsets --to-latest --execute

# Reset to specific timestamp
kafka-consumer-groups.sh --bootstrap-server BROKERS \
  --group my-group --topic my-topic \
  --reset-offsets --to-datetime 2023-04-18T00:00:00.000 --execute

# Shift by offset (e.g., skip 100 messages per partition)
kafka-consumer-groups.sh --bootstrap-server BROKERS \
  --group my-group --topic my-topic \
  --reset-offsets --shift-by 100 --execute
```

**Important:** The consumer group must be **inactive** (no running consumers) to reset offsets.

---

## 4. Producing and Consuming

### Produce from File

```bash
kafka-console-producer.sh --bootstrap-server BROKERS \
  --topic my-topic < messages.txt
```

### Consume with Key and Value

```bash
kafka-console-consumer.sh --bootstrap-server BROKERS \
  --topic my-topic \
  --from-beginning \
  --property print.key=true \
  --property key.separator="|"
```

### Consume with Timestamp

```bash
kafka-console-consumer.sh --bootstrap-server BROKERS \
  --topic my-topic \
  --from-beginning \
  --property print.timestamp=true
```

### Consume N Messages

```bash
kafka-console-consumer.sh --bootstrap-server BROKERS \
  --topic my-topic --max-messages 10
```

---

## 5. Performance Testing

### Producer Throughput Test

```bash
kafka-producer-perf-test.sh \
  --topic perf-test \
  --num-records 1000000 \
  --record-size 1024 \
  --throughput -1 \
  --producer-props bootstrap.servers=BROKERS
```

### Consumer Throughput Test

```bash
kafka-consumer-perf-test.sh \
  --bootstrap-server BROKERS \
  --topic perf-test \
  --messages 1000000
```

---

## 6. Key Concepts Quick Reference

### Partitions and Ordering

- Messages within a **single partition** are strictly ordered
- Messages across partitions have **no ordering guarantee**
- Use a message key to ensure related messages go to the same partition

### Consumer Groups

- Each partition is consumed by **exactly one consumer** within a group
- If consumers > partitions, some consumers sit idle
- If consumers < partitions, some consumers handle multiple partitions

### Replication

- **Replication factor**: Number of copies of each partition across brokers
- **ISR (In-Sync Replicas)**: The set of replicas that are caught up with the leader
- **`acks=all`**: Producer waits for all ISR to acknowledge — strongest durability

### Retention

```properties
# Time-based (default 7 days)
log.retention.hours=168

# Size-based (per partition)
log.retention.bytes=1073741824

# Compaction (keep latest value per key)
log.cleanup.policy=compact
```

---

## 7. Troubleshooting

### High Consumer Lag

1. Check if the consumer is running: `kafka-consumer-groups.sh --describe --group ...`
2. Check throughput: is the consumer processing slower than the producer?
3. Solutions: increase partitions + consumers, optimize consumer processing, or batch more aggressively

### Under-Replicated Partitions

```bash
kafka-topics.sh --bootstrap-server BROKERS \
  --describe --under-replicated-partitions
```

Causes: broker down, disk full, network issues. Check broker logs.

### Leader Election Issues

If a partition has no leader, check:

```bash
kafka-topics.sh --bootstrap-server BROKERS \
  --describe --unavailable-partitions
```

Usually caused by all replicas being offline. Restart affected brokers.

### Connection Timeout

```
org.apache.kafka.common.errors.TimeoutException
```

Common causes:
- Wrong bootstrap server address
- Firewall blocking port 9092 (or custom port)
- SASL config incorrect or missing
- `advertised.listeners` on broker doesn't match what the client can reach

---

## Quick Reference Card

| Task | Command |
|------|---------|
| List topics | `kafka-topics.sh --list` |
| Describe topic | `kafka-topics.sh --describe --topic X` |
| Consumer lag | `kafka-consumer-groups.sh --describe --group X` |
| Reset offsets | `kafka-consumer-groups.sh --reset-offsets --to-earliest --execute` |
| Quick consume | `kafka-console-consumer.sh --topic X --max-messages 10` |
| Perf test | `kafka-producer-perf-test.sh --num-records 1M --record-size 1024` |
