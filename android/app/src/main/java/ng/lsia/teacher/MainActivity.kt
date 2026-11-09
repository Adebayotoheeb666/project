package ng.lsia.teacher

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.activity.viewModels
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.google.zxing.integration.android.IntentIntegrator
import ng.lsia.teacher.ui.AppRoot
import ng.lsia.teacher.ui.TeacherViewModel

class MainActivity : ComponentActivity() {
    private val model: TeacherViewModel by viewModels()
    private val scanned = mutableStateOf("")

    private val scan =
        registerForActivityResult(ActivityResultContracts.StartActivityForResult()) { result ->
            val parsed = IntentIntegrator.parseActivityResult(result.resultCode, result.data)
            if (parsed?.contents != null) scanned.value = parsed.contents
        }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            val state by model.state.collectAsStateWithLifecycle()
            val qr by scanned
            AppRoot(
                state = state,
                scannedQr = qr,
                onEnroll = model::enroll,
                onScan = {
                    scan.launch(
                        IntentIntegrator(this)
                            .setDesiredBarcodeFormats(IntentIntegrator.QR_CODE)
                            .setPrompt("Scan the school enrollment code")
                            .setBeepEnabled(false)
                            .createScanIntent(),
                    )
                },
                onSetPin = model::setPin,
                onUnlock = model::unlock,
                onTab = model::open,
                onQuery = model::setQuery,
                onEdit = model::edit,
                onSave = model::saveStudent,
                onPull = model::pull,
                onSync = model::sync,
                onLock = model::lock,
            )
        }
    }
}
