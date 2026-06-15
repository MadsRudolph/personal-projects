package com.dtu.componentscanner.ui.pdf

import android.graphics.Bitmap
import android.graphics.pdf.PdfRenderer
import android.os.ParcelFileDescriptor
import androidx.compose.foundation.Image
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.unit.dp
import java.io.File
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock

// ---------------------------------------------------------------------------
// PdfDocument — opens renderer once, renders pages lazily on Dispatchers.IO,
// guards against PdfRenderer's non-thread-safety with a Mutex.
// ---------------------------------------------------------------------------

private class PdfDocument(file: File) {
    private val pfd: ParcelFileDescriptor =
        ParcelFileDescriptor.open(file, ParcelFileDescriptor.MODE_READ_ONLY)
    private val renderer: PdfRenderer = PdfRenderer(pfd)
    private val mutex = Mutex()

    val pageCount: Int get() = renderer.pageCount

    /** Renders [index] scaled so its width == [targetWidthPx]. Returns a white ARGB_8888 bitmap. */
    suspend fun render(index: Int, targetWidthPx: Int): Bitmap = mutex.withLock {
        withContext(Dispatchers.IO) {
            val page = renderer.openPage(index)
            try {
                val scale = targetWidthPx.toFloat() / page.width
                val w = targetWidthPx
                val h = (page.height * scale).toInt().coerceAtLeast(1)
                val bmp = Bitmap.createBitmap(w, h, Bitmap.Config.ARGB_8888)
                bmp.eraseColor(android.graphics.Color.WHITE)
                page.render(bmp, null, null, PdfRenderer.Page.RENDER_MODE_FOR_DISPLAY)
                bmp
            } finally {
                page.close()
            }
        }
    }

    /** Closes renderer and file descriptor, swallowing any exception from each. */
    fun close() {
        runCatching { renderer.close() }
        runCatching { pfd.close() }
    }
}

// ---------------------------------------------------------------------------
// PdfViewerScreen — lazy, leak-free composable
// ---------------------------------------------------------------------------

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun PdfViewerScreen(filePath: String, onBack: () -> Unit) {

    // Open the document once per filePath; null means construction failed (corrupt / missing).
    val pdf: PdfDocument? = remember(filePath) {
        runCatching { PdfDocument(File(filePath)) }.getOrNull()
    }

    // Close the document when the composable leaves composition or filePath changes.
    DisposableEffect(filePath) {
        onDispose { pdf?.close() }
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Datasheet") },
                navigationIcon = { TextButton(onClick = onBack) { Text("Back") } },
            )
        }
    ) { padding ->
        if (pdf == null) {
            // Construction failed — show a friendly error instead of crashing.
            Box(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(padding),
                contentAlignment = Alignment.Center,
            ) {
                Text("Could not open datasheet")
            }
        } else {
            LazyColumn(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(padding),
            ) {
                itemsIndexed(List(pdf.pageCount) { it }) { _, index ->
                    PdfPageItem(pdf = pdf, index = index)
                }
            }
        }
    }
}

// ---------------------------------------------------------------------------
// Single lazy page item
// ---------------------------------------------------------------------------

@Composable
private fun PdfPageItem(pdf: PdfDocument, index: Int) {
    // Measure available width in pixels so we can pass it to the renderer.
    BoxWithConstraints(modifier = Modifier.fillMaxWidth()) {
        val widthPx = constraints.maxWidth

        // Produce the bitmap in a coroutine; re-launch if index or widthPx changes.
        val bitmap: Bitmap? by produceState<Bitmap?>(
            initialValue = null,
            key1 = index,
            key2 = widthPx,
        ) {
            value = null // reset on key change
            if (widthPx > 0) {
                value = pdf.render(index, widthPx)
            }
        }

        if (bitmap == null) {
            // Placeholder with a spinner until the page is rendered.
            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .height(280.dp),
                contentAlignment = Alignment.Center,
            ) {
                CircularProgressIndicator()
            }
        } else {
            Image(
                bitmap = bitmap!!.asImageBitmap(),
                contentDescription = "Page ${index + 1}",
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(vertical = 4.dp),
                contentScale = ContentScale.FillWidth,
            )
        }
    }
}
