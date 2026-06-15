package com.dtu.componentscanner.data.pdf

import java.io.File

class PdfCache(
    private val cacheDir: File,
    private val downloader: PdfDownloader,
) {
    /** Returns a local PDF file for the part, downloading + caching if not present. */
    suspend fun getOrDownload(partNumber: String, url: String): File {
        val file = File(cacheDir, fileName(partNumber))
        if (file.exists() && file.length() > 0) return file
        val bytes = downloader.download(url)
        if (!cacheDir.exists()) cacheDir.mkdirs()
        file.writeBytes(bytes)
        return file
    }

    private fun fileName(partNumber: String): String =
        partNumber.replace(Regex("[^A-Za-z0-9._-]"), "_") + ".pdf"
}
