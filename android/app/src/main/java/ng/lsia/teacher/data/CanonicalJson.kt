package ng.lsia.teacher.data

object CanonicalJson {
    fun stringify(value: Any?): String =
        when (value) {
            null -> "null"
            is Boolean -> if (value) "true" else "false"
            is Int, is Long, is Short, is Byte -> value.toString()
            is Double, is Float -> {
                val number = (value as Number).toDouble()
                if (number % 1.0 == 0.0) number.toLong().toString() else number.toString()
            }
            is String -> quote(value)
            is Map<*, *> -> {
                val entries =
                    value.entries
                        .map { it.key.toString() to it.value }
                        .sortedBy { it.first }
                entries.joinToString(",", "{", "}") { (key, item) ->
                    "${quote(key)}:${stringify(item)}"
                }
            }
            is Iterable<*> -> value.joinToString(",", "[", "]") { stringify(it) }
            else -> quote(value.toString())
        }

    private fun quote(raw: String): String {
        val escaped =
            raw
                .replace("\\", "\\\\")
                .replace("\"", "\\\"")
                .replace("\n", "\\n")
                .replace("\r", "\\r")
                .replace("\t", "\\t")
        return "\"$escaped\""
    }
}
