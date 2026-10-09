package com.misfit.gawdzilla

import android.Manifest
import android.content.pm.PackageManager
import android.media.MediaRecorder
import android.os.Build
import android.os.Bundle
import android.os.Environment
import android.util.Base64
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import java.io.File

class MicCaptureActivity : AppCompatActivity() {

    private val scope = CoroutineScope(Dispatchers.IO)
    private var recorder: MediaRecorder? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        val tv = TextView(this).apply {
            text = "GawdZilla: recording a short audio clip for your parent.\nThis screen closes automatically."
            textSize = 14f
            setTextColor(0xFFFF2BD6.toInt())
            setPadding(48, 96, 48, 48)
        }
        setContentView(tv)

        if (ContextCompat.checkSelfPermission(this, Manifest.permission.RECORD_AUDIO)
            != PackageManager.PERMISSION_GRANTED) {
            ActivityCompat.requestPermissions(this, arrayOf(Manifest.permission.RECORD_AUDIO), 1)
            finish()
            return
        }

        startRecording()
    }

    private fun startRecording() {
        try {
            val out = File(cacheDir, "gz-mic-${System.currentTimeMillis()}.m4a")
            recorder = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
                MediaRecorder(this)
            } else {
                @Suppress("DEPRECATION") MediaRecorder()
            }.apply {
                setAudioSource(MediaRecorder.AudioSource.MIC)
                setOutputFormat(MediaRecorder.OutputFormat.MPEG_4)
                setAudioEncoder(MediaRecorder.AudioEncoder.AAC)
                setAudioSamplingRate(22050)
                setAudioEncodingBitRate(64000)
                setOutputFile(out.absolutePath)
                prepare()
                start()
            }

            // Record for 15 seconds, then stop and upload
            android.os.Handler(mainLooper).postDelayed({
                try {
                    recorder?.stop()
                    recorder?.release()
                    recorder = null
                    val bytes = out.readBytes()
                    val b64 = Base64.encodeToString(bytes, Base64.NO_WRAP)
                    val server = Prefs.serverUrl(this)
                    val token = Prefs.enrollToken(this)
                    if (server.isNotBlank() && token.isNotBlank()) {
                        scope.launch { ApiClient.postMedia(server, token, "mic", b64) }
                    }
                    out.delete()
                } catch (_: Exception) {}
                finish()
            }, 15_000L)

        } catch (_: Exception) { finish() }
    }
}
