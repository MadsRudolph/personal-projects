package com.dtu.componentscanner.domain

import javax.inject.Inject

/** Extracts and normalizes electronic part numbers from raw OCR text. Pure logic. */
class PartNumberExtractor @Inject constructor() {

    /** Canonicalize a single token: collapse whitespace, uppercase. */
    fun normalize(raw: String): String =
        raw.trim().replace(WHITESPACE, "").uppercase()

    /**
     * Return plausible part-number candidates from multi-line OCR text, best first.
     * Heuristic ranking: must contain a letter AND a digit, length 3..24; longer
     * tokens (more specific markings) rank higher.
     */
    fun extractCandidates(text: String): List<String> =
        text.split(WHITESPACE)
            .map { it.trim() }
            .filter { it.isNotEmpty() }
            .map { normalize(it) }
            .filter { looksLikePartNumber(it) }
            .distinct()
            .sortedByDescending { it.length }

    private fun looksLikePartNumber(token: String): Boolean {
        if (token.length !in 3..24) return false
        val hasLetter = token.any { it.isLetter() }
        val hasDigit = token.any { it.isDigit() }
        return hasLetter && hasDigit
    }

    private companion object {
        val WHITESPACE = Regex("\\s+")
    }
}
