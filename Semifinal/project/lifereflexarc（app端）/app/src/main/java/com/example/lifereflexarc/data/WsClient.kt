package com.example.lifereflexarc.data

import com.google.gson.Gson
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.launch
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.Response
import okhttp3.WebSocket
import okhttp3.WebSocketListener
import java.util.concurrent.TimeUnit
import kotlin.math.min

class WsClient(
    private val gson: Gson,
    private val baseWsUrl: String,
) {
    val connected = MutableStateFlow(false)
    val latestState = MutableStateFlow<IncidentState?>(null)

    private val client = OkHttpClient.Builder()
        .readTimeout(0, TimeUnit.MILLISECONDS)
        .build()

    private var webSocket: WebSocket? = null
    private var incidentId: String? = null
    private var authToken: String? = null
    private var reconnectAttempt = 0
    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.IO)

    fun connect(id: String, token: String? = null) {
        incidentId = id
        authToken = token
        reconnectAttempt = 0
        openSocket()
    }

    fun close() {
        webSocket?.close(1000, "closed")
        webSocket = null
        connected.value = false
    }

    private fun openSocket() {
        val id = incidentId ?: return
        val urlBuilder = StringBuilder("$baseWsUrl?incidentId=$id")
        authToken?.let { urlBuilder.append("&token=$it") }

        val request = Request.Builder()
            .url(urlBuilder.toString())
            .build()

        webSocket = client.newWebSocket(request, object : WebSocketListener() {
            override fun onOpen(ws: WebSocket, response: Response) {
                connected.value = true
                reconnectAttempt = 0
            }

            override fun onMessage(ws: WebSocket, text: String) {
                try {
                    val message = gson.fromJson(text, WsMessage::class.java)
                    when (message.type) {
                        "STATE" -> if (message.payload != null) {
                            latestState.value = message.payload
                        }
                        "PING" -> ws.send(gson.toJson(mapOf("type" to "PONG")))
                        // PONG is a no-op
                    }
                } catch (_: Exception) {
                    // ignore invalid payload
                }
            }

            override fun onClosed(ws: WebSocket, code: Int, reason: String) {
                connected.value = false
                scheduleReconnect()
            }

            override fun onFailure(ws: WebSocket, t: Throwable, response: Response?) {
                connected.value = false
                scheduleReconnect()
            }
        })
    }

    private fun scheduleReconnect() {
        val id = incidentId ?: return
        val delayMs = min(10_000L, 1_000L * (1 shl reconnectAttempt))
        reconnectAttempt = min(reconnectAttempt + 1, 4)
        scope.launch {
            delay(delayMs)
            if (incidentId == id) {
                openSocket()
            }
        }
    }
}
