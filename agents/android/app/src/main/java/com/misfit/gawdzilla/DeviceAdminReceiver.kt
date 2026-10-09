package com.misfit.gawdzilla

import android.app.admin.DeviceAdminReceiver
import android.app.admin.DevicePolicyManager
import android.content.ComponentName
import android.content.Context
import android.content.Intent
import android.widget.Toast

class DeviceAdminReceiver : DeviceAdminReceiver() {

    override fun onEnabled(context: Context, intent: Intent) {
        Toast.makeText(context, "GawdZilla device admin enabled", Toast.LENGTH_SHORT).show()
    }

    override fun onDisabled(context: Context, intent: Intent) {
        Toast.makeText(context, "GawdZilla device admin disabled", Toast.LENGTH_SHORT).show()
    }

    override fun onProfileProvisioningComplete(context: Context, intent: Intent) {
        super.onProfileProvisioningComplete(context, intent)
        val dpm = context.getSystemService(Context.DEVICE_POLICY_SERVICE) as DevicePolicyManager
        val admin = ComponentName(context, DeviceAdminReceiver::class.java)

        // Set a device name and lock the child out of uninstall
        try {
            dpm.setDeviceOwnerLockScreenInfo(admin, "Managed by GawdZilla")
        } catch (_: Exception) {}

        try {
            dpm.setUninstallBlocked(admin, context.packageName, true)
        } catch (_: Exception) {}

        // Start the agent service
        val svc = Intent(context, AgentService::class.java)
        if (android.os.Build.VERSION.SDK_INT >= 26) {
            context.startForegroundService(svc)
        } else {
            context.startService(svc)
        }
    }
}
