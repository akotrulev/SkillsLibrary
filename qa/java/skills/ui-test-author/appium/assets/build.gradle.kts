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
    testImplementation("io.appium:java-client:11.0.0")
    testImplementation("org.seleniumhq.selenium:selenium-support:4.51.0")
    testImplementation("org.testng:testng:7.12.0")
    testImplementation("io.qameta.allure:allure-testng:3.0.0")
    testImplementation("org.assertj:assertj-core:3.27.7")
}

allure {
    version.set("2.46.1")
    adapter {
        allureJavaVersion.set("3.0.0")
    }
}

tasks.test {
    useTestNG {
        suites("testng.xml")
    }
}
