---
layout: post 
title: "How to use maven"
date: 2022-05-26 14:30:05 +0800 
description: How to use maven 
img: maven-logo-black-on-white.png
tags: BigData
---

# How to use maven

1. Mixed Java/Scala Projects. The `pom.xml` maybe like this:
   ```xml
   <?xml version="1.0" encoding="UTF-8"?>
   <project xmlns="http://maven.apache.org/POM/4.0.0" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
            xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 http://maven.apache.org/maven-v4_0_0.xsd">
       <modelVersion>4.0.0</modelVersion>
   
       <groupId>sandbox</groupId>
       <artifactId>testJavaAndScala</artifactId>
       <version>1.0-SNAPSHOT</version>
       <name>Test for Java + Scala compilation</name>
       <description>Test for Java + Scala compilation</description>
   
       <dependencies>
           <dependency>
               <groupId>org.scala-lang</groupId>
               <artifactId>scala-library</artifactId>
               <version>2.7.2</version>
           </dependency>
       </dependencies>
       <build>
           <pluginManagement>
               <plugins>
                   <plugin>
                       <groupId>net.alchim31.maven</groupId>
                       <artifactId>scala-maven-plugin</artifactId>
                       <version>4.6.1</version>
                   </plugin>
                   <plugin>
                       <groupId>org.apache.maven.plugins</groupId>
                       <artifactId>maven-compiler-plugin</artifactId>
                       <version>3.8.1</version>
                       <configuration>
                           <source>1.8</source>
                           <target>1.8</target>
                       </configuration>
                   </plugin>
               </plugins>
           </pluginManagement>
           <plugins>
               <plugin>
                   <groupId>net.alchim31.maven</groupId>
                   <artifactId>scala-maven-plugin</artifactId>
                   <executions>
                       <execution>
                           <id>scala-compile-first</id>
                           <phase>process-resources</phase>
                           <goals>
                               <goal>add-source</goal>
                               <goal>compile</goal>
                           </goals>
                       </execution>
                       <execution>
                           <id>scala-test-compile</id>
                           <phase>process-test-resources</phase>
                           <goals>
                               <goal>testCompile</goal>
                           </goals>
                       </execution>
                   </executions>
               </plugin>
               <plugin>
                   <groupId>org.apache.maven.plugins</groupId>
                   <artifactId>maven-compiler-plugin</artifactId>
                   <configuration>
                       <source>1.8</source>
                       <target>1.8</target>
                   </configuration>
                   <executions>
                       <execution>
                           <phase>compile</phase>
                           <goals>
                               <goal>compile</goal>
                           </goals>
                       </execution>
                   </executions>
               </plugin>
           </plugins>
       </build>
   </project>
   ```
   [Reference documentation](https://davidb.github.io/scala-maven-plugin/example_java.html)