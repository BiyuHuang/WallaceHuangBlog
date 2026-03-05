---
title: "Maven: Practical Recipes for JVM Projects"
date: 2022-05-26 14:30:05 +0800
description: Practical Maven recipes — mixed Java/Scala builds, shell execution, assembly packaging, fat JARs, dependency management, and common troubleshooting.
image: /assets/img/maven-logo-black-on-white.png
tags: [BigData, Java]
categories: [Tech]
---

*Written by Biyu Huang, with [Cursor](https://www.cursor.com/) as co-author.*

---

Maven recipes I reach for regularly in Big Data and JVM projects.

---

## 1. Mixed Java/Scala Projects

Use `scala-maven-plugin` to compile Scala alongside Java in a single project. The key is ordering: **Scala compiles first** (in `process-resources` phase), then Java compiles normally.

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

[Reference: scala-maven-plugin docs](https://davidb.github.io/scala-maven-plugin/example_java.html)

**Source layout:**

```
src/main/java/       ← Java sources
src/main/scala/      ← Scala sources
src/test/java/       ← Java tests
src/test/scala/      ← Scala tests
```

---

## 2. Execute Shell Scripts in Build

Use `exec-maven-plugin` to run shell scripts as part of the Maven lifecycle — useful for code generation, environment setup, or custom pre-build steps.

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
                <skip>false</skip>
            </configuration>
        </execution>
    </executions>
</plugin>
```

Set `<skip>true</skip>` to temporarily disable the script without removing the config.

---

## 3. Assembly Plugin: Custom Distribution Archives

Build a distributable zip/tar.gz with your JAR, configs, and scripts in a specific directory structure.

### Plugin Configuration in `pom.xml`

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
                <descriptors>
                    <descriptor>assembly.xml</descriptor>
                </descriptors>
                <finalName>${project.artifactId}</finalName>
            </configuration>
        </execution>
    </executions>
</plugin>
```

### Assembly Descriptor (`assembly.xml`)

```xml
<assembly>
    <id>assembly</id>
    <formats>
        <format>zip</format>
    </formats>
    <fileSets>
        <fileSet>
            <directory>src/main/resources</directory>
            <outputDirectory>conf</outputDirectory>
            <includes>
                <include>*.properties</include>
                <include>*.config</include>
            </includes>
        </fileSet>
    </fileSets>
    <files>
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

**Output structure:**

```
myproject-assembly.zip
├── conf/
│   ├── app.properties
│   └── log4j.config
├── lib/
│   └── demo-1.0.0-SNAPSHOT.jar
└── deploy.sh
```

---

## 4. Fat JAR with maven-shade-plugin

When you need a single executable JAR with all dependencies bundled (common for Spark jobs):

```xml
<plugin>
    <groupId>org.apache.maven.plugins</groupId>
    <artifactId>maven-shade-plugin</artifactId>
    <version>3.5.1</version>
    <executions>
        <execution>
            <phase>package</phase>
            <goals>
                <goal>shade</goal>
            </goals>
            <configuration>
                <transformers>
                    <transformer implementation="org.apache.maven.plugins.shade.resource.ManifestResourceTransformer">
                        <mainClass>com.example.Main</mainClass>
                    </transformer>
                    <transformer implementation="org.apache.maven.plugins.shade.resource.ServicesResourceTransformer"/>
                </transformers>
                <filters>
                    <filter>
                        <artifact>*:*</artifact>
                        <excludes>
                            <exclude>META-INF/*.SF</exclude>
                            <exclude>META-INF/*.DSA</exclude>
                            <exclude>META-INF/*.RSA</exclude>
                        </excludes>
                    </filter>
                </filters>
                <relocations>
                    <relocation>
                        <pattern>com.google.protobuf</pattern>
                        <shadedPattern>shaded.com.google.protobuf</shadedPattern>
                    </relocation>
                </relocations>
            </configuration>
        </execution>
    </executions>
</plugin>
```

**Key sections:**
- `ManifestResourceTransformer`: Sets the main class for `java -jar`
- `ServicesResourceTransformer`: Merges `META-INF/services` files (needed for SPI)
- `filters`: Removes signature files that cause `SecurityException`
- `relocations`: Resolves dependency version conflicts by renaming packages

---

## 5. Dependency Management

### Check Dependency Tree

```bash
# Full tree
mvn dependency:tree

# Filter for a specific artifact
mvn dependency:tree -Dincludes=com.google.protobuf

# Analyze unused/undeclared dependencies
mvn dependency:analyze
```

### Exclude Transitive Dependencies

```xml
<dependency>
    <groupId>org.apache.spark</groupId>
    <artifactId>spark-core_2.12</artifactId>
    <version>3.3.0</version>
    <exclusions>
        <exclusion>
            <groupId>log4j</groupId>
            <artifactId>log4j</artifactId>
        </exclusion>
    </exclusions>
</dependency>
```

### Force a Dependency Version

Use `<dependencyManagement>` in the parent POM to pin versions across all modules:

```xml
<dependencyManagement>
    <dependencies>
        <dependency>
            <groupId>com.google.guava</groupId>
            <artifactId>guava</artifactId>
            <version>31.1-jre</version>
        </dependency>
    </dependencies>
</dependencyManagement>
```

---

## 6. Useful Commands

```bash
# Build, skip tests
mvn clean package -DskipTests

# Build specific module in multi-module project
mvn clean package -pl module-name -am

# Run with a profile
mvn clean package -P production

# Update all snapshot dependencies
mvn clean package -U

# Show effective POM (resolved with parent + profiles)
mvn help:effective-pom

# Show active profiles
mvn help:active-profiles

# Deploy to remote repository
mvn clean deploy -DskipTests
```

### Multi-Module Flags

| Flag | Meaning |
|------|---------|
| `-pl module-a` | Build only module-a |
| `-am` | Also build modules that module-a depends on |
| `-amd` | Also build modules that depend on module-a |
| `-rf :module-b` | Resume build from module-b (after failure) |

---

## 7. Troubleshooting

### "NoSuchMethodError" or "ClassNotFoundException" at Runtime

Almost always a dependency version conflict. Diagnose:

```bash
mvn dependency:tree -Dincludes=<suspected-artifact>
```

Fix with exclusions or shade plugin relocations.

### "Could not resolve dependencies"

```bash
# Force re-download of snapshots and releases
mvn clean install -U

# Clear local cache for a specific artifact
rm -rf ~/.m2/repository/com/example/problematic-artifact/
```

### Build Too Slow

```bash
# Parallel builds (use N threads)
mvn clean package -T 4

# Skip tests for faster iteration
mvn clean package -DskipTests

# Only build changed modules
mvn clean package -pl changed-module -am
```

### "OutOfMemoryError: Java heap space" During Build

```bash
export MAVEN_OPTS="-Xmx2g -XX:MaxMetaspaceSize=512m"
mvn clean package
```
