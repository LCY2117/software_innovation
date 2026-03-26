package com.flag.lifereflexarc.ui

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.flag.lifereflexarc.data.HealthSnapshot
import com.flag.lifereflexarc.data.LocationSnapshot
import com.flag.lifereflexarc.data.RouteState
import com.flag.lifereflexarc.ui.components.LogsPanel
import com.flag.lifereflexarc.ui.components.PressableButton
import com.flag.lifereflexarc.ui.components.StatusLight
import com.flag.lifereflexarc.ui.screens.AedDeliveryScreen
import com.flag.lifereflexarc.ui.screens.CreatedMonitoringScreen
import com.flag.lifereflexarc.ui.screens.CprMetronomeScreen
import com.flag.lifereflexarc.ui.screens.EmergencyAlertScreen
import com.flag.lifereflexarc.ui.screens.GuideIdleScreen
import com.flag.lifereflexarc.ui.screens.GuideTaskScreen
import com.flag.lifereflexarc.ui.screens.HandoverArchiveScreen
import com.flag.lifereflexarc.ui.screens.PrimeNavigationScreen
import com.flag.lifereflexarc.ui.screens.RunnerIdleScreen
import com.flag.lifereflexarc.ui.screens.SosCountdownScreen
import com.flag.lifereflexarc.ui.theme.PhoneColors
import com.flag.lifereflexarc.ui.theme.PhoneTokens
import com.flag.lifereflexarc.viewmodel.IncidentViewModel
import kotlinx.coroutines.delay

@Composable
fun PhoneAppRoot(viewModel: IncidentViewModel, userId: String, role: Role = Role.PRIME) {
    val incidentState by viewModel.state.collectAsState(null)
    val connected by viewModel.connected.collectAsState(false)
    val connecting by viewModel.connecting.collectAsState(false)
    val error by viewModel.error.collectAsState(null)
    val assignedRole by viewModel.assignedRole.collectAsState(null)
    val location by viewModel.location.collectAsState(null)
    val route by viewModel.route.collectAsState(null)
    val health by viewModel.health.collectAsState(null)
    val incidentId = incidentState?.incidentId
    val phase = incidentState?.phase
    val sos = incidentState?.sos

    LaunchedEffect(incidentState, connected, connecting, userId) {
        if (incidentState == null && !connected && !connecting) {
            viewModel.connectCurrent(userId)
        }
    }

    val countdown = remember(incidentId) { mutableStateOf(7) }
    val cancelRequested = remember(incidentId) { mutableStateOf(false) }
    val victimView = rememberSaveable(incidentId) { mutableStateOf("monitoring") }
    val nowTick = remember { mutableStateOf(System.currentTimeMillis()) }

    LaunchedEffect(phase, incidentId, sos?.status, sos?.startTs, sos?.durationSec) {
        if (phase != "CREATED") {
            victimView.value = "monitoring"
            cancelRequested.value = false
            countdown.value = 7
            return@LaunchedEffect
        }
        if (sos?.status == "ALERTING" && sos.startTs != null) {
            victimView.value = "alerting"
            cancelRequested.value = false
        } else {
            victimView.value = "monitoring"
            cancelRequested.value = false
            countdown.value = 7
        }
    }

    LaunchedEffect(phase, sos?.status, sos?.startTs, sos?.durationSec) {
        if (phase == "CREATED" && sos?.status == "ALERTING" && sos.startTs != null) {
            while (true) {
                nowTick.value = System.currentTimeMillis()
                delay(500)
                if (phase != "CREATED" || sos?.status != "ALERTING") {
                    return@LaunchedEffect
                }
            }
        }
    }

    if (phase == "CREATED" && sos?.status == "ALERTING" && sos.startTs != null) {
        val duration = sos.durationSec.coerceAtLeast(1)
        val elapsedSec = ((nowTick.value - sos.startTs) / 1000).toInt().coerceAtLeast(0)
        countdown.value = (duration - elapsedSec).coerceAtLeast(0)
    }

    val resolvedRole = when (assignedRole) {
        "PRIME" -> Role.PRIME
        "RUNNER" -> Role.RUNNER
        "GUIDE" -> Role.GUIDE
        else -> role
    }
    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(PhoneTokens.ScreenPadding),
        verticalArrangement = Arrangement.SpaceBetween,
    ) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            StatusLight(isConnected = connected)
            Spacer(modifier = Modifier.width(0.dp))
            Text(
                text = if (connected) "Connected" else "Reconnecting",
                color = PhoneColors.GrayText,
                modifier = Modifier.padding(start = 8.dp)
            )
        }

        Spacer(modifier = Modifier.height(8.dp))
        RealtimeStatusPanel(
            location = location,
            route = route,
            health = health,
            onTriggerAlert = viewModel::simulateHealthAlert,
        )

        Box(
            modifier = Modifier.weight(1f),
            contentAlignment = Alignment.Center
        ) {
            if (incidentState == null) {
                Column(horizontalAlignment = Alignment.CenterHorizontally) {
                    Text(
                        text = if (connecting) "Connecting..." else "Waiting for server...",
                        color = PhoneColors.GrayText
                    )
                    if (error != null) {
                        Spacer(modifier = Modifier.height(8.dp))
                        Text(text = error ?: "", color = PhoneColors.Red)
                    }
                }
            } else {
                when (screenFor(incidentState!!, resolvedRole)) {
                    PhoneScreen.SosCountdown -> {
                        if (victimView.value == "monitoring") {
                            CreatedMonitoringScreen(
                                onConfirm = {
                                    victimView.value = "alerting"
                                    cancelRequested.value = false
                                    viewModel.sosStart()
                                }
                            )
                        } else {
                            SosCountdownScreen(
                                seconds = countdown.value,
                                totalSeconds = sos?.durationSec ?: 10,
                                onCancel = {
                                    cancelRequested.value = true
                                    victimView.value = "monitoring"
                                    viewModel.sosCancel()
                                }
                            )
                        }
                    }
                    PhoneScreen.EmergencyAlert -> EmergencyAlertScreen(
                        incidentId = incidentState!!.incidentId,
                        onJoin = { viewModel.joinPrime(userId) }
                    )
                    PhoneScreen.PrimeNavigation -> PrimeNavigationScreen(
                        onArrived = { viewModel.actionCprStarted(userId) }
                    )
                    PhoneScreen.CprMetronome -> CprMetronomeScreen(
                        onCprStarted = { viewModel.actionCprStarted(userId) }
                    )
                    PhoneScreen.RunnerIdle -> RunnerIdleScreen(
                        onJoin = { viewModel.joinRunner(userId) }
                    )
                    PhoneScreen.AedDelivery -> AedDeliveryScreen(
                        phase = incidentState!!.phase,
                        onAedPicked = { viewModel.actionAedPicked(userId) },
                        onAedDelivered = { viewModel.actionAedDelivered(userId) }
                    )
                    PhoneScreen.GuideIdle -> GuideIdleScreen(
                        onJoin = { viewModel.joinGuide(userId) }
                    )
                    PhoneScreen.GuideTask -> GuideTaskScreen(
                        onAmbulanceArrived = { viewModel.actionAmbulanceArrived(userId) }
                    )
                    PhoneScreen.HandoverArchive -> HandoverArchiveScreen()
                }
            }
        }

        Spacer(modifier = Modifier.height(8.dp))
        LogsPanel(logs = incidentState?.logs ?: emptyList())
    }
}

@Composable
private fun RealtimeStatusPanel(
    location: LocationSnapshot?,
    route: RouteState?,
    health: HealthSnapshot?,
    onTriggerAlert: (String) -> Unit,
) {
    Surface(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(18.dp),
        color = PhoneColors.Slate,
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(14.dp),
            verticalArrangement = Arrangement.spacedBy(10.dp),
        ) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Text(
                    text = "REALTIME LINK",
                    color = PhoneColors.GrayText,
                    fontSize = 11.sp,
                    fontWeight = FontWeight.Bold,
                )
                Text(
                    text = health?.source ?: location?.provider ?: "WAITING",
                    color = PhoneColors.GreenSoft,
                    fontSize = 11.sp,
                    fontWeight = FontWeight.SemiBold,
                )
            }
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
            ) {
                StatusMetric(
                    label = "Location",
                    value = location?.let { "${it.latitude.format(5)}, ${it.longitude.format(5)}" } ?: "--",
                    modifier = Modifier.weight(1f),
                )
                StatusMetric(
                    label = "Route",
                    value = route?.let { "${it.targetLabel} ${it.distanceMeters.toInt()}m" } ?: "--",
                    modifier = Modifier.weight(1f),
                )
                StatusMetric(
                    label = "Health",
                    value = health?.let {
                        val heartRate = it.heartRate?.toString() ?: "--"
                        val spo2 = it.bloodOxygen?.toString() ?: "--"
                        "HR $heartRate / SpO2 $spo2"
                    } ?: "--",
                    modifier = Modifier.weight(1f),
                )
            }
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
            ) {
                val etaSeconds = route?.etaSeconds
                Text(
                    text = if (etaSeconds != null) {
                        "ETA ${etaSeconds / 60}m ${etaSeconds % 60}s"
                    } else {
                        "ETA --"
                    },
                    color = PhoneColors.GrayText,
                    fontSize = 11.sp,
                )
                Text(
                    text = "Risk ${health?.riskLevel ?: "UNKNOWN"}",
                    color = when (health?.riskLevel) {
                        "CRITICAL" -> PhoneColors.Red
                        "HIGH" -> PhoneColors.RedSoft
                        "MEDIUM" -> PhoneColors.Yellow
                        else -> PhoneColors.GrayText
                    },
                    fontSize = 11.sp,
                    fontWeight = FontWeight.SemiBold,
                )
            }
            if (health?.source == "MOCK_HEALTH" || health?.providerStatus == "SDK_PENDING_BINDING") {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(8.dp),
                ) {
                    PressableButton(
                        text = "Fall",
                        onClick = { onTriggerAlert("FALL_DETECTED") },
                        colors = ButtonDefaults.buttonColors(containerColor = PhoneColors.RedSoft),
                        modifier = Modifier.weight(1f),
                    )
                    PressableButton(
                        text = "HR Alert",
                        onClick = { onTriggerAlert("HEART_RATE_EXCEPTION") },
                        colors = ButtonDefaults.buttonColors(containerColor = PhoneColors.Blue),
                        modifier = Modifier.weight(1f),
                    )
                    PressableButton(
                        text = "Low SpO2",
                        onClick = { onTriggerAlert("LOW_SPO2_WARNING") },
                        colors = ButtonDefaults.buttonColors(containerColor = PhoneColors.Yellow),
                        modifier = Modifier.weight(1f),
                    )
                }
            }
        }
    }
}

@Composable
private fun StatusMetric(label: String, value: String, modifier: Modifier = Modifier) {
    Column(modifier = modifier) {
        Text(
            text = label.uppercase(),
            color = PhoneColors.GrayText,
            fontSize = 10.sp,
            fontWeight = FontWeight.Bold,
        )
        Text(
            text = value,
            color = PhoneColors.White,
            fontSize = 12.sp,
            fontWeight = FontWeight.Medium,
        )
    }
}

private fun Double.format(decimals: Int): String = "%.${decimals}f".format(this)
