package com.flag.lifereflexarc.health

import com.flag.lifereflexarc.data.HealthSnapshot
import kotlinx.coroutines.flow.Flow

interface HealthProvider {
    val sourceLabel: String

    fun stream(
        userId: String,
        incidentId: String?,
    ): Flow<HealthSnapshot>

    fun triggerAlert(alertType: String) = Unit
}
