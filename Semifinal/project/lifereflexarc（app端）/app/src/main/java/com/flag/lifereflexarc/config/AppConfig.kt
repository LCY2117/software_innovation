package com.flag.lifereflexarc.config

import com.flag.lifereflexarc.BuildConfig

object AppConfig {
    val appEnv: String = BuildConfig.APP_ENV
    val isCleartextAllowed: Boolean = BuildConfig.ALLOW_CLEARTEXT
    val locationProviderMode: String = BuildConfig.LOCATION_PROVIDER
    val healthProviderMode: String = BuildConfig.HEALTH_PROVIDER

    val apiBaseUrl: String = buildUrl(
        scheme = BuildConfig.API_SCHEME,
        host = BuildConfig.API_HOST,
        port = BuildConfig.API_PORT,
        path = "/",
    )

    val wsBaseUrl: String = buildUrl(
        scheme = BuildConfig.WS_SCHEME,
        host = BuildConfig.WS_HOST,
        port = BuildConfig.WS_PORT,
        path = "/ws",
    )

    private fun buildUrl(
        scheme: String,
        host: String,
        port: String,
        path: String,
    ): String {
        val normalizedPort = port.trim().takeIf { it.isNotEmpty() }?.let { ":$it" } ?: ""
        return "$scheme://$host$normalizedPort$path"
    }
}
