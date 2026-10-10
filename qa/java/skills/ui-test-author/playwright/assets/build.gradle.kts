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
    testImplementation("com.microsoft.playwright:playwright:1.63.0")
    testImplementation("org.testng:testng:7.12.0")
    testImplementation("io.qameta.allure:allure-testng:3.0.0")
    testImplementation("org.assertj:assertj-core:3.27.7")
}

allure {
    adapter {
        allureJavaVersion.set("3.0.0")
    }
}

tasks.test {
    useTestNG {
        suites("testng.xml")
    }
    environment("PLAYWRIGHT_JAVA_SRC", "src/test/java")
}

tasks.register<JavaExec>("installPlaywrightBrowsers") {
    classpath = sourceSets["test"].runtimeClasspath
    mainClass.set("com.microsoft.playwright.CLI")
    args("install", "--with-deps", "chromium")
}

tasks.register<JavaExec>("playwright") {
    classpath = sourceSets["test"].runtimeClasspath
    mainClass.set("com.microsoft.playwright.CLI")
}
