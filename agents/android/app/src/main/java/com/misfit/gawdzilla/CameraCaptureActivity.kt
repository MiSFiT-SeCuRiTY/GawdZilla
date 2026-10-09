package com.misfit.gawdzilla

import android.Manifest
import android.content.pm.PackageManager
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.hardware.camera2.*
import android.os.Bundle
import android.os.Handler
import android.os.HandlerThread
import android.util.Base64
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import java.io.ByteArrayOutputStream

/**
 * Camera capture activity. Must be foreground-visible: Android 10+ refuses
 * background camera access without the OS indicator. This activity:
 *  1. Shows a visible screen saying a photo is being taken
 *  2. Uses Camera2 to grab one frame
 *  3. Posts the frame to the server
 *  4. Finishes
 */
class CameraCaptureActivity : AppCompatActivity() {

    private val scope = CoroutineScope(Dispatchers.IO)
    private var camera: CameraDevice? = null
    private lateinit var bgThread: HandlerThread
    private lateinit var bgHandler: Handler

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        val tv = TextView(this).apply {
            text = "GawdZilla: capturing a photo for your parent.\nThis screen closes automatically."
            textSize = 14f
            setTextColor(0xFF00F0FF.toInt())
            setPadding(48, 96, 48, 48)
        }
        setContentView(tv)

        bgThread = HandlerThread("gz-cam").also { it.start() }
        bgHandler = Handler(bgThread.looper)

        if (ContextCompat.checkSelfPermission(this, Manifest.permission.CAMERA)
            != PackageManager.PERMISSION_GRANTED) {
            ActivityCompat.requestPermissions(this, arrayOf(Manifest.permission.CAMERA), 1)
            finish()
            return
        }

        openCameraAndCapture()
    }

    private fun openCameraAndCapture() {
        val mgr = getSystemService(CAMERA_SERVICE) as CameraManager
        try {
            val id = mgr.cameraIdList.firstOrNull() ?: run { finish(); return }
            mgr.openCamera(id, object : CameraDevice.StateCallback() {
                override fun onOpened(cam: CameraDevice) {
                    camera = cam
                    captureStill(cam)
                }
                override fun onDisconnected(cam: CameraDevice) { cam.close(); finish() }
                override fun onError(cam: CameraDevice, error: Int) { cam.close(); finish() }
            }, bgHandler)
        } catch (_: Exception) { finish() }
    }

    private fun captureStill(cam: CameraDevice) {
        try {
            val surface = android.media.ImageReader.newInstance(
                640, 480, android.graphics.ImageFormat.JPEG, 1
            )
            surface.setOnImageAvailableListener({ reader ->
                val image = reader.acquireLatestImage() ?: return@setOnImageAvailableListener
                try {
                    val buf = image.planes[0].buffer
                    val bytes = ByteArray(buf.remaining())
                    buf.get(bytes)
                    val bmp = BitmapFactory.decodeByteArray(bytes, 0, bytes.size)
                    postFrame(bmp)
                } finally { image.close(); reader.close() }
                cam.close()
                finish()
            }, bgHandler)

            val req = cam.createCaptureRequest(CameraDevice.TEMPLATE_STILL_CAPTURE).apply {
                addTarget(surface.surface)
                set(CaptureRequest.CONTROL_MODE, CameraMetadata.CONTROL_MODE_AUTO)
            }.build()

            cam.createCaptureSession(listOf(surface.surface),
                object : CameraCaptureSession.StateCallback() {
                    override fun onConfigured(session: CameraCaptureSession) {
                        try { session.capture(req, null, bgHandler) } catch (_: Exception) { finish() }
                    }
                    override fun onConfigureFailed(session: CameraCaptureSession) { finish() }
                }, bgHandler)
        } catch (_: Exception) { finish() }
    }

    private fun postFrame(bmp: Bitmap?) {
        bmp ?: return
        val baos = ByteArrayOutputStream()
        bmp.compress(Bitmap.CompressFormat.JPEG, 70, baos)
        val b64 = Base64.encodeToString(baos.toByteArray(), Base64.NO_WRAP)

        val server = Prefs.serverUrl(this)
        val token = Prefs.enrollToken(this)
        if (server.isBlank() || token.isBlank()) return

        scope.launch {
            ApiClient.postMedia(server, token, "camera", b64)
        }
    }
}
