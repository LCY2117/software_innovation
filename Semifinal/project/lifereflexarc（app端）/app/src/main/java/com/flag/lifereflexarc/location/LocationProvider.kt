package com.flag.lifereflexarc.location

import com.flag.lifereflexarc.data.LocationSnapshot
import kotlinx.coroutines.flow.Flow

interface LocationProvider {
    val label: String

    fun stream(
        userId: String,
        role: String,
        incidentId: String?,
    ): Flow<LocationSnapshot>
}
