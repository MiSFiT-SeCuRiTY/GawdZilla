package com.misfit.gawdzilla

import android.service.notification.NotificationListenerService
import android.service.notification.StatusBarNotification
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch

class NotificationListener : NotificationListenerService() {

    private val scope = CoroutineScope(Dispatchers.IO)

    override fun onNotificationPosted(sbn: StatusBarNotification?) {
        sbn ?: return
        val pkg = sbn.packageName ?: return
        val extras = sbn.notification?.extras ?: return
        val title = extras.getCharSequence("android.title")?.toString() ?: ""
        val text  = extras.getCharSequence("android.text")?.toString()  ?: ""

        val server = Prefs.serverUrl(this)
        val token  = Prefs.enrollToken(this)
        if (server.isBlank() || token.isBlank()) return

        scope.launch {
            ApiClient.postNotification(server, token, pkg, title, text)
        }
    }
}
