package com.misfit.gawdzilla

import android.app.usage.UsageStatsManager
import android.content.Context
import org.json.JSONArray
import org.json.JSONObject

object UsageReader {
    fun collect(ctx: Context, windowMinutes: Long = 60): JSONArray {
        val arr = JSONArray()
        try {
            val usm = ctx.getSystemService(Context.USAGE_STATS_SERVICE) as UsageStatsManager
            val end = System.currentTimeMillis()
            val start = end - windowMinutes * 60_000
            val stats = usm.queryUsageStats(UsageStatsManager.INTERVAL_DAILY, start, end)
                ?: return arr
            val byPkg = HashMap<String, Long>()
            for (s in stats) {
                byPkg[s.packageName] = (byPkg[s.packageName] ?: 0L) + s.totalTimeInForeground
            }
            for ((pkg, ms) in byPkg) {
                val o = JSONObject()
                o.put("package", pkg)
                o.put("seconds", ms / 1000)
                arr.put(o)
            }
        } catch (_: Exception) {}
        return arr
    }
}
