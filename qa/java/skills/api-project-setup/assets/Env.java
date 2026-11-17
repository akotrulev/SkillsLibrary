package com.example.apitests.support;

import java.io.IOException;
import java.io.InputStream;
import java.io.UncheckedIOException;
import java.util.Properties;
import java.util.stream.Stream;

/**
 * The suite's configuration. A key resolves from the environment variable, then the JVM system property
 * ({@code -DKEY=value}), then {@code env.properties} on the test classpath. A secret has no entry in the
 * file, so the environment is its only source.
 */
public final class Env {
    public static final String API_URL = "API_URL";

    private static final String DEFAULTS_FILE = "env.properties";
    private static final Properties DEFAULTS = loadDefaults();

    private Env() {
    }

    public static String apiUrl() {
        return required(API_URL);
    }

    public static String required(String name) {
        return Stream.of(System.getenv(name), System.getProperty(name), DEFAULTS.getProperty(name))
                .filter(value -> value != null && !value.isBlank())
                .findFirst()
                .orElseThrow(() -> new IllegalStateException(
                        name + " is not set: export it, pass -D" + name + "=…, or give it a default in " + DEFAULTS_FILE));
    }

    private static Properties loadDefaults() {
        Properties defaults = new Properties();
        try (InputStream file = Env.class.getClassLoader().getResourceAsStream(DEFAULTS_FILE)) {
            if (file == null) {
                throw new IllegalStateException(DEFAULTS_FILE + " is not on the test classpath (src/test/resources)");
            }
            defaults.load(file);
        } catch (IOException e) {
            throw new UncheckedIOException("Cannot read " + DEFAULTS_FILE, e);
        }
        return defaults;
    }
}
