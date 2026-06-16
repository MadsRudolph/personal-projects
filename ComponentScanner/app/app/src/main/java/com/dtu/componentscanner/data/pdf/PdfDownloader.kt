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
        val request = Request.Builder()
            .url(url)
            // Some vendor sites (e.g. st.com) reject non-browser clients.
            .header(
                "User-Agent",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 " +
                    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            )
            .header("Accept", "application/pdf,*/*")
            .build()
        client.newCall(request).execute().use { response ->
            if (!response.isSuccessful) throw IOException("PDF download failed: HTTP ${response.code}")
            return response.body?.bytes() ?: throw IOException("empty PDF body")
        }
    }
}
