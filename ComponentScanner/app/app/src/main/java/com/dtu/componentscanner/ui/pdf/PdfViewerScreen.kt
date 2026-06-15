package com.dtu.componentscanner.ui.pdf

import android.graphics.Bitmap
import android.graphics.Color
import android.graphics.pdf.PdfRenderer
import android.os.ParcelFileDescriptor
import androidx.compose.foundation.Image
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.unit.dp
import java.io.File

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun PdfViewerScreen(filePath: String, onBack: () -> Unit) {
    val pages by produceState<List<Bitmap>>(initialValue = emptyList(), filePath) {
        value = renderPdf(File(filePath))
    }
    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Datasheet") },
                navigationIcon = { TextButton(onClick = onBack) { Text("Back") } },
            )
        }
    ) { padding ->
        if (pages.isEmpty()) {
            Box(Modifier.fillMaxSize().padding(padding)) { CircularProgressIndicator() }
        } else {
            LazyColumn(Modifier.fillMaxSize().padding(padding)) {
                items(pages) { bmp ->
                    Image(
                        bitmap = bmp.asImageBitmap(),
                        contentDescription = null,
                        modifier = Modifier.fillMaxWidth().padding(4.dp),
                        contentScale = ContentScale.FillWidth,
                    )
                }
            }
        }
    }
}

private fun renderPdf(file: File): List<Bitmap> {
    if (!file.exists()) return emptyList()
    val descriptor = ParcelFileDescriptor.open(file, ParcelFileDescriptor.MODE_READ_ONLY)
    val renderer = PdfRenderer(descriptor)
    val bitmaps = ArrayList<Bitmap>(renderer.pageCount)
    for (i in 0 until renderer.pageCount) {
        val page = renderer.openPage(i)
        val scale = 2
        val bmp = Bitmap.createBitmap(page.width * scale, page.height * scale, Bitmap.Config.ARGB_8888)
        bmp.eraseColor(Color.WHITE)
        page.render(bmp, null, null, PdfRenderer.Page.RENDER_MODE_FOR_DISPLAY)
        bitmaps.add(bmp)
        page.close()
    }
    renderer.close()
    descriptor.close()
    return bitmaps
}
