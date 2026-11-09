package ng.lsia.teacher.ui

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.combine
import kotlinx.coroutines.flow.flatMapLatest
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch
import ng.lsia.teacher.data.SchoolRepository
import ng.lsia.teacher.data.db.ClassEntity
import ng.lsia.teacher.data.db.PendingOpEntity
import ng.lsia.teacher.data.db.StudentEntity
import ng.lsia.teacher.data.db.SubjectEntity

enum class Gate { Loading, Enroll, SetPin, Locked, Ready }

enum class Tab { Desk, Classes, Students, Queue, Settings }

data class UiState(
    val gate: Gate = Gate.Loading,
    val tab: Tab = Tab.Desk,
    val error: String? = null,
    val notice: String? = null,
    val connected: Boolean? = null,
    val pendingCount: Int = 0,
    val query: String = "",
    val students: List<StudentEntity> = emptyList(),
    val classes: List<ClassEntity> = emptyList(),
    val subjects: List<SubjectEntity> = emptyList(),
    val pending: List<PendingOpEntity> = emptyList(),
    val schoolName: String = "",
    val teacherName: String = "",
    val editing: StudentEntity? = null,
    val composeNew: Boolean = false,
)

class TeacherViewModel(app: Application) : AndroidViewModel(app) {
    private val repo = SchoolRepository(app)
    private val gate = MutableStateFlow(Gate.Loading)
    private val tab = MutableStateFlow(Tab.Desk)
    private val error = MutableStateFlow<String?>(null)
    private val notice = MutableStateFlow<String?>(null)
    private val connected = MutableStateFlow<Boolean?>(null)
    private val query = MutableStateFlow("")
    private val editing = MutableStateFlow<StudentEntity?>(null)
    private val composeNew = MutableStateFlow(false)

    val state: StateFlow<UiState> =
        combine(
            combine(gate, tab, error, notice, connected) { g, t, e, n, c ->
                Triple(g, t, Triple(e, n, c))
            },
            combine(query, editing, composeNew, repo.pendingCount, repo.classes) { q, ed, neu, count, classes ->
                Quint(q, ed, neu, count, classes)
            },
            query.flatMapLatest { repo.search(it) },
            repo.pending,
            repo.subjects,
        ) { first, second, students, pending, subjects ->
            val (g, t, extras) = first
            val (e, n, c) = extras
            UiState(
                gate = g,
                tab = t,
                error = e,
                notice = n,
                connected = c,
                pendingCount = second.count,
                query = second.query,
                students = students,
                classes = second.classes,
                subjects = subjects,
                pending = pending,
                schoolName = repo.keys.session("school_name").orEmpty(),
                teacherName = repo.keys.session("teacher_name").orEmpty(),
                editing = second.editing,
                composeNew = second.composeNew,
            )
        }.stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), UiState())

    init {
        refreshGate()
        viewModelScope.launch {
            if (repo.enrolled()) connected.value = repo.reachable()
        }
    }

    fun refreshGate() {
        gate.value =
            when {
                !repo.enrolled() -> Gate.Enroll
                !repo.hasPin() -> Gate.SetPin
                else -> Gate.Locked
            }
    }

    fun enroll(qr: String, teacherId: String, password: String, deviceName: String) {
        viewModelScope.launch {
            error.value = null
            try {
                repo.enroll(qr, teacherId, password, deviceName)
                gate.value = Gate.SetPin
                notice.value = "Phone enrolled. Set a PIN for this device."
            } catch (ex: Exception) {
                error.value = ex.message ?: "Enrollment failed."
            }
        }
    }

    fun setPin(pin: String, again: String) {
        if (pin.length < 4) {
            error.value = "Use at least 4 digits."
            return
        }
        if (pin != again) {
            error.value = "PIN entries do not match."
            return
        }
        repo.keys.setPin(pin)
        gate.value = Gate.Ready
        error.value = null
    }

    fun unlock(pin: String) {
        if (repo.keys.unlock(pin)) {
            gate.value = Gate.Ready
            error.value = null
        } else {
            error.value = "Wrong PIN."
        }
    }

    fun open(tab: Tab) {
        this.tab.value = tab
        composeNew.value = false
        editing.value = null
    }

    fun setQuery(value: String) {
        query.value = value
    }

    fun edit(student: StudentEntity?) {
        editing.value = student
        composeNew.value = student == null
    }

    fun saveStudent(id: String, classId: String?, first: String, last: String, extra: Map<String, String>) {
        viewModelScope.launch {
            error.value = null
            if (id.isBlank() || first.isBlank() || last.isBlank()) {
                error.value = "Student id, first name, and last name are required."
                return@launch
            }
            val data =
                extra +
                    mapOf(
                        "first_name" to first.trim(),
                        "last_name" to last.trim(),
                    )
            repo.saveStudent(id, classId, data, repo.student(id))
            composeNew.value = false
            editing.value = null
            notice.value = "Saved on this phone. Waiting to sync with the school computer."
            tab.value = Tab.Students
        }
    }

    fun saveScore(studentId: String, subjectId: String, term: String, ca: Double?, exam: Double?) {
        viewModelScope.launch {
            error.value = null
            try {
                repo.saveScore(studentId, subjectId, term, ca, exam)
                notice.value = "Score saved locally. Queued for LAN sync."
            } catch (ex: Exception) {
                error.value = ex.message ?: "Could not record score."
            }
        }
    }

    fun saveAttendance(classId: String, date: String, studentId: String, status: String) {
        viewModelScope.launch {
            error.value = null
            try {
                repo.saveAttendance(classId, date, studentId, status)
                notice.value = "Attendance recorded locally. Queued for LAN sync."
            } catch (ex: Exception) {
                error.value = ex.message ?: "Could not record attendance."
            }
        }
    }

    fun sync() {
        viewModelScope.launch {
            error.value = null
            try {
                val ok = repo.reachable()
                connected.value = ok
                if (!ok) {
                    error.value = "School computer is not reachable on this network."
                    return@launch
                }
                val msg = repo.syncNow()
                notice.value = msg
            } catch (ex: Exception) {
                error.value = ex.message ?: "Sync failed."
            }
        }
    }

    fun pull() {
        viewModelScope.launch {
            error.value = null
            try {
                val ok = repo.reachable()
                connected.value = ok
                if (!ok) {
                    error.value = "School computer is not reachable on this network."
                    return@launch
                }
                repo.pullDirectory()
                notice.value = "Directory refreshed from the school computer."
            } catch (ex: Exception) {
                error.value = ex.message ?: "Could not refresh."
            }
        }
    }

    fun lock() {
        gate.value = Gate.Locked
    }

    private data class Quint(
        val query: String,
        val editing: StudentEntity?,
        val composeNew: Boolean,
        val count: Int,
        val classes: List<ClassEntity>,
    )
}
