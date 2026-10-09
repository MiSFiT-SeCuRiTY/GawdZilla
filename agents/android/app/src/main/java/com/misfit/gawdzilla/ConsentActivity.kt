package com.misfit.gawdzilla

import android.content.Intent
import android.os.Bundle
import android.widget.Button
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity

class ConsentActivity : AppCompatActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        val scroll = ScrollView(this)
        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(48, 96, 48, 48)
        }
        scroll.addView(root)

        root.addView(TextView(this).apply {
            text = "GawdZilla — Consent"
            textSize = 22f
            setTextColor(0xFF00F0FF.toInt())
        })

        root.addView(TextView(this).apply {
            text = "This device will be managed by your parent.\n" +
                   "You will see a persistent notification while the agent runs.\n" +
                   "Camera and microphone use will show the OS indicator.\n" +
                   "Ask your parent to disable any item you don't want shared."
            textSize = 13f
            setPadding(0, 16, 0, 24)
        })

        val items = listOf(
            "Device health (CPU / RAM / storage / battery)",
            "App usage and screen-time limits",
            "Website filtering",
            "Location (while consent is active)",
            "Notification mirroring",
            "Camera (permission-gated, on-device indicator)",
            "Microphone (permission-gated, on-device indicator)",
            "SMS / contacts / call log (Android only)",
        )
        for (item in items) {
            root.addView(TextView(this).apply {
                text = "• $item"
                textSize = 13f
                setPadding(0, 4, 0, 4)
            })
        }

        root.addView(Button(this).apply {
            text = "I agree — start agent"
            setOnClickListener {
                val svc = Intent(this@ConsentActivity, AgentService::class.java)
                if (android.os.Build.VERSION.SDK_INT >= 26) {
                    startForegroundService(svc)
                } else {
                    startService(svc)
                }
                finish()
            }
        })

        root.addView(Button(this).apply {
            text = "Cancel"
            setOnClickListener { finish() }
        })

        setContentView(scroll)
    }
}
