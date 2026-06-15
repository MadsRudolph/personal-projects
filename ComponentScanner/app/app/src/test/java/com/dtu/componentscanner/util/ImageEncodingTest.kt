package com.dtu.componentscanner.util

import org.junit.Assert.assertArrayEquals
import org.junit.Assert.assertEquals
import org.junit.Test
import java.util.Base64

class ImageEncodingTest {

    @Test
    fun `encodeBase64 round-trips arbitrary bytes`() {
        val original = byteArrayOf(0x00, 0x01, 0x7F, -1, 0x42, 0x00, 0x10)
        val encoded = encodeBase64(original)
        val decoded = Base64.getDecoder().decode(encoded)
        assertArrayEquals("Decoded bytes must match original", original, decoded)
    }

    @Test
    fun `encodeBase64 empty array produces empty string`() {
        val encoded = encodeBase64(byteArrayOf())
        assertEquals("", encoded)
    }

    @Test
    fun `encodeBase64 known value matches standard Base64`() {
        // "Man" → standard Base64 is "TWFu"
        val bytes = "Man".toByteArray(Charsets.UTF_8)
        assertEquals("TWFu", encodeBase64(bytes))
    }

    @Test
    fun `encodeBase64 output is decodable by java Base64 decoder`() {
        val data = "Hello, Component Scanner!".toByteArray(Charsets.UTF_8)
        val encoded = encodeBase64(data)
        val decodedString = String(Base64.getDecoder().decode(encoded), Charsets.UTF_8)
        assertEquals("Hello, Component Scanner!", decodedString)
    }
}
