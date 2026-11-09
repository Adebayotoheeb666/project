package ng.lsia.teacher.data.sync

import android.content.Context
import androidx.work.CoroutineWorker
import androidx.work.WorkerParameters
import ng.lsia.teacher.data.net.SchoolClient
import ng.lsia.teacher.data.crypto.DeviceKeys

class ReachabilityWorker(context: Context, params: WorkerParameters) : CoroutineWorker(context, params) {
    override suspend fun doWork(): Result {
        val keys = DeviceKeys(applicationContext)
        val base = keys.session("base_url") ?: return Result.success()
        val ok = SchoolClient().health(base)
        keys.session("last_reachability", if (ok) "connected" else "offline")
        return Result.success()
    }
}
