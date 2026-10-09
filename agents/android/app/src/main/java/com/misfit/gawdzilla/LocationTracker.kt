package com.misfit.gawdzilla

import android.Manifest
import android.content.Context
import android.content.pm.PackageManager
import android.location.Location
import android.location.LocationListener
import android.location.LocationManager
import android.os.Bundle
import androidx.core.content.ContextCompat
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch

object LocationTracker {
    private var listener: LocationListener? = null

    fun start(ctx: Context, scope: CoroutineScope) {
        val hasFine = ContextCompat.checkSelfPermission(
            ctx, Manifest.permission.ACCESS_FINE_LOCATION
        ) == PackageManager.PERMISSION_GRANTED
        if (!hasFine) return

        val lm = ctx.getSystemService(Context.LOCATION_SERVICE) as LocationManager
        if (listener != null) return

        listener = object : LocationListener {
            override fun onLocationChanged(loc: Location) {
                val server = Prefs.serverUrl(ctx)
                val token  = Prefs.enrollToken(ctx)
                if (server.isBlank() || token.isBlank()) return
                scope.launch(Dispatchers.IO) {
                    ApiClient.postLocation(
                        server, token,
                        loc.latitude, loc.longitude,
                        if (loc.hasAccuracy()) loc.accuracy else null,
                        if (loc.hasSpeed()) loc.speed else null
                    )
                }
            }
            override fun onProviderDisabled(provider: String) {}
            override fun onProviderEnabled(provider: String) {}
            @Deprecated("") override fun onStatusChanged(provider: String?, status: Int, extras: Bundle?) {}
        }

        try {
            lm.requestLocationUpdates(LocationManager.GPS_PROVIDER, 60_000L, 25f, listener!!)
        } catch (_: Exception) {}
        try {
            lm.requestLocationUpdates(LocationManager.NETWORK_PROVIDER, 120_000L, 50f, listener!!)
        } catch (_: Exception) {}
    }

    fun stop(ctx: Context) {
        val lm = ctx.getSystemService(Context.LOCATION_SERVICE) as LocationManager
        listener?.let { lm.removeUpdates(it) }
        listener = null
    }
}
