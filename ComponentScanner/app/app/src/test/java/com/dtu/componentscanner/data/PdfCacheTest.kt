package com.dtu.componentscanner.data

import com.dtu.componentscanner.data.pdf.PdfCache
import com.dtu.componentscanner.data.pdf.PdfDownloader
import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Rule
import org.junit.Test
import org.junit.rules.TemporaryFolder

class PdfCacheTest {
    @get:Rule val tmp = TemporaryFolder()

    private class FakeDownloader(val bytes: ByteArray = byteArrayOf(1, 2, 3)) : PdfDownloader {
        var calls = 0
        override suspend fun download(url: String): ByteArray { calls++; return bytes }
    }

    @Test
    fun `getOrDownload writes the pdf to the cache dir`() = runTest {
        val downloader = FakeDownloader()
        val cache = PdfCache(tmp.root, downloader)
        val file = cache.getOrDownload("LM358N", "https://x/lm358.pdf")
        assertTrue(file.exists())
        assertEquals(3, file.length())
    }

    @Test
    fun `second call reuses the cached file without re-downloading`() = runTest {
        val downloader = FakeDownloader()
        val cache = PdfCache(tmp.root, downloader)
        cache.getOrDownload("LM358N", "https://x/lm358.pdf")
        cache.getOrDownload("LM358N", "https://x/lm358.pdf")
        assertEquals(1, downloader.calls)
    }
}
