package com.flag.lifereflexarc.health

import com.flag.lifereflexarc.data.HealthSnapshot
import kotlinx.coroutines.channels.awaitClose
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.channelFlow
import kotlinx.coroutines.flow.collect
import kotlinx.coroutines.launch
import kotlin.math.sin

class MockHealthProvider : HealthProvider {
    override val sourceLabel: String = "MOCK_HEALTH"

    private val alertFlow = MutableSharedFlow<String>(extraBufferCapacity = 8)

    override fun stream(
        userId: String,
        incidentId: String?,
    ): Flow<HealthSnapshot> = channelFlow {
        val alertJob = launch {
            alertFlow.collect { alertType ->
                trySend(alertSnapshot(userId, incidentId, alertType))
            }
        }
        val tickerJob = launch {
            var tick = 0
            while (true) {
                val heartRate = 74 + (sin(tick / 2.0) * 7).toInt()
                val bloodOxygen = 97 - (tick % 2)
                trySend(
                    HealthSnapshot(
                        userId = userId,
                        source = sourceLabel,
                        providerStatus = "ACTIVE",
                        heartRate = heartRate,
                        bloodOxygen = bloodOxygen,
                        riskLevel = "NORMAL",
                        updatedTs = System.currentTimeMillis(),
                        incidentId = incidentId,
                    )
                )
                tick += 1
                kotlinx.coroutines.delay(5000)
            }
        }
        awaitClose {
            alertJob.cancel()
            tickerJob.cancel()
        }
    }

    override fun triggerAlert(alertType: String) {
        alertFlow.tryEmit(alertType)
    }

    private fun alertSnapshot(
        userId: String,
        incidentId: String?,
        alertType: String,
    ): HealthSnapshot = when (alertType.uppercase()) {
        "FALL_DETECTED" -> HealthSnapshot(
            userId = userId,
            source = sourceLabel,
            providerStatus = "ACTIVE",
            heartRate = 132,
            bloodOxygen = 89,
            riskLevel = "CRITICAL",
            alertType = "FALL_DETECTED",
            incidentId = incidentId,
            updatedTs = System.currentTimeMillis(),
        )
        "LOW_SPO2_WARNING" -> HealthSnapshot(
            userId = userId,
            source = sourceLabel,
            providerStatus = "ACTIVE",
            heartRate = 108,
            bloodOxygen = 88,
            riskLevel = "HIGH",
            alertType = "LOW_SPO2_WARNING",
            incidentId = incidentId,
            updatedTs = System.currentTimeMillis(),
        )
        else -> HealthSnapshot(
            userId = userId,
            source = sourceLabel,
            providerStatus = "ACTIVE",
            heartRate = 156,
            bloodOxygen = 92,
            riskLevel = "CRITICAL",
            alertType = "HEART_RATE_EXCEPTION",
            incidentId = incidentId,
            updatedTs = System.currentTimeMillis(),
        )
    }
}
