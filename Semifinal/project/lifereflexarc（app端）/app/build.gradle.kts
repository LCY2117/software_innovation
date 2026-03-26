import java.util.Properties

plugins {
    alias(libs.plugins.android.application)
    alias(libs.plugins.kotlin.compose)
}

val envProperties = Properties().apply {
    val envFile = rootProject.file("env.properties")
    if (envFile.exists()) {
        envFile.inputStream().use(::load)
    }
    val localFile = rootProject.file("local.properties")
    if (localFile.exists()) {
        localFile.inputStream().use(::load)
    }
}

val keystoreProperties = Properties().apply {
    val keystoreFile = rootProject.file("keystore.properties")
    if (keystoreFile.exists()) {
        keystoreFile.inputStream().use(::load)
    }
}

fun quoted(value: String): String = "\"$value\""

fun readConfig(prefix: String?, key: String, defaultValue: String): String {
    val keys = buildList {
        if (!prefix.isNullOrBlank()) {
            add("${prefix}_${key}")
        }
        add(key)
    }
    for (name in keys) {
        val gradleValue = project.findProperty(name) as String?
        if (!gradleValue.isNullOrBlank()) {
            return gradleValue
        }
        val envValue = envProperties.getProperty(name)
        if (!envValue.isNullOrBlank()) {
            return envValue
        }
    }
    return defaultValue
}

val releaseStoreFile = keystoreProperties.getProperty("RELEASE_STORE_FILE")
val hasReleaseSigning =
    !releaseStoreFile.isNullOrBlank() &&
        !keystoreProperties.getProperty("RELEASE_STORE_PASSWORD").isNullOrBlank() &&
        !keystoreProperties.getProperty("RELEASE_KEY_ALIAS").isNullOrBlank() &&
        !keystoreProperties.getProperty("RELEASE_KEY_PASSWORD").isNullOrBlank()

android {
    namespace = "com.flag.lifereflexarc"
    compileSdk {
        version = release(36)
    }

    defaultConfig {
        applicationId = "com.flag.lifereflexarc"
        minSdk = 24
        targetSdk = 36
        versionCode = readConfig(prefix = null, key = "APP_VERSION_CODE", defaultValue = "1").toInt()
        versionName = readConfig(prefix = null, key = "APP_VERSION_NAME", defaultValue = "1.0.0")

        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
    }

    signingConfigs {
        create("release") {
            if (hasReleaseSigning) {
                storeFile = rootProject.file(releaseStoreFile!!)
                storePassword = keystoreProperties.getProperty("RELEASE_STORE_PASSWORD")
                keyAlias = keystoreProperties.getProperty("RELEASE_KEY_ALIAS")
                keyPassword = keystoreProperties.getProperty("RELEASE_KEY_PASSWORD")
            }
        }
    }

    buildTypes {
        debug {
            isDebuggable = true
            applicationIdSuffix = ".debug"
            manifestPlaceholders["usesCleartextTraffic"] = "true"
            buildConfigField("String", "APP_ENV", quoted("debug"))
            buildConfigField("String", "LOCATION_PROVIDER", quoted(readConfig("DEMO_LOCAL", "LOCATION_PROVIDER", "auto")))
            buildConfigField("String", "HEALTH_PROVIDER", quoted(readConfig("DEMO_LOCAL", "HEALTH_PROVIDER", "mock")))
            buildConfigField("String", "API_SCHEME", quoted(readConfig("DEMO_LOCAL", "API_SCHEME", "http")))
            buildConfigField("String", "API_HOST", quoted(readConfig("DEMO_LOCAL", "API_HOST", "10.0.2.2")))
            buildConfigField("String", "API_PORT", quoted(readConfig("DEMO_LOCAL", "API_PORT", "8080")))
            buildConfigField("String", "WS_SCHEME", quoted(readConfig("DEMO_LOCAL", "WS_SCHEME", "ws")))
            buildConfigField("String", "WS_HOST", quoted(readConfig("DEMO_LOCAL", "WS_HOST", "10.0.2.2")))
            buildConfigField("String", "WS_PORT", quoted(readConfig("DEMO_LOCAL", "WS_PORT", "8080")))
            buildConfigField("boolean", "ALLOW_CLEARTEXT", "true")
        }
        create("demoLocal") {
            initWith(getByName("debug"))
            matchingFallbacks += listOf("debug")
            applicationIdSuffix = ".demo"
            manifestPlaceholders["usesCleartextTraffic"] = "true"
            buildConfigField("String", "APP_ENV", quoted("demoLocal"))
            buildConfigField("String", "LOCATION_PROVIDER", quoted(readConfig("DEMO_LOCAL", "LOCATION_PROVIDER", "auto")))
            buildConfigField("String", "HEALTH_PROVIDER", quoted(readConfig("DEMO_LOCAL", "HEALTH_PROVIDER", "mock")))
            buildConfigField("String", "API_SCHEME", quoted(readConfig("DEMO_LOCAL", "API_SCHEME", "http")))
            buildConfigField("String", "API_HOST", quoted(readConfig("DEMO_LOCAL", "API_HOST", "10.0.2.2")))
            buildConfigField("String", "API_PORT", quoted(readConfig("DEMO_LOCAL", "API_PORT", "8080")))
            buildConfigField("String", "WS_SCHEME", quoted(readConfig("DEMO_LOCAL", "WS_SCHEME", "ws")))
            buildConfigField("String", "WS_HOST", quoted(readConfig("DEMO_LOCAL", "WS_HOST", "10.0.2.2")))
            buildConfigField("String", "WS_PORT", quoted(readConfig("DEMO_LOCAL", "WS_PORT", "8080")))
            buildConfigField("boolean", "ALLOW_CLEARTEXT", "true")
        }
        release {
            isMinifyEnabled = false
            manifestPlaceholders["usesCleartextTraffic"] = "false"
            buildConfigField("String", "APP_ENV", quoted("release"))
            buildConfigField("String", "LOCATION_PROVIDER", quoted(readConfig("RELEASE", "LOCATION_PROVIDER", "auto")))
            buildConfigField("String", "HEALTH_PROVIDER", quoted(readConfig("RELEASE", "HEALTH_PROVIDER", "mock")))
            buildConfigField("String", "API_SCHEME", quoted(readConfig("RELEASE", "API_SCHEME", "https")))
            buildConfigField("String", "API_HOST", quoted(readConfig("RELEASE", "API_HOST", "example.com")))
            buildConfigField("String", "API_PORT", quoted(readConfig("RELEASE", "API_PORT", "")))
            buildConfigField("String", "WS_SCHEME", quoted(readConfig("RELEASE", "WS_SCHEME", "wss")))
            buildConfigField("String", "WS_HOST", quoted(readConfig("RELEASE", "WS_HOST", "example.com")))
            buildConfigField("String", "WS_PORT", quoted(readConfig("RELEASE", "WS_PORT", "")))
            buildConfigField("boolean", "ALLOW_CLEARTEXT", "false")
            signingConfig =
                if (hasReleaseSigning) {
                    signingConfigs.getByName("release")
                } else {
                    signingConfigs.getByName("debug")
                }
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro"
            )
        }
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_11
        targetCompatibility = JavaVersion.VERSION_11
    }
    buildFeatures {
        compose = true
        buildConfig = true
    }
    lint {
        // Contest packaging takes priority over release lint gating.
        checkReleaseBuilds = false
    }
}

dependencies {
    implementation(libs.androidx.core.ktx)
    implementation(libs.androidx.lifecycle.runtime.ktx)
    implementation(libs.androidx.activity.compose)
    implementation(platform(libs.androidx.compose.bom))
    implementation(libs.androidx.compose.ui)
    implementation(libs.androidx.compose.ui.graphics)
    implementation(libs.androidx.compose.animation)
    implementation(libs.androidx.compose.ui.tooling.preview)
    implementation(libs.androidx.compose.material3)
    implementation(libs.androidx.lifecycle.viewmodel.compose)
    implementation(libs.coroutines.android)
    implementation(libs.retrofit)
    implementation(libs.retrofit.gson)
    implementation(libs.okhttp)
    implementation(libs.okhttp.logging)
    implementation(libs.gson)
    testImplementation(libs.junit)
    androidTestImplementation(libs.androidx.junit)
    androidTestImplementation(libs.androidx.espresso.core)
    androidTestImplementation(platform(libs.androidx.compose.bom))
    androidTestImplementation(libs.androidx.compose.ui.test.junit4)
    debugImplementation(libs.androidx.compose.ui.tooling)
    debugImplementation(libs.androidx.compose.ui.test.manifest)
}
