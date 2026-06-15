package com.dtu.componentscanner.data.pdf

import okhttp3.OkHttpClient
import okhttp3.Request
import java.io.IOException
import javax.inject.Inject

interface PdfDownloader {
    suspend fun download(url: String): ByteArray
}

class OkHttpPdfDownloader @Inject constructor(
    private val client: OkHttpClient,
) : PdfDownloader {
    override suspend fun download(url: String): ByteArray {
        val request = Request.Builder().url(url).build()
        client.newCall(request).execute().use { response ->
            if (!response.isSuccessful) throw IOException("PDF download failed: HTTP ${response.code}")
            return response.body?.bytes() ?: throw IOException("empty PDF body")
        }
    }
}
