package com.misfit.gawdzilla

import android.app.ActivityManager
import android.content.Context
import android.os.Build
import android.os.Environment
import android.os.StatFs
import android.os.SystemClock
import org.json.JSONObject

object SysInfo {
    fun collect(ctx: Context): JSONObject {
        val o = JSONObject()
        o.put("hostname", Build.MODEL)
        o.put("platform", "android")
        o.put("os_version", "Android ${Build.VERSION.RELEASE} (API ${Build.VERSION.SDK_INT})")
        o.put("arch", Build.SUPPORTED_ABIS.firstOrNull() ?: "unknown")
        o.put("manufacturer", Build.MANUFACTURER)
        o.put("model", Build.MODEL)
        o.put("uptime_seconds", SystemClock.elapsedRealtime() / 1000)

        try {
            val am = ctx.getSystemService(Context.ACTIVITY_SERVICE) as ActivityManager
            val mi = ActivityManager.MemoryInfo()
            am.getMemoryInfo(mi)
            o.put("ram_total_mb", mi.totalMem / 1024 / 1024)
            o.put("ram_used_mb", (mi.totalMem - mi.availMem) / 1024 / 1024)
            o.put("ram_percent", ((mi.totalMem - mi.availMem) * 100 / mi.totalMem).toInt())
        } catch (_: Exception) {}

        try {
            val stat = StatFs(Environment.getDataDirectory().path)
            val total = stat.blockCountLong * stat.blockSizeLong
            val free  = stat.availableBlocksLong * stat.blockSizeLong
            o.put("disk_total_gb", "%.1f".format(total / 1024.0 / 1024.0 / 1024.0))
            o.put("disk_used_gb",  "%.1f".format((total - free) / 1024.0 / 1024.0 / 1024.0))
            o.put("disk_percent",  ((total - free) * 100 / total).toInt())
        } catch (_: Exception) {}

        return o
    }
}
