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
2. Execute shell within maven project. Add `exec-maven-plugin` into `pom.xl`
   ```xml
   <plugin>
        <artifactId>exec-maven-plugin</artifactId>
        <groupId>org.codehaus.mojo</groupId>
        <version>3.0.0</version>
        <executions>
            <execution>
                 <id>exec-to-do-something</id>
                 <phase>generate-sources</phase>
                 <goals>
                     <goal>exec</goal>
                 </goals>
                 <configuration>
                     <executable>/bin/bash</executable>
                     <commandlineArgs>${YOUR_SCRIPT_PATH}/xxx.sh</commandlineArgs>
                     <skip>false</skip> <!-- when this option is set to true, xxx.sh wouldn't be executed. --> 
                 </configuration>
            </execution>
        </executions>
   </plugin>
   ```
   
3. Use `maven-assembly-plugin` to make a single distributable archive.
   1. add `maven-assembly-plugin` into `pom.xml`
      ```xml
      <plugin>
          <groupId>org.apache.maven.plugins</groupId>
          <artifactId>maven-assembly-plugin</artifactId>
          <executions>
              <execution>
                  <id>assembly</id>
                  <phase>package</phase>
                  <goals>
                      <goal>single</goal>
                  </goals>
                  <configuration>
                      <descriptors> <!-- A list of descriptor files to generate from. -->
                          <descriptor>assembly.xml</descriptor>
                      </descriptors>
                      <finalName>${project.artifactId}</finalName> <!-- The filename of the assembled distribution file. -->
                  </configuration>
              </execution>
          </executions>
      </plugin>
      ```
   2. add `assembly.xml` into project
      ```xml
      <assembly>
          <id>assembly</id> <!-- this property will be part of the finalName as suffix -->
          <formats>
              <format>zip</format>
          </formats>
          <fileSets>
              <fileSet>
                  <!-- Configuration files to be placed in conf/ -->
                  <directory>src/main/resources</directory>
                  <outputDirectory>conf</outputDirectory>
                  <includes>
                      <include>*.properties</include>
                      <include>*.config</include>
                  </includes>
              </fileSet>
          </fileSets>
          <files>
              <!-- File in lib -->
              <file>
                  <source>target/${project.artifactId}-${project.version}.jar</source>
                  <destName>demo-1.0.0-SNAPSHOT.jar</destName>
                  <outputDirectory>lib</outputDirectory>
              </file>
              <file>
                  <source>deploy.sh</source>
                  <destName>deploy.sh</destName>
                  <fileMode>0755</fileMode>
                  <outputDirectory>.</outputDirectory>
              </file>
          </files>
      </assembly>
      ```