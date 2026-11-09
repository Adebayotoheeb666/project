package ng.lsia.teacher.data.crypto

import android.content.Context
import android.util.Base64
import androidx.security.crypto.EncryptedSharedPreferences
import androidx.security.crypto.MasterKey
import org.bouncycastle.crypto.generators.Ed25519KeyPairGenerator
import org.bouncycastle.crypto.params.Ed25519KeyGenerationParameters
import org.bouncycastle.crypto.params.Ed25519PrivateKeyParameters
import org.bouncycastle.crypto.params.Ed25519PublicKeyParameters
import org.bouncycastle.crypto.signers.Ed25519Signer
import java.security.SecureRandom

class DeviceKeys(context: Context) {
    private val prefs =
        EncryptedSharedPreferences.create(
            context,
            "lsia_secure",
            MasterKey.Builder(context).setKeyScheme(MasterKey.KeyScheme.AES256_GCM).build(),
            EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
            EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM,
        )

    fun publicKeyB64(): String {
        val existing = prefs.getString(PUBLIC, null)
        if (existing != null) return existing
        generate()
        return prefs.getString(PUBLIC, "")!!
    }

    fun deviceId(): String {
        val existing = prefs.getString(DEVICE_ID, null)
        if (existing != null) return existing
        val id = "dev_" + java.util.UUID.randomUUID().toString().replace("-", "").take(16)
        prefs.edit().putString(DEVICE_ID, id).apply()
        return id
    }

    fun sign(message: ByteArray): String {
        val seed = seed()
        val privateKey = Ed25519PrivateKeyParameters(seed)
        val signer = Ed25519Signer()
        signer.init(true, privateKey)
        signer.update(message, 0, message.size)
        return Base64.encodeToString(signer.generateSignature(), Base64.NO_WRAP)
    }

    fun pinHash(): String? = prefs.getString(PIN, null)

    fun setPin(pin: String) {
        prefs.edit().putString(PIN, hashPin(pin)).apply()
    }

    fun unlock(pin: String): Boolean = pinHash() == hashPin(pin)

    fun session(key: String, value: String?) {
        prefs.edit().apply {
            if (value == null) remove(key) else putString(key, value)
        }.apply()
    }

    fun session(key: String): String? = prefs.getString(key, null)

    private fun generate() {
        val generator = Ed25519KeyPairGenerator()
        generator.init(Ed25519KeyGenerationParameters(SecureRandom()))
        val pair = generator.generateKeyPair()
        val privateKey = pair.private as Ed25519PrivateKeyParameters
        val publicKey = pair.public as Ed25519PublicKeyParameters
        prefs.edit()
            .putString(SEED, Base64.encodeToString(privateKey.encoded, Base64.NO_WRAP))
            .putString(PUBLIC, Base64.encodeToString(publicKey.encoded, Base64.NO_WRAP))
            .apply()
    }

    private fun seed(): ByteArray {
        val stored = prefs.getString(SEED, null)
        if (stored == null) {
            generate()
            return Base64.decode(prefs.getString(SEED, "")!!, Base64.NO_WRAP)
        }
        return Base64.decode(stored, Base64.NO_WRAP)
    }

    private fun hashPin(pin: String): String {
        val digest = java.security.MessageDigest.getInstance("SHA-256")
        val salt = deviceId()
        return Base64.encodeToString(digest.digest("$salt:$pin".toByteArray()), Base64.NO_WRAP)
    }

    companion object {
        private const val SEED = "ed25519_seed"
        private const val PUBLIC = "ed25519_public"
        private const val DEVICE_ID = "device_id"
        private const val PIN = "pin_hash"
    }
}
