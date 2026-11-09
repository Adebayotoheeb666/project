package ng.lsia.teacher

import android.app.Application
import androidx.work.Constraints
import androidx.work.ExistingPeriodicWorkPolicy
import androidx.work.NetworkType
import androidx.work.PeriodicWorkRequestBuilder
import androidx.work.WorkManager
import ng.lsia.teacher.data.sync.ReachabilityWorker
import java.util.concurrent.TimeUnit

class LsiaTeacherApp : Application() {
    override fun onCreate() {
        super.onCreate()
        val request =
            PeriodicWorkRequestBuilder<ReachabilityWorker>(15, TimeUnit.MINUTES)
                .setConstraints(Constraints.Builder().setRequiredNetworkType(NetworkType.CONNECTED).build())
                .build()
        WorkManager.getInstance(this).enqueueUniquePeriodicWork(
            "lsia-reachability",
            ExistingPeriodicWorkPolicy.KEEP,
            request,
        )
    }
}
