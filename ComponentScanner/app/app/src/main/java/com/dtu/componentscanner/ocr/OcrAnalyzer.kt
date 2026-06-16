package com.dtu.componentscanner.ocr

import android.annotation.SuppressLint
import androidx.camera.core.ImageAnalysis
import androidx.camera.core.ImageProxy
import com.google.mlkit.vision.common.InputImage
import com.google.mlkit.vision.text.TextRecognition
import com.google.mlkit.vision.text.latin.TextRecognizerOptions

/** Runs on-device OCR a few times per second and reports recognized text. */
class OcrAnalyzer(
    private val onText: (String) -> Unit,
) : ImageAnalysis.Analyzer {

    private val recognizer = TextRecognition.getClient(TextRecognizerOptions.DEFAULT_OPTIONS)
    private var lastAnalyzedMs = 0L

    @SuppressLint("UnsafeOptInUsageError")
    override fun analyze(imageProxy: ImageProxy) {
        val now = System.currentTimeMillis()
        if (now - lastAnalyzedMs < MIN_INTERVAL_MS) {
            imageProxy.close()
            return
        }
        lastAnalyzedMs = now
        val mediaImage = imageProxy.image
        if (mediaImage == null) {
            imageProxy.close()
            return
        }
        val input = InputImage.fromMediaImage(mediaImage, imageProxy.imageInfo.rotationDegrees)
        recognizer.process(input)
            .addOnSuccessListener { result -> if (result.text.isNotBlank()) onText(result.text) }
            .addOnCompleteListener { imageProxy.close() }
    }

    private companion object {
        const val MIN_INTERVAL_MS = 350L
    }
}
