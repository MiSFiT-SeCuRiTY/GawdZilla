package com.misfit.gawdzilla

import android.content.Context

object Prefs {
    private const val FILE = "gawdzilla_prefs"
    private const val K_SERVER = "server_url"
    private const val K_TOKEN  = "enroll_token"
    private const val K_ENROLLED = "enrolled"

    private fun sp(ctx: Context) = ctx.getSharedPreferences(FILE, Context.MODE_PRIVATE)

    fun serverUrl(ctx: Context): String = sp(ctx).getString(K_SERVER, "") ?: ""
    fun setServerUrl(ctx: Context, v: String) = sp(ctx).edit().putString(K_SERVER, v).apply()

    fun enrollToken(ctx: Context): String = sp(ctx).getString(K_TOKEN, "") ?: ""
    fun setEnrollToken(ctx: Context, v: String) = sp(ctx).edit().putString(K_TOKEN, v).apply()

    fun isEnrolled(ctx: Context): Boolean = sp(ctx).getBoolean(K_ENROLLED, false)
    fun setEnrolled(ctx: Context, v: Boolean) = sp(ctx).edit().putBoolean(K_ENROLLED, v).apply()
}
