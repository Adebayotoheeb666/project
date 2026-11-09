package ng.lsia.teacher.data.net

import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonArray
import kotlinx.serialization.json.JsonNull
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.buildJsonObject
import kotlinx.serialization.json.contentOrNull
import kotlinx.serialization.json.jsonArray
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import kotlinx.serialization.json.put
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import java.util.concurrent.TimeUnit

class SchoolException(val code: String, override val message: String) : Exception(message)

class SchoolClient {
    private val json = Json { ignoreUnknownKeys = true }
    private val http =
        OkHttpClient.Builder()
            .connectTimeout(8, TimeUnit.SECONDS)
            .readTimeout(20, TimeUnit.SECONDS)
            .build()
    private val media = "application/json; charset=utf-8".toMediaType()

    fun health(baseUrl: String): Boolean =
        try {
            val request = Request.Builder().url("${baseUrl.trimEnd('/')}/api/v1/health").build()
            http.newCall(request).execute().use { it.isSuccessful }
        } catch (_: Exception) {
            false
        }

    fun inspectTicket(baseUrl: String, ticket: String): JsonObject {
        return get(baseUrl, "/api/v1/devices/enrollment-tickets/$ticket").jsonObject
    }

    fun enroll(
        baseUrl: String,
        ticket: String,
        teacherId: String,
        password: String,
        deviceId: String,
        deviceName: String,
        publicKey: String,
    ): JsonObject {
        val body =
            buildJsonObject {
                put("ticket", ticket)
                put("teacher_id", teacherId)
                put("password", password)
                put("device_id", deviceId)
                put("device_name", deviceName)
                put("public_key", publicKey)
            }
        return post(baseUrl, "/api/v1/devices/enroll", body, token = null).jsonObject
    }

    fun directory(baseUrl: String, token: String): JsonObject =
        get(baseUrl, "/api/v1/me/directory", token).jsonObject

    fun handshake(
        baseUrl: String,
        deviceId: String,
        timestamp: Long,
        challengeResponse: String,
    ): JsonObject {
        val body =
            buildJsonObject {
                put("device_id", deviceId)
                put("timestamp", timestamp)
                put("challenge_response", challengeResponse)
            }
        return post(baseUrl, "/api/v1/sync/handshake", body, token = null).jsonObject
    }

    fun pushOperations(
        baseUrl: String,
        deviceId: String,
        operations: List<JsonObject>,
    ): JsonObject {
        val body =
            buildJsonObject {
                put("device_id", deviceId)
                put("operations", JsonArray(operations))
            }
        return post(baseUrl, "/api/v1/sync/push", body, token = null).jsonObject
    }

    fun pullOperations(
        baseUrl: String,
        deviceId: String,
        sinceClock: Long,
        limit: Int = 20,
    ): JsonObject {
        val body =
            buildJsonObject {
                put("device_id", deviceId)
                put("since_clock", sinceClock)
                put("limit", limit)
            }
        return post(baseUrl, "/api/v1/sync/pull", body, token = null).jsonObject
    }

    private fun get(baseUrl: String, path: String, token: String? = null): kotlinx.serialization.json.JsonElement {
        val builder = Request.Builder().url("${baseUrl.trimEnd('/')}$path")
        if (token != null) builder.header("Authorization", "Bearer $token")
        return parse(http.newCall(builder.build()).execute())
    }

    private fun post(
        baseUrl: String,
        path: String,
        body: JsonObject,
        token: String?,
    ): kotlinx.serialization.json.JsonElement {
        val builder =
            Request.Builder()
                .url("${baseUrl.trimEnd('/')}$path")
                .post(body.toString().toRequestBody(media))
        if (token != null) builder.header("Authorization", "Bearer $token")
        return parse(http.newCall(builder.build()).execute())
    }

    private fun parse(response: okhttp3.Response): kotlinx.serialization.json.JsonElement {
        response.use {
            val text = it.body?.string().orEmpty()
            val parsed =
                runCatching { json.parseToJsonElement(text) }.getOrElse {
                    if (response.isSuccessful) JsonObject(emptyMap()) else JsonObject(emptyMap())
                }
            if (!response.isSuccessful) {
                val error = parsed.jsonObjectOrNull()?.get("error")?.jsonObjectOrNull()
                throw SchoolException(
                    error?.get("code")?.jsonPrimitive?.contentOrNull ?: "HTTP_${response.code}",
                    error?.get("message")?.jsonPrimitive?.contentOrNull ?: "School computer refused the request.",
                )
            }
            return parsed
        }
    }
}

fun JsonObject.str(key: String): String {
    val value = this[key] ?: return ""
    if (value is JsonNull) return ""
    return (value as? JsonPrimitive)?.contentOrNull.orEmpty()
}

fun JsonObject.obj(key: String): JsonObject? = this[key]?.jsonObjectOrNull()

fun JsonObject.arr(key: String): JsonArray = this[key]?.jsonArray ?: JsonArray(emptyList())

fun kotlinx.serialization.json.JsonElement.jsonObjectOrNull(): JsonObject? = this as? JsonObject

fun JsonObject.toStringMap(): Map<String, String> =
    entries.associate { (key, value) ->
        key to ((value as? JsonPrimitive)?.contentOrNull ?: value.toString())
    }
