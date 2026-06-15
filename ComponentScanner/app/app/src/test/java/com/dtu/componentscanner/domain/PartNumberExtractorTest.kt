package com.dtu.componentscanner.domain

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class PartNumberExtractorTest {
    private val extractor = PartNumberExtractor()

    @Test
    fun `normalizes case and whitespace`() {
        assertEquals("LM358N", extractor.normalize("  lm358 n "))
    }

    @Test
    fun `extracts candidate tokens from multiline OCR text ranked best-first`() {
        val text = "TEXAS\nLM358N\n2143 G4"
        val candidates = extractor.extractCandidates(text)
        assertTrue(candidates.isNotEmpty())
        assertEquals("LM358N", candidates.first())
    }

    @Test
    fun `rejects pure words and date-code-only lines`() {
        val candidates = extractor.extractCandidates("HELLO WORLD\n2143")
        assertTrue(candidates.none { it == "HELLO" })
        assertTrue(candidates.none { it == "2143" })
    }

    @Test
    fun `prefers longer alphanumeric tokens as the primary candidate`() {
        val candidates = extractor.extractCandidates("U1 STM32F103C8T6 R4")
        assertEquals("STM32F103C8T6", candidates.first())
    }
}
