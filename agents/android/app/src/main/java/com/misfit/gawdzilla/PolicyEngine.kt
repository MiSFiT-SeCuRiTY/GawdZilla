package com.misfit.gawdzilla

import android.app.admin.DevicePolicyManager
import android.content.ComponentName
import android.content.Context
import android.os.Handler
import android.os.Looper
import org.json.JSONObject
import java.util.Calendar

object PolicyEngine {

    private var schedulerRunning = false

    fun apply(ctx: Context, policyJson: JSONObject) {
        val dpm = ctx.getSystemService(Context.DEVICE_POLICY_SERVICE) as DevicePolicyManager
        val admin = ComponentName(ctx, DeviceAdminReceiver::class.java)
        if (!dpm.isAdminActive(admin)) return

        if (policyJson.optBoolean("instant_lock", false)) {
            try { dpm.lockNow() } catch (_: Exception) {}
        }

        startScreenTimeScheduler(ctx, policyJson)
    }

    fun applyAppRules(ctx: Context, rules: List<Pair<String, String>>) {
        val dpm = ctx.getSystemService(Context.DEVICE_POLICY_SERVICE) as DevicePolicyManager
        val admin = ComponentName(ctx, DeviceAdminReceiver::class.java)
        if (!dpm.isAdminActive(admin)) return

        for ((pkg, action) in rules) {
            try {
                if (action == "block") dpm.setApplicationHidden(admin, pkg, true)
                else                  dpm.setApplicationHidden(admin, pkg, false)
            } catch (_: Exception) {}
        }
    }

    // ─────────────────────────────────────────────────────────
    //  Screen-time scheduler: wakes up every 5 min and locks if
    //  the current time is inside the configured bedtime window.
    // ─────────────────────────────────────────────────────────
    private fun startScreenTimeScheduler(ctx: Context, policyJson: JSONObject) {
        if (schedulerRunning) return
        schedulerRunning = true

        val start = policyJson.optString("bedtime_start", "")
        val end   = policyJson.optString("bedtime_end", "")
        if (start.isBlank() || end.isBlank()) return

        val handler = Handler(Looper.getMainLooper())
        val runnable = object : Runnable {
            override fun run() {
                try {
                    val cal = Calendar.getInstance()
                    val h = cal.get(Calendar.HOUR_OF_DAY)
                    val m = cal.get(Calendar.MINUTE)
                    val nowMin = h * 60 + m

                    val sParts = start.split(":")
                    val eParts = end.split(":")
                    val sMin = (sParts[0].toIntOrNull() ?: 21) * 60 + (sParts.getOrNull(1)?.toIntOrNull() ?: 0)
                    val eMin = (eParts[0].toIntOrNull() ?: 7)  * 60 + (eParts.getOrNull(1)?.toIntOrNull() ?: 0)

                    val inWindow = if (sMin <= eMin) nowMin in sMin until eMin
                                   else nowMin >= sMin || nowMin < eMin

                    if (inWindow) {
                        val dpm = ctx.getSystemService(Context.DEVICE_POLICY_SERVICE) as DevicePolicyManager
                        val admin = ComponentName(ctx, DeviceAdminReceiver::class.java)
                        if (dpm.isAdminActive(admin)) {
                            try { dpm.lockNow() } catch (_: Exception) {}
                        }
                    }
                } catch (_: Exception) {}
                handler.postDelayed(this, 5 * 60 * 1000L)
            }
        }
        handler.post(runnable)
    }
}
