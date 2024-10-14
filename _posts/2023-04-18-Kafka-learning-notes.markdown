---
layout: post 
title: "Kafka learning notes"
date: 2023-04-18 10:30:05 +0800 
description: Kafka learning notes 
img: kafka_logo.png 
tags: BigData
---

# Kafka commands

- __console__ related
   ```
   # SASL config(producer.properties/consumer.properties)
   sasl.mechanism=SCRAM-SHA-512
   security.protocol=SASL_PLAINTEXT
   sasl.jaas.config=org.apache.kafka.common.security.scram.ScramLoginModule required \
   username="XXXXX" \
   password="XXXXX";
   ```
   - ___kafka-console-producer.sh with SASL___
   ```bash
   kafka-console-producer.sh --broker-list BROKERS --topic TOPIC --producer.config producer.properties
   ```
   - ___kafka-console-consumer.sh with SASL___
   ```bash
   kafka-console-consumer.sh --bootstrap-server BROKERS --topic TOPIC --group GROUP_ID --consumer.config consumer.properties
   ```