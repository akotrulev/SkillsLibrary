import java.util.Properties

plugins {
    java
    id("io.qameta.allure") version "4.3.0"
}

repositories {
    mavenCentral()
}

java {
    toolchain {
        languageVersion.set(JavaLanguageVersion.of(21))
    }
}

dependencies {
    testImplementation("io.rest-assured:rest-assured:6.3.0")
    testImplementation("com.fasterxml.jackson.core:jackson-databind:2.22.4")
    testImplementation("com.fasterxml.jackson.datatype:jackson-datatype-jsr310:2.22.4")
    testImplementation("org.testng:testng:7.12.0")
    testImplementation("org.assertj:assertj-core:3.27.7")
    testImplementation("io.qameta.allure:allure-testng:3.0.0")
    testImplementation("io.qameta.allure:allure-rest-assured:3.0.0")
}

allure {
    version.set("2.46.1")
    adapter {
        allureJavaVersion.set("3.0.0")
    }
}

val envKeys: Set<String> = Properties()
    .apply { file("src/test/resources/env.properties").inputStream().use { load(it) } }
    .stringPropertyNames()

tasks.test {
    useTestNG {
        suites("testng.xml")
    }
    envKeys.forEach { key -> System.getProperty(key)?.let { systemProperty(key, it) } }
}

tasks.register<Jar>("fatJar") {
    group = "build"
    description = "One runnable jar: test classes, test resources, testng.xml and the test runtime classpath."
    archiveFileName.set("${rootProject.name}.jar")
    manifest {
        attributes("Main-Class" to "org.testng.TestNG")
    }
    duplicatesStrategy = DuplicatesStrategy.EXCLUDE
    from(sourceSets.test.get().output)
    from("testng.xml")
    dependsOn(configurations.testRuntimeClasspath)
    from({
        configurations.testRuntimeClasspath.get().filter { it.name.endsWith("jar") }.map { zipTree(it) }
    })
    exclude("META-INF/*.SF", "META-INF/*.DSA", "META-INF/*.RSA", "META-INF/*.EC", "META-INF/INDEX.LIST")
}
