package com.example.lifereflexarc.data

import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.POST
import retrofit2.http.Path

interface ApiService {
    @POST("/api/v1/incidents")
    suspend fun createIncident(): ApiResponse<CreateIncidentResponse>

    @GET("/api/v1/incidents/current")
    suspend fun getCurrentIncident(): ApiResponse<IncidentState>

    @POST("/api/v1/incidents/current/join_auto")
    suspend fun joinCurrentAuto(
        @Body body: AutoJoinRequest,
    ): ApiResponse<AutoJoinResponse>

    @POST("/api/v1/incidents/{id}/join")
    suspend fun joinIncident(
        @Path("id") incidentId: String,
        @Body body: JoinRequest,
    ): ApiResponse<JoinResponse>

    @POST("/api/v1/incidents/{id}/actions")
    suspend fun postAction(
        @Path("id") incidentId: String,
        @Body body: ActionRequest,
    ): ApiResponse<ActionResponse>

    @POST("/api/v1/incidents/{id}/sos_start")
    suspend fun sosStart(
        @Path("id") incidentId: String,
    ): ApiResponse<IncidentState>

    @POST("/api/v1/incidents/{id}/sos_cancel")
    suspend fun sosCancel(
        @Path("id") incidentId: String,
    ): ApiResponse<IncidentState>

    @POST("/api/v1/incidents/{id}/trigger")
    suspend fun triggerIncident(
        @Path("id") incidentId: String,
    ): ApiResponse<ActionResponse>

    // Auth endpoints
    @POST("/api/v1/auth/send_code")
    suspend fun sendSmsCode(
        @Body body: SendCodeRequest,
    ): ApiResponse<SendCodeResponse>

    @POST("/api/v1/auth/login")
    suspend fun login(
        @Body body: LoginRequest,
    ): ApiResponse<TokenResponse>

    @POST("/api/v1/auth/register")
    suspend fun register(
        @Body body: RegisterRequest,
    ): ApiResponse<TokenResponse>

    // Geo endpoints
    @POST("/api/v1/geo/location")
    suspend fun reportLocation(
        @Body body: LocationUpdate,
    ): ApiResponse<OkResponse>
}

