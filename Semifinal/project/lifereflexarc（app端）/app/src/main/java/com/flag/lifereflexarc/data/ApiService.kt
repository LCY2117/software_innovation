package com.flag.lifereflexarc.data

import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.POST
import retrofit2.http.Path
import retrofit2.http.Query

interface ApiService {
    @POST("/incidents")
    suspend fun createIncident(): CreateIncidentResponse

    @GET("/incidents/current")
    suspend fun getCurrentIncident(): IncidentState

    @POST("/incidents/current/join_auto")
    suspend fun joinCurrentAuto(
        @Body body: AutoJoinRequest,
    ): AutoJoinResponse

    @POST("/incidents/{id}/join")
    suspend fun joinIncident(
        @Path("id") incidentId: String,
        @Body body: JoinRequest,
    )

    @POST("/incidents/{id}/actions")
    suspend fun postAction(
        @Path("id") incidentId: String,
        @Body body: ActionRequest,
    )

    @POST("/incidents/{id}/sos_start")
    suspend fun sosStart(
        @Path("id") incidentId: String,
    )

    @POST("/incidents/{id}/sos_cancel")
    suspend fun sosCancel(
        @Path("id") incidentId: String,
    )

    @POST("/incidents/{id}/trigger")
    suspend fun triggerIncident(
        @Path("id") incidentId: String,
    )

    @POST("/location/update")
    suspend fun updateLocation(
        @Body body: LocationUpdateRequest,
    )

    @GET("/route/plan")
    suspend fun getRoutePlan(
        @Query("userId") userId: String,
        @Query("role") role: String,
        @Query("lat") latitude: Double,
        @Query("lng") longitude: Double,
        @Query("incidentId") incidentId: String? = null,
    ): RoutePlanResponse

    @POST("/health/sync/snapshot")
    suspend fun syncHealthSnapshot(
        @Body body: HealthSnapshotRequest,
    )
}
