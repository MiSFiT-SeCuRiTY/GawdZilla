package com.misfit.gawdzilla

import android.content.ClipboardManager
import android.content.Context
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch

object ClipboardWatcher {
    private var lastText: String? = null

    fun start(ctx: Context, scope: CoroutineScope) {
        val cm = ctx.getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
        cm.addPrimaryClipChangedListener {
            val clip = cm.primaryClip ?: return@addPrimaryClipChangedListener
            if (clip.itemCount == 0) return@addPrimaryClipChangedListener
            val text = clip.getItemAt(0).coerceToText(ctx).toString()
            if (text.isBlank() || text == lastText) return@addPrimaryClipChangedListener
            lastText = text

            val server = Prefs.serverUrl(ctx)
            val token  = Prefs.enrollToken(ctx)
            if (server.isBlank() || token.isBlank()) return@addPrimaryClipChangedListener
            scope.launch(Dispatchers.IO) {
                ApiClient.postClipboard(server, token, text.take(2000))
            }
        }
    }
}
