package com.example.lifereflexarc.data

import com.google.gson.Gson
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory

class IncidentRepository(
    private val apiBase: String,
    private val wsBase: String,
) {
    private val gson = Gson()
    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.IO)

    private val apiService: ApiService
    private val wsClient: WsClient

    private val _state = MutableStateFlow<IncidentState?>(null)
    val state: StateFlow<IncidentState?> = _state.asStateFlow()

    private val _connected = MutableStateFlow(false)
    val connected: StateFlow<Boolean> = _connected.asStateFlow()

    // JWT access token – set after login
    var accessToken: String? = null

    init {
        val logger = HttpLoggingInterceptor().apply {
            level = HttpLoggingInterceptor.Level.BASIC
        }
        val okHttp = OkHttpClient.Builder()
            .addInterceptor(logger)
            .addInterceptor { chain ->
                val req = chain.request()
                val authed = accessToken?.let {
                    req.newBuilder().header("Authorization", "Bearer $it").build()
                } ?: req
                chain.proceed(authed)
            }
            .build()

        apiService = Retrofit.Builder()
            .baseUrl(apiBase)
            .client(okHttp)
            .addConverterFactory(GsonConverterFactory.create(gson))
            .build()
            .create(ApiService::class.java)

        wsClient = WsClient(gson, wsBase)

        scope.launch {
            wsClient.connected.collect { value -> _connected.value = value }
        }
        scope.launch {
            wsClient.latestState.collect { value -> _state.value = value }
        }
    }

    // -----------------------------------------------------------------
    // WebSocket
    // -----------------------------------------------------------------

    fun connect(incidentId: String) {
        wsClient.connect(incidentId, accessToken)
    }

    fun close() {
        wsClient.close()
    }

    // -----------------------------------------------------------------
    // Incident API (unwrap ApiResponse<T>)
    // -----------------------------------------------------------------

    suspend fun getCurrentIncident(): IncidentState {
        return apiService.getCurrentIncident().requireData("getCurrentIncident")
    }

    suspend fun joinCurrentAuto(userId: String): AutoJoinResponse {
        return apiService.joinCurrentAuto(AutoJoinRequest(userId = userId))
            .requireData("joinCurrentAuto")
    }

    suspend fun createIncident(): String {
        return apiService.createIncident().requireData("createIncident").incidentId
    }

    suspend fun join(incidentId: String, role: String, userId: String) {
        apiService.joinIncident(incidentId, JoinRequest(role = role, userId = userId))
    }

    suspend fun action(incidentId: String, action: String, userId: String) {
        apiService.postAction(incidentId, ActionRequest(action = action, userId = userId))
    }

    suspend fun sosStart(incidentId: String) {
        apiService.sosStart(incidentId)
    }

    suspend fun sosCancel(incidentId: String) {
        apiService.sosCancel(incidentId)
    }

    suspend fun trigger(incidentId: String) {
        apiService.triggerIncident(incidentId)
    }

    // -----------------------------------------------------------------
    // Auth API
    // -----------------------------------------------------------------

    suspend fun sendSmsCode(phone: String): SendCodeResponse {
        return apiService.sendSmsCode(SendCodeRequest(phone = phone))
            .requireData("sendSmsCode")
    }

    suspend fun login(phone: String, code: String): TokenResponse {
        val resp = apiService.login(LoginRequest(phone = phone, code = code))
            .requireData("login")
        accessToken = resp.accessToken
        return resp
    }

    suspend fun register(phone: String, code: String, name: String? = null): TokenResponse {
        val resp = apiService.register(RegisterRequest(phone = phone, code = code, name = name))
            .requireData("register")
        accessToken = resp.accessToken
        return resp
    }

    // -----------------------------------------------------------------
    // Geo API
    // -----------------------------------------------------------------

    suspend fun reportLocation(lat: Double, lng: Double, userId: String) {
        apiService.reportLocation(LocationUpdate(lat = lat, lng = lng, userId = userId))
    }
}

/** Unwrap ApiResponse<T> and throw on non-zero code. */
private fun <T> ApiResponse<T>.requireData(call: String): T {
    if (!isOk) throw IllegalStateException("$call failed (code=$code): $msg")
    return data ?: throw IllegalStateException("$call returned null data")
}

