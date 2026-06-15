package com.dtu.componentscanner.util

import android.graphics.Bitmap
import android.graphics.BitmapFactory
import java.io.ByteArrayOutputStream
import java.util.Base64

/**
 * Encode [bytes] as a standard Base64 string (no line breaks, with padding).
 * Uses java.util.Base64 so this function is testable on the JVM without Android.
 */
fun encodeBase64(bytes: ByteArray): String =
    Base64.getEncoder().encodeToString(bytes)

/**
 * Downscale [jpegBytes] so its longest edge is ≤ [maxDim], re-compress to JPEG at
 * [quality] %, and return the result as a Base64 string.
 * Requires Android (BitmapFactory / Bitmap).
 */
fun downscaleJpegBase64(
    jpegBytes: ByteArray,
    maxDim: Int = 1280,
    quality: Int = 85,
): String {
    val original = BitmapFactory.decodeByteArray(jpegBytes, 0, jpegBytes.size)
        ?: return encodeBase64(jpegBytes)   // fallback: encode as-is

    val (w, h) = original.width to original.height
    val scaled: Bitmap = if (w <= maxDim && h <= maxDim) {
        original
    } else {
        val scale = maxDim.toFloat() / maxOf(w, h)
        Bitmap.createScaledBitmap(
            original,
            (w * scale).toInt().coerceAtLeast(1),
            (h * scale).toInt().coerceAtLeast(1),
            true,
        )
    }

    val out = ByteArrayOutputStream()
    scaled.compress(Bitmap.CompressFormat.JPEG, quality, out)
    if (scaled !== original) scaled.recycle()
    original.recycle()
    return encodeBase64(out.toByteArray())
}
