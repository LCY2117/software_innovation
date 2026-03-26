package com.flag.lifereflexarc.location

import android.Manifest
import android.content.Context
import android.content.pm.PackageManager
import android.location.Location
import android.location.LocationListener
import android.location.LocationManager
import androidx.core.content.ContextCompat
import com.flag.lifereflexarc.data.LocationSnapshot
import kotlinx.coroutines.channels.awaitClose
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.callbackFlow

class RealLocationProvider(
    private val context: Context,
) : LocationProvider {
    override val label: String = "ANDROID_GPS"

    override fun stream(
        userId: String,
        role: String,
        incidentId: String?,
    ): Flow<LocationSnapshot> = callbackFlow {
        if (!hasLocationPermission()) {
            close(IllegalStateException("Location permission not granted"))
            return@callbackFlow
        }

        val manager = context.getSystemService(Context.LOCATION_SERVICE) as LocationManager
        val listener = LocationListener { location ->
            trySend(location.toSnapshot(userId, role, incidentId))
        }

        listOf(LocationManager.GPS_PROVIDER, LocationManager.NETWORK_PROVIDER)
            .filter { provider -> manager.isProviderEnabled(provider) }
            .forEach { provider ->
                manager.requestLocationUpdates(provider, 3000L, 3f, listener)
                manager.getLastKnownLocation(provider)?.let { last ->
                    trySend(last.toSnapshot(userId, role, incidentId))
                }
            }

        awaitClose { manager.removeUpdates(listener) }
    }

    private fun hasLocationPermission(): Boolean {
        val fine = ContextCompat.checkSelfPermission(context, Manifest.permission.ACCESS_FINE_LOCATION)
        val coarse = ContextCompat.checkSelfPermission(context, Manifest.permission.ACCESS_COARSE_LOCATION)
        return fine == PackageManager.PERMISSION_GRANTED || coarse == PackageManager.PERMISSION_GRANTED
    }

    private fun Location.toSnapshot(
        userId: String,
        role: String,
        incidentId: String?,
    ): LocationSnapshot = LocationSnapshot(
        userId = userId,
        role = role,
        provider = label,
        latitude = latitude,
        longitude = longitude,
        accuracyMeters = if (hasAccuracy()) accuracy else null,
        speedMetersPerSecond = if (hasSpeed()) speed else null,
        bearingDegrees = if (hasBearing()) bearing else null,
        updatedTs = time.takeIf { it > 0L } ?: System.currentTimeMillis(),
        incidentId = incidentId,
    )
}
