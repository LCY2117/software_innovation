package com.flag.lifereflexarc.location

import com.flag.lifereflexarc.data.LocationSnapshot
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.flow
import kotlin.math.max
import kotlin.math.min

class DemoLocationProvider : LocationProvider {
    override val label: String = "DEMO_ROUTE"

    override fun stream(
        userId: String,
        role: String,
        incidentId: String?,
    ): Flow<LocationSnapshot> = flow {
        val path = routeFor(role.uppercase())
        var index = 0
        while (true) {
            val point = path[index]
            emit(
                LocationSnapshot(
                    userId = userId,
                    role = role,
                    provider = label,
                    latitude = point.first,
                    longitude = point.second,
                    accuracyMeters = 6f,
                    speedMetersPerSecond = 1.4f,
                    bearingDegrees = null,
                    updatedTs = System.currentTimeMillis(),
                    incidentId = incidentId,
                )
            )
            index = min(index + 1, max(path.lastIndex, 0))
            delay(3000)
        }
    }

    private fun routeFor(role: String): List<Pair<Double, Double>> = when (role) {
        "PRIME" -> interpolatePath(
            22.54182 to 114.05571,
            22.54310 to 114.05786,
            8,
        )
        "RUNNER" -> interpolatePath(
            22.54132 to 114.05610,
            22.54418 to 114.05642,
            7,
        )
        "GUIDE" -> interpolatePath(
            22.54468 to 114.05934,
            22.54052 to 114.05892,
            7,
        )
        else -> listOf(22.54310 to 114.05786)
    }

    private fun interpolatePath(
        start: Pair<Double, Double>,
        end: Pair<Double, Double>,
        steps: Int,
    ): List<Pair<Double, Double>> {
        if (steps <= 1) {
            return listOf(end)
        }
        return (0 until steps).map { step ->
            val ratio = step.toDouble() / (steps - 1).toDouble()
            val latitude = start.first + (end.first - start.first) * ratio
            val longitude = start.second + (end.second - start.second) * ratio
            latitude to longitude
        }
    }
}
