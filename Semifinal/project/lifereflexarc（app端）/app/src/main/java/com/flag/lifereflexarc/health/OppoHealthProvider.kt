package com.flag.lifereflexarc.health

import android.content.Context
import com.flag.lifereflexarc.data.HealthSnapshot
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.flow

class OppoHealthProvider(
    private val context: Context,
) : HealthProvider {
    override val sourceLabel: String = "OPPO_HEALTH"

    override fun stream(
        userId: String,
        incidentId: String?,
    ): Flow<HealthSnapshot> = flow {
        while (true) {
            emit(
                HealthSnapshot(
                    userId = userId,
                    source = sourceLabel,
                    providerStatus = "SDK_PENDING_BINDING",
                    heartRate = null,
                    bloodOxygen = null,
                    riskLevel = "UNKNOWN",
                    incidentId = incidentId,
                    updatedTs = System.currentTimeMillis(),
                )
            )
            delay(15000)
        }
    }
}
