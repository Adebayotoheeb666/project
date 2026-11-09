package ng.lsia.teacher.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.FilterChip
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import ng.lsia.teacher.data.db.StudentEntity
import org.json.JSONObject

private val Paper = Color(0xFFF3ECDE)
private val Ink = Color(0xFF1B1712)
private val Forest = Color(0xFF1D4534)
private val Stamp = Color(0xFF9A3412)

@Composable
fun AppRoot(
    state: UiState,
    onEnroll: (String, String, String, String) -> Unit,
    onScan: () -> Unit,
    scannedQr: String,
    onSetPin: (String, String) -> Unit,
    onUnlock: (String) -> Unit,
    onTab: (Tab) -> Unit,
    onQuery: (String) -> Unit,
    onEdit: (StudentEntity?) -> Unit,
    onSave: (String, String?, String, String, Map<String, String>) -> Unit,
    onPull: () -> Unit,
    onSync: () -> Unit,
    onLock: () -> Unit,
) {
    MaterialTheme(
        colorScheme =
            lightColorScheme(
                primary = Forest,
                onPrimary = Color(0xFFF6EFE2),
                background = Paper,
                surface = Color(0xFFF8F1E3),
                onBackground = Ink,
                onSurface = Ink,
                error = Color(0xFF7F1D1D),
            ),
    ) {
        Surface(modifier = Modifier.fillMaxSize().background(Paper), color = Paper) {
            when (state.gate) {
                Gate.Loading -> Text("Opening register…", modifier = Modifier.padding(24.dp))
                Gate.Enroll -> EnrollForm(state, scannedQr, onEnroll, onScan)
                Gate.SetPin -> PinForm(state, setNew = true, onSetPin = onSetPin, onUnlock = onUnlock)
                Gate.Locked -> PinForm(state, setNew = false, onSetPin = onSetPin, onUnlock = onUnlock)
                Gate.Ready -> ReadyShell(state, onTab, onQuery, onEdit, onSave, onPull, onSync, onLock)
            }
        }
    }
}

@Composable
private fun EnrollForm(
    state: UiState,
    scannedQr: String,
    onEnroll: (String, String, String, String) -> Unit,
    onScan: () -> Unit,
) {
    var qr by remember(scannedQr) { mutableStateOf(scannedQr) }
    var teacher by remember { mutableStateOf("") }
    var password by remember { mutableStateOf("") }
    var device by remember { mutableStateOf("Teacher phone") }
    Column(
        modifier = Modifier.fillMaxSize().padding(24.dp).verticalScroll(rememberScrollState()),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Text("Connect to school computer", style = MaterialTheme.typography.headlineMedium)
        Text("Scan the QR code shown on the school administration computer, then enter your staff account details.")
        Banner(state)
        Button(onClick = onScan, modifier = Modifier.fillMaxWidth()) { Text("Scan QR code") }
        OutlinedTextField(qr, { qr = it }, label = { Text("Enrollment JSON") }, modifier = Modifier.fillMaxWidth())
        OutlinedTextField(teacher, { teacher = it }, label = { Text("Teacher account id") }, modifier = Modifier.fillMaxWidth())
        OutlinedTextField(
            password,
            { password = it },
            label = { Text("Password") },
            visualTransformation = PasswordVisualTransformation(),
            modifier = Modifier.fillMaxWidth(),
        )
        OutlinedTextField(device, { device = it }, label = { Text("Device name") }, modifier = Modifier.fillMaxWidth())
        Button(
            onClick = { onEnroll(qr, teacher, password, device) },
            colors = ButtonDefaults.buttonColors(containerColor = Forest),
            modifier = Modifier.fillMaxWidth(),
        ) { Text("Enroll this phone") }
    }
}

@Composable
private fun PinForm(
    state: UiState,
    setNew: Boolean,
    onSetPin: (String, String) -> Unit,
    onUnlock: (String) -> Unit,
) {
    var pin by remember { mutableStateOf("") }
    var again by remember { mutableStateOf("") }
    Column(modifier = Modifier.fillMaxSize().padding(24.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
        Text(if (setNew) "Set a device PIN" else "Unlock", style = MaterialTheme.typography.headlineMedium)
        Text(if (setNew) "This PIN stays on the phone. It is not sent to the school computer." else "Enter your PIN to open the register.")
        Banner(state)
        OutlinedTextField(
            pin,
            { pin = it.filter(Char::isDigit).take(6) },
            label = { Text("PIN") },
            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.NumberPassword),
            visualTransformation = PasswordVisualTransformation(),
            modifier = Modifier.fillMaxWidth(),
        )
        if (setNew) {
            OutlinedTextField(
                again,
                { again = it.filter(Char::isDigit).take(6) },
                label = { Text("Confirm PIN") },
                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.NumberPassword),
                visualTransformation = PasswordVisualTransformation(),
                modifier = Modifier.fillMaxWidth(),
            )
            Button(onClick = { onSetPin(pin, again) }, modifier = Modifier.fillMaxWidth()) { Text("Save PIN") }
        } else {
            Button(onClick = { onUnlock(pin) }, modifier = Modifier.fillMaxWidth()) { Text("Unlock") }
        }
    }
}

@Composable
private fun ReadyShell(
    state: UiState,
    onTab: (Tab) -> Unit,
    onQuery: (String) -> Unit,
    onEdit: (StudentEntity?) -> Unit,
    onSave: (String, String?, String, String, Map<String, String>) -> Unit,
    onPull: () -> Unit,
    onSync: () -> Unit,
    onLock: () -> Unit,
) {
    Scaffold(
        containerColor = Paper,
        bottomBar = {
            Row(Modifier.fillMaxWidth().background(Forest).padding(8.dp), horizontalArrangement = Arrangement.SpaceEvenly) {
                Tab.entries.forEach { item ->
                    TextButton(onClick = { onTab(item) }) {
                        Text(item.name, color = if (state.tab == item) Color.White else Color(0xFFD7CBB3))
                    }
                }
            }
        },
    ) { padding ->
        Column(Modifier.padding(padding).padding(20.dp)) {
            Banner(state)
            when {
                state.composeNew || state.editing != null -> StudentEditor(state, onSave) { onEdit(null) }
                state.tab == Tab.Desk -> Desk(state, onPull, onSync)
                state.tab == Tab.Classes -> ClassList(state)
                state.tab == Tab.Students -> StudentList(state, onQuery, onEdit)
                state.tab == Tab.Queue -> QueueList(state, onSync)
                state.tab == Tab.Settings -> SettingsPane(state, onPull, onSync, onLock)
            }
        }
    }
}

@Composable
private fun Desk(state: UiState, onPull: () -> Unit, onSync: () -> Unit) {
    Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
        Text(state.schoolName.ifBlank { "School register" }, style = MaterialTheme.typography.headlineMedium)
        Text("Hello, ${state.teacherName.ifBlank { "teacher" }}. Work continues offline; pending changes wait on this phone.")
        StatusChip(state)
        Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
            Button(onClick = onSync) { Text("Sync over Wi-Fi") }
            OutlinedButton(onClick = onPull) { Text("Refresh directory") }
        }
        Text("${state.students.size} students on this phone · ${state.pendingCount} waiting to sync")
    }
}

@Composable
private fun ClassList(state: UiState) {
    LazyColumn(verticalArrangement = Arrangement.spacedBy(8.dp)) {
        items(state.classes, key = { it.id }) { row ->
            Surface(shape = RoundedCornerShape(4.dp), modifier = Modifier.fillMaxWidth()) {
                Column(Modifier.padding(16.dp)) {
                    Text(row.name, fontWeight = FontWeight.SemiBold)
                    Text("${row.id} · ${row.academicYear}")
                }
            }
        }
    }
}

@Composable
private fun StudentList(
    state: UiState,
    onQuery: (String) -> Unit,
    onEdit: (StudentEntity?) -> Unit,
) {
    Column {
        OutlinedTextField(state.query, onQuery, label = { Text("Search") }, modifier = Modifier.fillMaxWidth())
        Spacer(Modifier.height(8.dp))
        Button(onClick = { onEdit(null) }) { Text("Register student") }
        Spacer(Modifier.height(8.dp))
        LazyColumn(contentPadding = PaddingValues(bottom = 48.dp)) {
            items(state.students, key = { it.id }) { row ->
                val data = runCatching { JSONObject(row.dataJson) }.getOrNull()
                Surface(
                    modifier = Modifier.fillMaxWidth().padding(vertical = 6.dp).clickable { onEdit(row) },
                    shape = RoundedCornerShape(4.dp),
                ) {
                    Column(Modifier.padding(16.dp)) {
                        Text(
                            "${data?.optString("first_name").orEmpty()} ${data?.optString("last_name").orEmpty()}".trim()
                                .ifBlank { row.id },
                            fontWeight = FontWeight.SemiBold,
                        )
                        Text("${row.id} · ${row.classId ?: "Unassigned"}")
                        if (row.pending) Text("Pending sync", color = Stamp)
                    }
                }
            }
        }
    }
}

@Composable
private fun StudentEditor(
    state: UiState,
    onSave: (String, String?, String, String, Map<String, String>) -> Unit,
    onCancel: () -> Unit,
) {
    val current = state.editing
    val data = current?.let { runCatching { JSONObject(it.dataJson) }.getOrNull() }
    var id by remember(current) { mutableStateOf(current?.id.orEmpty()) }
    var first by remember(current) { mutableStateOf(data?.optString("first_name").orEmpty()) }
    var last by remember(current) { mutableStateOf(data?.optString("last_name").orEmpty()) }
    var classId by remember(current) { mutableStateOf(current?.classId ?: state.classes.firstOrNull()?.id.orEmpty()) }
    var admission by remember(current) { mutableStateOf(data?.optString("admission_number").orEmpty()) }
    var gender by remember(current) { mutableStateOf(data?.optString("gender").orEmpty()) }
    Column(Modifier.verticalScroll(rememberScrollState()), verticalArrangement = Arrangement.spacedBy(10.dp)) {
        Text(if (current == null) "Register student" else "Student record", style = MaterialTheme.typography.headlineSmall)
        OutlinedTextField(id, { id = it }, label = { Text("Student id") }, enabled = current == null, modifier = Modifier.fillMaxWidth())
        OutlinedTextField(first, { first = it }, label = { Text("First name") }, modifier = Modifier.fillMaxWidth())
        OutlinedTextField(last, { last = it }, label = { Text("Last name") }, modifier = Modifier.fillMaxWidth())
        Text("Class")
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            state.classes.forEach { klass ->
                FilterChip(selected = classId == klass.id, onClick = { classId = klass.id }, label = { Text(klass.id) })
            }
        }
        OutlinedTextField(admission, { admission = it }, label = { Text("Admission number") }, modifier = Modifier.fillMaxWidth())
        OutlinedTextField(gender, { gender = it }, label = { Text("Gender") }, modifier = Modifier.fillMaxWidth())
        Button(
            onClick = {
                onSave(
                    id,
                    classId.ifBlank { null },
                    first,
                    last,
                    mapOf("admission_number" to admission, "gender" to gender),
                )
            },
            modifier = Modifier.fillMaxWidth(),
        ) { Text("Save on this phone") }
        TextButton(onClick = onCancel) { Text("Cancel") }
    }
}

@Composable
private fun QueueList(state: UiState, onSync: () -> Unit) {
    Column {
        if (state.pending.isNotEmpty()) {
            Button(onClick = onSync, modifier = Modifier.fillMaxWidth().padding(bottom = 12.dp)) {
                Text("Transmit ${state.pending.size} pending operations")
            }
        }
        if (state.pending.isEmpty()) {
            Text("No pending operations. All changes on this phone have synchronized with the school computer.")
            return
        }
        LazyColumn(verticalArrangement = Arrangement.spacedBy(8.dp)) {
            items(state.pending, key = { it.id }) { row ->
                Surface(shape = RoundedCornerShape(4.dp), modifier = Modifier.fillMaxWidth()) {
                    Column(Modifier.padding(16.dp)) {
                        Text(row.type.replace('_', ' '), fontWeight = FontWeight.SemiBold)
                        Text(row.studentId ?: "")
                        Text("${row.status} · clock ${row.lamportClock}")
                    }
                }
            }
        }
    }
}

@Composable
private fun SettingsPane(state: UiState, onPull: () -> Unit, onSync: () -> Unit, onLock: () -> Unit) {
    Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
        StatusChip(state)
        Text("Assigned classes: ${state.classes.joinToString { it.id }.ifBlank { "none yet" }}")
        Button(onClick = onSync) { Text("Sync now over local Wi-Fi") }
        OutlinedButton(onClick = onPull) { Text("Pull assigned records") }
        OutlinedButton(onClick = onLock) { Text("Lock phone") }
    }
}

@Composable
private fun StatusChip(state: UiState) {
    val label =
        when {
            state.pendingCount > 0 && state.connected == true -> "Connected · ${state.pendingCount} pending"
            state.pendingCount > 0 -> "Offline · ${state.pendingCount} pending"
            state.connected == true -> "Connected · synced locally"
            state.connected == false -> "Offline"
            else -> "Checking school computer"
        }
    Text(label, color = if (state.pendingCount > 0) Stamp else Forest, fontWeight = FontWeight.SemiBold)
}

@Composable
private fun Banner(state: UiState) {
    state.error?.let { Text(it, color = MaterialTheme.colorScheme.error) }
    state.notice?.let { Text(it, color = Forest) }
}
