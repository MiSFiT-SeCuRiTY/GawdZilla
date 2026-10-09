package com.misfit.gawdzilla

import android.app.admin.DevicePolicyManager
import android.content.ComponentName
import android.content.Intent
import android.os.Build
import android.os.Bundle
import android.provider.Settings
import android.widget.Button
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity

class MainActivity : AppCompatActivity() {

    private lateinit var statusText: TextView
    private lateinit var serverInput: EditText
    private lateinit var tokenInput: EditText

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        val scroll = ScrollView(this)
        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(48, 96, 48, 48)
        }
        scroll.addView(root)

        root.addView(TextView(this).apply {
            text = "GawdZilla Agent"
            textSize = 22f
            setTextColor(0xFF00F0FF.toInt())
        })

        root.addView(TextView(this).apply {
            text = "Parental-control agent. Visible notification while running."
            textSize = 12f
            setPadding(0, 8, 0, 24)
        })

        statusText = TextView(this).apply {
            textSize = 13f
            setPadding(0, 0, 0, 24)
        }
        root.addView(statusText)

        root.addView(TextView(this).apply { text = "Server URL" })
        serverInput = EditText(this).apply {
            hint = "http://192.168.1.10:7777"
            setText(Prefs.serverUrl(this@MainActivity))
        }
        root.addView(serverInput)

        root.addView(TextView(this).apply { text = "Enrollment token" })
        tokenInput = EditText(this).apply {
            hint = "GZ-XXXX-XXXX-XXXX"
            setText(Prefs.enrollToken(this@MainActivity))
        }
        root.addView(tokenInput)

        root.addView(Button(this).apply {
            text = "Save"
            setOnClickListener {
                Prefs.setServerUrl(this@MainActivity, serverInput.text.toString().trim())
                Prefs.setEnrollToken(this@MainActivity, tokenInput.text.toString().trim())
                refreshStatus()
            }
        })

        root.addView(Button(this).apply {
            text = "Open consent screen"
            setOnClickListener {
                startActivity(Intent(this@MainActivity, ConsentActivity::class.java))
            }
        })

        root.addView(Button(this).apply {
            text = "Enable device admin"
            setOnClickListener { enableDeviceAdmin() }
        })

        root.addView(Button(this).apply {
            text = "Become Device Owner (uninstall protection)"
            setOnClickListener { showDeviceOwnerInstructions() }
        })

        root.addView(Button(this).apply {
            text = "Grant usage access"
            setOnClickListener {
                startActivity(Intent(Settings.ACTION_USAGE_ACCESS_SETTINGS))
            }
        })

        root.addView(Button(this).apply {
            text = "Grant notification access"
            setOnClickListener {
                try {
                    startActivity(Intent("android.settings.ACTION_NOTIFICATION_LISTENER_SETTINGS"))
                } catch (_: Exception) {}
            }
        })

        root.addView(Button(this).apply {
            text = "Open app permissions"
            setOnClickListener {
                try {
                    startActivity(Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS).apply {
                        data = android.net.Uri.parse("package:$packageName")
                    })
                } catch (_: Exception) {}
            }
        })

        setContentView(scroll)
        refreshStatus()

        if (Build.VERSION.SDK_INT >= 33) {
            requestPermissions(arrayOf(android.Manifest.permission.POST_NOTIFICATIONS), 1)
        }
    }

    private fun enableDeviceAdmin() {
        val dpm = getSystemService(DEVICE_POLICY_SERVICE) as DevicePolicyManager
        val admin = ComponentName(this, DeviceAdminReceiver::class.java)
        if (dpm.isAdminActive(admin)) {
            statusText.text = "Device admin already active"
            return
        }
        val intent = Intent(DevicePolicyManager.ACTION_ADD_DEVICE_ADMIN).apply {
            putExtra(DevicePolicyManager.EXTRA_DEVICE_ADMIN, admin)
            putExtra(
                DevicePolicyManager.EXTRA_ADD_EXPLANATION,
                "GawdZilla needs device admin to enforce parental controls."
            )
        }
        startActivity(intent)
    }

    private fun showDeviceOwnerInstructions() {
        val dpm = getSystemService(DEVICE_POLICY_SERVICE) as DevicePolicyManager
        val admin = ComponentName(this, DeviceAdminReceiver::class.java)

        if (dpm.isDeviceOwnerApp(packageName)) {
            statusText.text = "Already Device Owner"
            return
        }

        val msg = """
            To make GawdZilla uninstall-proof, the device must be set up as Device Owner.

            This must be done ONE of these ways:

            • Via ADB on a fresh phone (no accounts):
                adb shell dpm set-device-owner com.misfit.gawdzilla/.DeviceAdminReceiver

            • Via QR during factory reset setup
              (Android shows a 6-tap "Welcome" screen on a reset device)

            Once set, the child cannot uninstall GawdZilla, cannot clear
            its data, and cannot disable Device Admin.

            A permanent notification is always visible — required by Android.
        """.trimIndent()

        androidx.appcompat.app.AlertDialog.Builder(this)
            .setTitle("Become Device Owner")
            .setMessage(msg)
            .setPositiveButton("Copy ADB command") { _, _ ->
                val cm = getSystemService(CLIPBOARD_SERVICE) as android.content.ClipboardManager
                cm.setPrimaryClip(android.content.ClipData.newPlainText(
                    "adb",
                    "adb shell dpm set-device-owner com.misfit.gawdzilla/.DeviceAdminReceiver"
                ))
                statusText.text = "ADB command copied"
            }
            .setNegativeButton("Close", null)
            .show()
    }

    private fun refreshStatus() {
        val enrolled = Prefs.isEnrolled(this)
        val dpm = getSystemService(DEVICE_POLICY_SERVICE) as DevicePolicyManager
        val admin = ComponentName(this, DeviceAdminReceiver::class.java)
        val adminActive = dpm.isAdminActive(admin)
        val owner = dpm.isDeviceOwnerApp(packageName)
        statusText.text = buildString {
            append("Status: "); append(if (enrolled) "ENROLLED" else "not enrolled")
            append("  ·  Admin: "); append(if (adminActive) "ACTIVE" else "off")
            append("  ·  Device Owner: "); append(if (owner) "YES" else "no")
        }
    }

    override fun onResume() {
        super.onResume()
        refreshStatus()
    }
}
