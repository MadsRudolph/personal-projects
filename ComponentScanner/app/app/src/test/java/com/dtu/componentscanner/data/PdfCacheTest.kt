package com.dtu.componentscanner.data

import com.dtu.componentscanner.data.pdf.PdfCache
import com.dtu.componentscanner.data.pdf.PdfDownloader
import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertEquals
import org.junit.Assert.assertThrows
import org.junit.Assert.assertTrue
import org.junit.Rule
import org.junit.Test
import org.junit.rules.TemporaryFolder

class PdfCacheTest {
    @get:Rule val tmp = TemporaryFolder()

    // A minimal valid-looking PDF payload (starts with the "%PDF" magic bytes).
    private val pdfBytes = "%PDF-1.7\n...".toByteArray()

    private class FakeDownloader(val bytes: ByteArray) : PdfDownloader {
        var calls = 0
        override suspend fun download(url: String): ByteArray { calls++; return bytes }
    }

    @Test
    fun `getOrDownload writes the pdf to the cache dir`() = runTest {
        val downloader = FakeDownloader(pdfBytes)
        val cache = PdfCache(tmp.root, downloader)
        val file = cache.getOrDownload("LM358N", "https://x/lm358.pdf")
        assertTrue(file.exists())
        assertEquals(pdfBytes.size.toLong(), file.length())
    }

    @Test
    fun `second call reuses the cached file without re-downloading`() = runTest {
        val downloader = FakeDownloader(pdfBytes)
        val cache = PdfCache(tmp.root, downloader)
        cache.getOrDownload("LM358N", "https://x/lm358.pdf")
        cache.getOrDownload("LM358N", "https://x/lm358.pdf")
        assertEquals(1, downloader.calls)
    }

    @Test
    fun `getOrDownload throws when the content is not a PDF`() = runTest {
        val html = "<!DOCTYPE html><html>blocked</html>".toByteArray()
        val cache = PdfCache(tmp.root, FakeDownloader(html))
        assertThrows(java.io.IOException::class.java) {
            kotlinx.coroutines.runBlocking { cache.getOrDownload("L7805CV", "https://x/stub.pdf") }
        }
    }
}
