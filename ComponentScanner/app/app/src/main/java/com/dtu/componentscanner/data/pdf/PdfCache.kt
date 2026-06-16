package com.dtu.componentscanner.data.pdf

import java.io.File
import java.io.IOException

class PdfCache(
    private val cacheDir: File,
    private val downloader: PdfDownloader,
) {
    /** Returns a local PDF file for the part, downloading + caching if not present.
     *  Throws if the downloaded content isn't actually a PDF (e.g. a vendor served
     *  an HTML anti-bot page) so the caller can fall back to opening in a browser. */
    suspend fun getOrDownload(partNumber: String, url: String): File {
        val file = File(cacheDir, fileName(partNumber))
        if (file.exists() && file.length() > 0) return file
        val bytes = downloader.download(url)
        if (!isPdf(bytes)) throw IOException("Downloaded content is not a PDF")
        if (!cacheDir.exists()) cacheDir.mkdirs()
        file.writeBytes(bytes)
        return file
    }

    /** PDFs start with the magic bytes "%PDF". */
    private fun isPdf(bytes: ByteArray): Boolean =
        bytes.size >= 4 &&
            bytes[0] == '%'.code.toByte() &&
            bytes[1] == 'P'.code.toByte() &&
            bytes[2] == 'D'.code.toByte() &&
            bytes[3] == 'F'.code.toByte()

    private fun fileName(partNumber: String): String =
        partNumber.replace(Regex("[^A-Za-z0-9._-]"), "_") + ".pdf"
}
