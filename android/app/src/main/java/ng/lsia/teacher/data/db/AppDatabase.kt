package ng.lsia.teacher.data.db

import android.content.Context
import androidx.room.Dao
import androidx.room.Database
import androidx.room.Entity
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.PrimaryKey
import androidx.room.Query
import androidx.room.Room
import androidx.room.RoomDatabase
import androidx.room.Update
import kotlinx.coroutines.flow.Flow

@Entity(tableName = "students")
data class StudentEntity(
    @PrimaryKey val id: String,
    val classId: String?,
    val dataJson: String,
    val version: Int,
    val updatedBy: String?,
    val pending: Boolean = false,
)

@Entity(tableName = "classes")
data class ClassEntity(
    @PrimaryKey val id: String,
    val name: String,
    val academicYear: String,
)

@Entity(tableName = "subjects")
data class SubjectEntity(
    @PrimaryKey val id: String,
    val name: String,
    val code: String,
)

@Entity(tableName = "pending_operations")
data class PendingOpEntity(
    @PrimaryKey val id: String,
    val studentId: String?,
    val type: String,
    val payloadJson: String,
    val timestamp: Long,
    val lamportClock: Long,
    val signature: String,
    val status: String,
)

@Entity(tableName = "kv")
data class KvEntity(
    @PrimaryKey val key: String,
    val value: String,
)

@Dao
interface SchoolDao {
    @Query("SELECT * FROM students ORDER BY id")
    fun students(): Flow<List<StudentEntity>>

    @Query("SELECT * FROM students WHERE id = :id")
    suspend fun student(id: String): StudentEntity?

    @Query(
        "SELECT * FROM students WHERE id LIKE '%' || :q || '%' OR dataJson LIKE '%' || :q || '%' ORDER BY id",
    )
    fun searchStudents(q: String): Flow<List<StudentEntity>>

    @Query("SELECT * FROM students WHERE classId = :classId ORDER BY id")
    fun studentsInClass(classId: String): Flow<List<StudentEntity>>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun upsertStudents(rows: List<StudentEntity>)

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun upsertStudent(row: StudentEntity)

    @Query("SELECT * FROM classes ORDER BY name")
    fun classes(): Flow<List<ClassEntity>>

    @Query("SELECT * FROM classes")
    suspend fun classList(): List<ClassEntity>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun upsertClasses(rows: List<ClassEntity>)

    @Query("SELECT * FROM subjects ORDER BY name")
    fun subjects(): Flow<List<SubjectEntity>>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun upsertSubjects(rows: List<SubjectEntity>)

    @Query("SELECT * FROM pending_operations ORDER BY lamportClock")
    fun pending(): Flow<List<PendingOpEntity>>

    @Query("SELECT * FROM pending_operations WHERE status = 'PENDING_SYNC' ORDER BY lamportClock")
    suspend fun pendingOps(): List<PendingOpEntity>

    @Query("SELECT COUNT(*) FROM pending_operations WHERE status = 'PENDING_SYNC'")
    fun pendingCount(): Flow<Int>

    @Insert
    suspend fun insertOp(row: PendingOpEntity)

    @Update
    suspend fun updateOp(row: PendingOpEntity)

    @Query("SELECT value FROM kv WHERE `key` = :key")
    suspend fun kv(key: String): String?

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun putKv(row: KvEntity)
}

@Database(
    entities = [StudentEntity::class, ClassEntity::class, SubjectEntity::class, PendingOpEntity::class, KvEntity::class],
    version = 1,
)
abstract class AppDatabase : RoomDatabase() {
    abstract fun dao(): SchoolDao

    companion object {
        fun create(context: Context): AppDatabase =
            Room.databaseBuilder(context, AppDatabase::class.java, "lsia-teacher.db").build()
    }
}
