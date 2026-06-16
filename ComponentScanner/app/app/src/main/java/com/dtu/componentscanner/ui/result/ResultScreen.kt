package com.dtu.componentscanner.ui.result

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import android.content.Intent
import android.net.Uri
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ResultScreen(
    partNumber: String,
    onOpenPdf: (String) -> Unit,
    onOpenPdfWeb: (String) -> Unit,
    onBack: () -> Unit,
    viewModel: ResultViewModel = hiltViewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    val context = LocalContext.current
    LaunchedEffect(partNumber) { viewModel.load(partNumber) }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text(partNumber) },
                navigationIcon = { TextButton(onClick = onBack) { Text("Back") } },
            )
        }
    ) { padding ->
        Column(Modifier.fillMaxSize().padding(padding).padding(16.dp).verticalScroll(rememberScrollState())) {
            when {
                state.isLoading -> CircularProgressIndicator()
                state.notFound -> Text("No datasheet found for $partNumber.")
                state.error != null -> {
                    Text("Error: ${state.error}")
                    Spacer(Modifier.height(12.dp))
                    Button(onClick = { viewModel.load(partNumber) }) { Text("Retry") }
                }
                state.datasheet != null -> {
                    val ds = state.datasheet!!
                    Text("Manufacturer: ${ds.manufacturer}", style = MaterialTheme.typography.titleMedium)
                    Spacer(Modifier.height(12.dp))
                    ds.keySpecs.forEach { spec ->
                        Row(Modifier.fillMaxWidth().padding(vertical = 4.dp)) {
                            Text(spec.name, Modifier.weight(1f))
                            Text(spec.value, Modifier.weight(1f))
                        }
                    }
                    Spacer(Modifier.height(16.dp))
                    when {
                        // Downloadable PDF (e.g. TI) → fast native in-app renderer.
                        state.localPdfPath != null -> {
                            Button(onClick = { onOpenPdf(state.localPdfPath!!) }) {
                                Text("Open datasheet")
                            }
                        }
                        // Vendor blocks direct download (e.g. ST/Mouser) → render
                        // in-app via the WebView (Google Docs) viewer.
                        state.downloadFailed -> {
                            Button(onClick = { onOpenPdfWeb(ds.datasheetUrl) }) {
                                Text("Open datasheet")
                            }
                        }
                        // Still downloading.
                        else -> {
                            Row(verticalAlignment = androidx.compose.ui.Alignment.CenterVertically) {
                                CircularProgressIndicator(Modifier.size(18.dp), strokeWidth = 2.dp)
                                Spacer(Modifier.width(8.dp))
                                Text("Preparing datasheet…")
                            }
                        }
                    }
                    Spacer(Modifier.height(8.dp))
                    // Last-resort fallback if the in-app viewer can't render it.
                    OutlinedButton(onClick = {
                        runCatching {
                            context.startActivity(
                                Intent(Intent.ACTION_VIEW, Uri.parse(ds.datasheetUrl))
                            )
                        }
                    }) { Text("Open in browser") }
                }
            }
        }
    }
}
