package ng.lsia.teacher

import ng.lsia.teacher.data.CanonicalJson
import org.junit.Assert.assertEquals
import org.junit.Test

class CanonicalJsonTest {
    @Test
    fun sortsKeysLikePython() {
        val encoded =
            CanonicalJson.stringify(
                mapOf(
                    "type" to "STUDENT_CREATE",
                    "payload" to mapOf("first_name" to "Kemi", "ca" to 20),
                    "id" to "evt-1",
                    "lamport_clock" to 42L,
                    "student_id" to "FUTA/SS2A/042",
                    "timestamp" to 1726850000000L,
                ),
            )
        assertEquals(
            """{"id":"evt-1","lamport_clock":42,"payload":{"ca":20,"first_name":"Kemi"},"student_id":"FUTA/SS2A/042","timestamp":1726850000000,"type":"STUDENT_CREATE"}""",
            encoded,
        )
    }
}
