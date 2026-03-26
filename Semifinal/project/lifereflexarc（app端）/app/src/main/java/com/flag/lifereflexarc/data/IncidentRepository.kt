package com.flag.lifereflexarc.data

import com.google.gson.Gson
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
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

    init {
        val logger = HttpLoggingInterceptor().apply {
            level = HttpLoggingInterceptor.Level.BASIC
        }
        val okHttp = OkHttpClient.Builder()
            .addInterceptor(logger)
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

    fun connect(incidentId: String) {
        wsClient.connect(incidentId)
    }

    fun close() {
        wsClient.close()
    }

    suspend fun getCurrentIncident(): IncidentState {
        return apiService.getCurrentIncident()
    }

    suspend fun joinCurrentAuto(userId: String): AutoJoinResponse {
        return apiService.joinCurrentAuto(AutoJoinRequest(userId = userId))
    }

    suspend fun createIncident(): String {
        return apiService.createIncident().incidentId
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
}
