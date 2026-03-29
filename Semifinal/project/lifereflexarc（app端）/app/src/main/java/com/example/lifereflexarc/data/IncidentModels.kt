package com.example.lifereflexarc.data

// ---------------------------------------------------------------------------
// Unified API response envelope (mirrors server ApiResponse<T>)
// ---------------------------------------------------------------------------

data class ApiResponse<T>(
    val code: Int,
    val msg: String,
    val data: T?,
    val traceId: String? = null,
) {
    val isOk: Boolean get() = code == 0
}

// ---------------------------------------------------------------------------
// Incident models
// ---------------------------------------------------------------------------

data class IncidentState(
    val incidentId: String,
    val phase: String,
    val sos: SosState? = null,
    val roles: RoleStates,
    val logs: List<LogEntry>,
)

data class SosState(
    val status: String,
    val startTs: Long?,
    val durationSec: Int,
)

data class RoleStates(
    val PRIME: RoleState,
    val RUNNER: RoleState,
    val GUIDE: RoleState,
)

data class RoleState(
    val status: String?,
    val userId: String?,
)

data class LogEntry(
    val ts: Long,
    val msg: String,
)

data class CreateIncidentResponse(
    val incidentId: String,
)

data class JoinRequest(
    val role: String,
    val userId: String,
)

data class JoinResponse(
    val ok: Boolean,
    val incidentId: String,
    val role: String,
)

data class ActionRequest(
    val action: String,
    val userId: String,
)

data class ActionResponse(
    val ok: Boolean,
    val incidentId: String,
    val phase: String,
)

data class AutoJoinRequest(
    val userId: String,
)

data class AutoJoinResponse(
    val ok: Boolean,
    val incidentId: String,
    val role: String,
)

data class WsMessage(
    val type: String,
    val payload: IncidentState?,
)

// ---------------------------------------------------------------------------
// Auth models
// ---------------------------------------------------------------------------

data class SendCodeRequest(
    val phone: String,
)

data class SendCodeResponse(
    val sent: Boolean,
    val devCode: String? = null,
)

data class LoginRequest(
    val phone: String,
    val code: String,
)

data class RegisterRequest(
    val phone: String,
    val code: String,
    val name: String? = null,
)

data class TokenResponse(
    val accessToken: String,
    val refreshToken: String,
    val userId: String,
    val phone: String,
)

// ---------------------------------------------------------------------------
// Geo models
// ---------------------------------------------------------------------------

data class LocationUpdate(
    val lat: Double,
    val lng: Double,
    val userId: String,
)

data class OkResponse(
    val ok: Boolean,
)

