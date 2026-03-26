package com.flag.lifereflexarc.data

import android.content.Context
import com.flag.lifereflexarc.config.AppConfig
import com.flag.lifereflexarc.health.HealthProvider
import com.flag.lifereflexarc.health.MockHealthProvider
import com.flag.lifereflexarc.health.OppoHealthProvider
import com.flag.lifereflexarc.location.DemoLocationProvider
import com.flag.lifereflexarc.location.LocationProvider
import com.flag.lifereflexarc.location.RealLocationProvider
import com.google.gson.Gson
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.collect
import kotlinx.coroutines.launch
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory

class DeviceRealtimeCoordinator(
    private val context: Context,
    private val apiBase: String,
) {
    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.IO)
    private val mockHealthProvider = MockHealthProvider()
    private val oppoHealthProvider = OppoHealthProvider(context)
    private val demoLocationProvider = DemoLocationProvider()
    private val realLocationProvider = RealLocationProvider(context)

    private val apiService: ApiService

    private var locationJob: Job? = null
    private var healthJob: Job? = null

    private var userId: String? = null
    private var incidentId: String? = null
    private var role: String? = null
    private var locationPermissionGranted = false

    private val _location = MutableStateFlow<LocationSnapshot?>(null)
    val location: StateFlow<LocationSnapshot?> = _location.asStateFlow()

    private val _route = MutableStateFlow<RouteState?>(null)
    val route: StateFlow<RouteState?> = _route.asStateFlow()

    private val _health = MutableStateFlow<HealthSnapshot?>(null)
    val health: StateFlow<HealthSnapshot?> = _health.asStateFlow()

    init {
        val logger = HttpLoggingInterceptor().apply {
            level = HttpLoggingInterceptor.Level.BASIC
        }
        val client = OkHttpClient.Builder()
            .addInterceptor(logger)
            .build()
        apiService = Retrofit.Builder()
            .baseUrl(apiBase)
            .client(client)
            .addConverterFactory(GsonConverterFactory.create(Gson()))
            .build()
            .create(ApiService::class.java)
    }

    fun setLocationPermission(granted: Boolean) {
        locationPermissionGranted = granted
        restartLocation()
    }

    fun start(
        userId: String,
        incidentId: String?,
        role: String?,
    ) {
        this.userId = userId
        this.incidentId = incidentId
        this.role = role
        restartLocation()
        restartHealth()
    }

    fun updateSession(
        incidentId: String?,
        role: String?,
    ) {
        this.incidentId = incidentId
        this.role = role
        restartLocation()
        restartHealth()
    }

    fun triggerMockHealthAlert(alertType: String) {
        mockHealthProvider.triggerAlert(alertType)
    }

    private fun restartLocation() {
        locationJob?.cancel()
        val currentUserId = userId ?: return
        val currentRole = role ?: return
        locationJob = scope.launch {
            locationProvider().stream(currentUserId, currentRole, incidentId).collect { snapshot ->
                _location.value = snapshot
                runCatching {
                    apiService.updateLocation(
                        LocationUpdateRequest(
                            userId = snapshot.userId,
                            role = snapshot.role,
                            provider = snapshot.provider,
                            latitude = snapshot.latitude,
                            longitude = snapshot.longitude,
                            accuracyMeters = snapshot.accuracyMeters,
                            speedMetersPerSecond = snapshot.speedMetersPerSecond,
                            bearingDegrees = snapshot.bearingDegrees,
                            updatedTs = snapshot.updatedTs,
                            incidentId = snapshot.incidentId,
                        )
                    )
                    val routePlan = apiService.getRoutePlan(
                        userId = snapshot.userId,
                        role = snapshot.role,
                        latitude = snapshot.latitude,
                        longitude = snapshot.longitude,
                        incidentId = snapshot.incidentId,
                    )
                    _route.value = routePlan.route
                }
            }
        }
    }

    private fun restartHealth() {
        healthJob?.cancel()
        val currentUserId = userId ?: return
        healthJob = scope.launch {
            healthProvider().stream(currentUserId, incidentId).collect { snapshot ->
                _health.value = snapshot
                runCatching {
                    apiService.syncHealthSnapshot(
                        HealthSnapshotRequest(
                            userId = snapshot.userId,
                            source = snapshot.source,
                            providerStatus = snapshot.providerStatus,
                            heartRate = snapshot.heartRate,
                            bloodOxygen = snapshot.bloodOxygen,
                            riskLevel = snapshot.riskLevel,
                            alertType = snapshot.alertType,
                            incidentId = snapshot.incidentId,
                            updatedTs = snapshot.updatedTs,
                        )
                    )
                }
            }
        }
    }

    private fun locationProvider(): LocationProvider {
        val mode = AppConfig.locationProviderMode.lowercase()
        return when {
            mode == "demo" -> demoLocationProvider
            mode == "real" && locationPermissionGranted -> realLocationProvider
            locationPermissionGranted -> realLocationProvider
            else -> demoLocationProvider
        }
    }

    private fun healthProvider(): HealthProvider {
        return when (AppConfig.healthProviderMode.lowercase()) {
            "oppo" -> oppoHealthProvider
            else -> mockHealthProvider
        }
    }
}
