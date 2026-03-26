package com.flag.lifereflexarc.data

data class LocationSnapshot(
    val userId: String,
    val role: String,
    val provider: String,
    val latitude: Double,
    val longitude: Double,
    val accuracyMeters: Float? = null,
    val speedMetersPerSecond: Float? = null,
    val bearingDegrees: Float? = null,
    val updatedTs: Long,
    val incidentId: String? = null,
)

data class LocationUpdateRequest(
    val userId: String,
    val role: String,
    val provider: String,
    val latitude: Double,
    val longitude: Double,
    val accuracyMeters: Float? = null,
    val speedMetersPerSecond: Float? = null,
    val bearingDegrees: Float? = null,
    val updatedTs: Long,
    val incidentId: String? = null,
)

data class ScenePoint(
    val key: String,
    val label: String,
    val latitude: Double,
    val longitude: Double,
)

data class RouteWaypoint(
    val latitude: Double,
    val longitude: Double,
)

data class RouteState(
    val userId: String,
    val role: String,
    val targetKey: String,
    val targetLabel: String,
    val distanceMeters: Double,
    val etaSeconds: Int,
    val polyline: List<RouteWaypoint>,
)

data class HealthSnapshot(
    val userId: String,
    val source: String,
    val providerStatus: String,
    val heartRate: Int?,
    val bloodOxygen: Int?,
    val riskLevel: String,
    val alertType: String? = null,
    val incidentId: String? = null,
    val updatedTs: Long,
)

data class HealthSnapshotRequest(
    val userId: String,
    val source: String,
    val providerStatus: String,
    val heartRate: Int?,
    val bloodOxygen: Int?,
    val riskLevel: String,
    val alertType: String? = null,
    val incidentId: String? = null,
    val updatedTs: Long,
)

data class HealthAlert(
    val userId: String,
    val alertType: String,
    val riskLevel: String,
    val message: String,
    val updatedTs: Long,
)

data class RoutePlanResponse(
    val scene: List<ScenePoint>,
    val route: RouteState,
)

data class LocationStatePayload(
    val scene: List<ScenePoint>,
    val locations: List<LocationSnapshot>,
    val routes: List<RouteState>,
)

data class HealthStatePayload(
    val snapshots: List<HealthSnapshot>,
    val latestAlert: HealthAlert? = null,
)
