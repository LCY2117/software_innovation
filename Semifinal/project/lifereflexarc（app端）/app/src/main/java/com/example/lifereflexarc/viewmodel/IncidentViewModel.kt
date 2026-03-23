package com.example.lifereflexarc.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.example.lifereflexarc.data.IncidentRepository
import com.example.lifereflexarc.data.IncidentState
import com.example.lifereflexarc.data.TokenResponse
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

class IncidentViewModel(
    private val repository: IncidentRepository = IncidentRepository(
        apiBase = "http://111.230.52.99:8080/",
        wsBase = "ws://111.230.52.99:8080/ws",
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
    private val _authToken = MutableStateFlow<String?>(null)
    val authToken: StateFlow<String?> = _authToken.asStateFlow()

    // -----------------------------------------------------------------
    // Auth
    // -----------------------------------------------------------------

    fun login(phone: String, code: String) {
        viewModelScope.launch {
            try {
                _error.value = null
                val token = repository.login(phone, code)
                _authToken.value = token.accessToken
                _userId.value = token.userId
            } catch (e: Exception) {
                _error.value = e.message
            }
        }
    }

    fun sendSmsCode(phone: String, onCode: (String?) -> Unit = {}) {
        viewModelScope.launch {
            try {
                _error.value = null
                val resp = repository.sendSmsCode(phone)
                onCode(resp.devCode)
            } catch (e: Exception) {
                _error.value = e.message
                onCode(null)
            }
        }
    }

    // -----------------------------------------------------------------
    // Incident
    // -----------------------------------------------------------------

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
    }

    fun createIncident() {
        viewModelScope.launch {
            try {
                _error.value = null
                val id = repository.createIncident()
                _incidentId.value = id
                repository.connect(id)
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

    fun reportLocation(lat: Double, lng: Double) {
        val userId = _userId.value ?: return
        viewModelScope.launch {
            try {
                repository.reportLocation(lat, lng, userId)
            } catch (_: Exception) {
                // Location reporting is best-effort; don't show error to user
            }
        }
    }
}
