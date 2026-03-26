package com.flag.lifereflexarc.viewmodel

import android.content.Context
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.flag.lifereflexarc.config.AppConfig
import com.flag.lifereflexarc.data.DeviceRealtimeCoordinator
import com.flag.lifereflexarc.data.HealthSnapshot
import com.flag.lifereflexarc.data.IncidentRepository
import com.flag.lifereflexarc.data.IncidentState
import com.flag.lifereflexarc.data.LocationSnapshot
import com.flag.lifereflexarc.data.RouteState
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.collect
import kotlinx.coroutines.launch

class IncidentViewModel(
    private val repository: IncidentRepository = IncidentRepository(
        apiBase = AppConfig.apiBaseUrl,
        wsBase = AppConfig.wsBaseUrl,
    ),
) : ViewModel() {

    private val _incidentId = MutableStateFlow<String?>(null)
    val incidentId: StateFlow<String?> = _incidentId.asStateFlow()

    val state: StateFlow<IncidentState?> = repository.state
    val connected: StateFlow<Boolean> = repository.connected

    private val _error = MutableStateFlow<String?>(null)
    val error: StateFlow<String?> = _error.asStateFlow()
    private val _connecting = MutableStateFlow(false)
    val connecting: StateFlow<Boolean> = _connecting.asStateFlow()
    private val _assignedRole = MutableStateFlow<String?>(null)
    val assignedRole: StateFlow<String?> = _assignedRole.asStateFlow()
    private val _userId = MutableStateFlow<String?>(null)
    private val _location = MutableStateFlow<LocationSnapshot?>(null)
    val location: StateFlow<LocationSnapshot?> = _location.asStateFlow()
    private val _route = MutableStateFlow<RouteState?>(null)
    val route: StateFlow<RouteState?> = _route.asStateFlow()
    private val _health = MutableStateFlow<HealthSnapshot?>(null)
    val health: StateFlow<HealthSnapshot?> = _health.asStateFlow()

    private var realtimeCoordinator: DeviceRealtimeCoordinator? = null

    fun bindDeviceContext(context: Context) {
        if (realtimeCoordinator != null) {
            return
        }
        val coordinator = DeviceRealtimeCoordinator(
            context = context.applicationContext,
            apiBase = AppConfig.apiBaseUrl,
        )
        realtimeCoordinator = coordinator
        viewModelScope.launch {
            coordinator.location.collect { value -> _location.value = value }
        }
        viewModelScope.launch {
            coordinator.route.collect { value -> _route.value = value }
        }
        viewModelScope.launch {
            coordinator.health.collect { value -> _health.value = value }
        }
    }

    fun setLocationPermission(granted: Boolean) {
        realtimeCoordinator?.setLocationPermission(granted)
    }

    fun connectCurrent(userId: String) {
        if (_connecting.value) {
            return
        }
        viewModelScope.launch {
            try {
                _connecting.value = true
                _error.value = null
                _userId.value = userId
                val current = repository.getCurrentIncident()
                _incidentId.value = current.incidentId
                val join = repository.joinCurrentAuto(userId)
                _assignedRole.value = join.role
                repository.connect(current.incidentId)
                realtimeCoordinator?.start(userId, current.incidentId, join.role)
            } catch (e: Exception) {
                _error.value = e.message
            } finally {
                _connecting.value = false
            }
        }
    }

    fun connect(incidentId: String) {
        _incidentId.value = incidentId
        repository.connect(incidentId)
        realtimeCoordinator?.updateSession(incidentId, _assignedRole.value)
    }

    fun createIncident() {
        viewModelScope.launch {
            try {
                _error.value = null
                val id = repository.createIncident()
                _incidentId.value = id
                repository.connect(id)
                realtimeCoordinator?.updateSession(id, _assignedRole.value)
            } catch (e: Exception) {
                _error.value = e.message
            }
        }
    }

    fun joinPrime(userId: String) = join("PRIME", userId)
    fun joinRunner(userId: String) = join("RUNNER", userId)
    fun joinGuide(userId: String) = join("GUIDE", userId)

    private fun join(role: String, userId: String) {
        val id = _incidentId.value ?: return
        viewModelScope.launch {
            try {
                _error.value = null
                repository.join(id, role, userId)
            } catch (e: Exception) {
                _error.value = e.message
            }
        }
    }

    fun actionCprStarted(userId: String) = action("CPR_STARTED", userId)
    fun actionAedPicked(userId: String) = action("AED_PICKED", userId)
    fun actionAedDelivered(userId: String) = action("AED_DELIVERED", userId)
    fun actionAmbulanceArrived(userId: String) = action("AMBULANCE_ARRIVED", userId)

    private fun action(action: String, userId: String) {
        val id = _incidentId.value ?: return
        viewModelScope.launch {
            try {
                _error.value = null
                repository.action(id, action, userId)
            } catch (e: Exception) {
                _error.value = e.message
            }
        }
    }

    fun sosStart() {
        val id = _incidentId.value ?: return
        viewModelScope.launch {
            try {
                _error.value = null
                repository.sosStart(id)
            } catch (e: Exception) {
                _error.value = e.message
            }
        }
    }

    fun sosCancel() {
        val id = _incidentId.value ?: return
        viewModelScope.launch {
            try {
                _error.value = null
                repository.sosCancel(id)
            } catch (e: Exception) {
                _error.value = e.message
            }
        }
    }

    fun triggerIncident() {
        val id = _incidentId.value ?: return
        viewModelScope.launch {
            try {
                _error.value = null
                repository.trigger(id)
            } catch (e: Exception) {
                _error.value = e.message
            }
        }
    }

    fun simulateHealthAlert(alertType: String) {
        realtimeCoordinator?.triggerMockHealthAlert(alertType)
    }
}
