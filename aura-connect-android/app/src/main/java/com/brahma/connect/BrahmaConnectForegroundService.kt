package com.aura.connect

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.Service
import android.content.Context
import android.content.Intent
import android.content.pm.ServiceInfo
import android.os.Build
import android.os.IBinder
import androidx.core.app.NotificationCompat
import com.aura.connect.commands.DeviceCommandHandler
import com.aura.connect.core.AgentStateStore
import com.aura.connect.core.ConnectionState
import com.aura.connect.network.AuraWebSocketClient
import com.aura.connect.pairing.PairingStorage
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.launch
import kotlinx.coroutines.flow.collect

class AuraConnectForegroundService : Service() {
    private val scope = CoroutineScope(Job() + Dispatchers.IO)
    private lateinit var storage: PairingStorage
    private lateinit var client: AuraWebSocketClient
    private var started = false

    override fun onCreate() {
        super.onCreate()
        storage = PairingStorage(this)
        client = AuraWebSocketClient(this, storage, DeviceCommandHandler(this))
        createNotificationChannel()
        try {
            val notification = buildNotification("Aura Connect", "Starting connection")
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                startForeground(NOTIFICATION_ID, notification, ServiceInfo.FOREGROUND_SERVICE_TYPE_DATA_SYNC)
            } else {
                startForeground(NOTIFICATION_ID, notification)
            }
        } catch (security: SecurityException) {
            stopSelf()
            return
        } catch (t: Throwable) {
            stopSelf()
            return
        }
        scope.launch {
            AgentStateStore.connectionState.collect {
                updateNotification()
            }
        }
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        when (intent?.action) {
            ACTION_STOP -> {
                client.disconnect()
                stopForeground(STOP_FOREGROUND_REMOVE)
                stopSelf()
                return START_NOT_STICKY
            }
            ACTION_SEND_CHAT -> {
                val text = intent.getStringExtra(EXTRA_CHAT_TEXT)
                if (!text.isNullOrBlank()) {
                    client.sendChatMessage(text)
                }
                return START_STICKY
            }
        }
        connectIfPossible()
        return START_STICKY
    }

    private fun connectIfPossible() {
        val endpoint = AgentStateStore.gateway.value ?: return
        val credential = storage.loadCredential()
        val offer = AgentStateStore.pairingOffer.value ?: storage.loadGatewayHint()
        if (!started) {
            started = true
        }
        client.connect(endpoint, credential, offer)
        AgentStateStore.setConnectionState(ConnectionState.CONNECTING)
    }

    private fun updateNotification() {
        val state = AgentStateStore.connectionState.value
        val text = when (state) {
            ConnectionState.CONNECTED -> "Connected to Aura"
            ConnectionState.CONNECTING -> "Connecting to Aura"
            ConnectionState.RECONNECTING -> "Reconnecting"
            ConnectionState.DISCONNECTED -> "Disconnected"
        }
        val manager = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        manager.notify(NOTIFICATION_ID, buildNotification("Aura Connect", text))
    }

    private fun buildNotification(title: String, text: String): Notification {
        return NotificationCompat.Builder(this, CHANNEL_ID)
            .setSmallIcon(R.drawable.ic_aura_launcher)
            .setContentTitle(title)
            .setContentText(text)
            .setOngoing(true)
            .setPriority(NotificationCompat.PRIORITY_LOW)
            .build()
    }

    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.O) return
        val channel = NotificationChannel(CHANNEL_ID, "Aura Connect", NotificationManager.IMPORTANCE_LOW)
        val manager = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        manager.createNotificationChannel(channel)
    }

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onDestroy() {
        client.disconnect()
        super.onDestroy()
    }

    companion object {
        const val ACTION_STOP = "com.aura.connect.action.STOP"
        const val ACTION_SEND_CHAT = "com.aura.connect.action.SEND_CHAT"
        const val EXTRA_CHAT_TEXT = "com.aura.connect.extra.CHAT_TEXT"
        private const val CHANNEL_ID = "aura_connect"
        private const val NOTIFICATION_ID = 4201
    }
}
