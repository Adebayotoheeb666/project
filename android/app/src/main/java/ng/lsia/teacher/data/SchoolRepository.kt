package ng.lsia.teacher.data

import android.app.Application
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.withContext
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.buildJsonObject
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.put
import ng.lsia.teacher.data.crypto.DeviceKeys
import ng.lsia.teacher.data.db.AppDatabase
import ng.lsia.teacher.data.db.ClassEntity
import ng.lsia.teacher.data.db.KvEntity
import ng.lsia.teacher.data.db.PendingOpEntity
import ng.lsia.teacher.data.db.StudentEntity
import ng.lsia.teacher.data.db.SubjectEntity
import ng.lsia.teacher.data.net.SchoolClient
import ng.lsia.teacher.data.net.arr
import ng.lsia.teacher.data.net.obj
import ng.lsia.teacher.data.net.str
import ng.lsia.teacher.data.net.toStringMap
import org.json.JSONObject
import java.util.UUID

class SchoolRepository(app: Application) {
    private val db = AppDatabase.create(app)
    private val dao = db.dao()
    val keys = DeviceKeys(app)
    private val client = SchoolClient()

    val students: Flow<List<StudentEntity>> = dao.students()
    val classes: Flow<List<ClassEntity>> = dao.classes()
    val subjects: Flow<List<SubjectEntity>> = dao.subjects()
    val pending: Flow<List<PendingOpEntity>> = dao.pending()
    val pendingCount: Flow<Int> = dao.pendingCount()

    fun search(q: String) = if (q.isBlank()) dao.students() else dao.searchStudents(q)

    fun studentsInClass(classId: String) = dao.studentsInClass(classId)

    suspend fun student(id: String) = dao.student(id)

    suspend fun kv(key: String) = dao.kv(key)

    fun enrolled(): Boolean = keys.session("enrolled") == "1"

    fun hasPin(): Boolean = keys.pinHash() != null

    suspend fun enroll(qrJson: String, teacherId: String, password: String, deviceName: String) {
        val qr = JSONObject(qrJson)
        val baseUrl = qr.getString("base_url")
        val ticket = qr.getString("ticket")
        val result =
            withContext(Dispatchers.IO) {
                client.enroll(
                    baseUrl = baseUrl,
                    ticket = ticket,
                    teacherId = teacherId,
                    password = password,
                    deviceId = keys.deviceId(),
                    deviceName = deviceName.ifBlank { "Teacher phone" },
                    publicKey = keys.publicKeyB64(),
                )
            }
        persistEnrollment(baseUrl, result)
    }

    suspend fun pullDirectory() {
        val base = keys.session("base_url") ?: return
        val token = keys.session("token") ?: return
        val snapshot = withContext(Dispatchers.IO) { client.directory(base, token) }
        applyDirectory(snapshot)
    }

    suspend fun reachable(): Boolean {
        val base = keys.session("base_url") ?: return false
        return withContext(Dispatchers.IO) { client.health(base) }
    }

    suspend fun saveStudent(
        id: String,
        classId: String?,
        data: Map<String, String>,
        existing: StudentEntity?,
    ) {
        val teacherId = keys.session("teacher_id") ?: "teacher"
        val payload = data.toMutableMap()
        payload["class_id"] = classId.orEmpty()
        val type = "STUDENT_UPSERT"
        val entity =
            StudentEntity(
                id = id.trim(),
                classId = classId?.ifBlank { null },
                dataJson = CanonicalJson.stringify(payload),
                version = (existing?.version ?: 0) + 1,
                updatedBy = teacherId,
                pending = true,
            )
        dao.upsertStudent(entity)
        enqueue(type, id.trim(), payload)
    }

    suspend fun saveScore(
        studentId: String,
        subjectId: String,
        term: String,
        caScore: Double?,
        examScore: Double?,
    ) {
        val payload = buildMap<String, Any> {
            put("subject_id", subjectId)
            put("term", term)
            caScore?.let { put("ca_score", it) }
            examScore?.let { put("exam_score", it) }
        }
        enqueue("SCORE_UPDATE", studentId, payload)
    }

    suspend fun saveAttendance(
        classId: String,
        date: String,
        studentId: String,
        status: String,
    ) {
        val payload = mapOf(
            "class_id" to classId,
            "date" to date,
            "status" to status,
        )
        enqueue("ATTENDANCE_RECORD", studentId, payload)
    }

    suspend fun syncNow(): String = withContext(Dispatchers.IO) {
        val baseUrl = keys.session("base_url") ?: throw IllegalStateException("Device is not enrolled.")
        val deviceId = keys.deviceId()
        val now = System.currentTimeMillis()
        val challenge = "HANDSHAKE:$deviceId:$now".toByteArray(Charsets.UTF_8)
        val sig = keys.sign(challenge)

        // 1. Handshake
        client.handshake(baseUrl, deviceId, now, sig)

        // 2. Push Pending Operations
        val pendingList = dao.pendingOps()
        if (pendingList.isNotEmpty()) {
            val ops = pendingList.map { op ->
                buildJsonObject {
                    put("id", op.id)
                    op.studentId?.let { put("student_id", it) }
                    put("type", op.type)
                    val parsedPayload = runCatching { Json.parseToJsonElement(op.payloadJson).jsonObject }.getOrElse { JsonObject(emptyMap()) }
                    put("payload", parsedPayload)
                    put("teacher_id", keys.session("teacher_id") ?: "")
                    put("device_id", deviceId)
                    put("timestamp", op.timestamp)
                    put("lamport_clock", op.lamportClock)
                    put("signature", op.signature)
                }
            }
            val pushRes = client.pushOperations(baseUrl, deviceId, ops)
            val receipts = pushRes.arr("receipts")
            for (rec in receipts) {
                val robj = rec.jsonObject
                val rid = robj.str("id")
                val rstatus = robj.str("status")
                val existing = pendingList.find { it.id == rid }
                if (existing != null) {
                    dao.updateOp(existing.copy(status = rstatus))
                }
            }
        }

        // 3. Pull new events from server
        val lastClock = dao.kv("last_server_clock")?.toLongOrNull() ?: 0L
        val pullRes = client.pullOperations(baseUrl, deviceId, lastClock)
        val latestClock = (pullRes["latest_clock"] as? JsonPrimitive)?.content?.toLongOrNull() ?: lastClock
        dao.putKv(KvEntity("last_server_clock", latestClock.toString()))

        // 4. Update directory
        pullDirectory()

        "Sync complete. All changes synchronized."
    }

    private suspend fun persistEnrollment(baseUrl: String, result: JsonObject) {
        val teacher = result.obj("teacher") ?: JsonObject(emptyMap())
        val school = result.obj("school") ?: JsonObject(emptyMap())
        keys.session("enrolled", "1")
        keys.session("token", result.str("token"))
        keys.session("teacher_id", teacher.str("id"))
        keys.session("teacher_name", teacher.str("name"))
        keys.session("base_url", school.str("base_url").ifBlank { baseUrl })
        keys.session("school_name", school.str("name"))
        keys.session("school_id", school.str("id"))
        dao.putKv(KvEntity("school_name", school.str("name")))
        result.obj("directory")?.let { applyDirectory(it) }
    }

    private suspend fun applyDirectory(snapshot: JsonObject) {
        val classes =
            snapshot.arr("classes").map {
                val row = it.jsonObject
                ClassEntity(row.str("id"), row.str("name"), row.str("academic_year"))
            }
        val subjects =
            snapshot.arr("subjects").map {
                val row = it.jsonObject
                SubjectEntity(row.str("id"), row.str("name"), row.str("code"))
            }
        val students =
            snapshot.arr("students").map {
                val row = it.jsonObject
                val data = row.obj("data")?.toStringMap() ?: emptyMap()
                StudentEntity(
                    id = row.str("id"),
                    classId = row.str("class_id").ifBlank { null },
                    dataJson = CanonicalJson.stringify(data),
                    version = (row["version"] as? JsonPrimitive)?.content?.toIntOrNull() ?: 1,
                    updatedBy = row.str("updated_by").ifBlank { null },
                    pending = false,
                )
            }
        dao.upsertClasses(classes)
        dao.upsertSubjects(subjects)
        dao.upsertStudents(students)
    }

    private suspend fun enqueue(type: String, studentId: String, payload: Map<String, Any>) {
        val clock = (dao.kv("lamport")?.toLongOrNull() ?: 0L) + 1
        dao.putKv(KvEntity("lamport", clock.toString()))
        val eventId = UUID.randomUUID().toString()
        val timestamp = System.currentTimeMillis()
        val canonical =
            CanonicalJson.stringify(
                mapOf(
                    "id" to eventId,
                    "student_id" to studentId,
                    "type" to type,
                    "payload" to payload,
                    "teacher_id" to (keys.session("teacher_id") ?: ""),
                    "device_id" to keys.deviceId(),
                    "timestamp" to timestamp,
                    "lamport_clock" to clock,
                ),
            )
        dao.insertOp(
            PendingOpEntity(
                id = eventId,
                studentId = studentId,
                type = type,
                payloadJson = CanonicalJson.stringify(payload),
                timestamp = timestamp,
                lamportClock = clock,
                signature = keys.sign(canonical.toByteArray(Charsets.UTF_8)),
                status = "PENDING_SYNC",
            ),
        )
    }
}
