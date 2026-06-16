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
                    state.localPdfPath?.let { path ->
                        Button(onClick = { onOpenPdf(path) }) { Text("Open datasheet PDF") }
                        Spacer(Modifier.height(8.dp))
                    }
                    if (state.localPdfPath == null && !state.downloadFailed) {
                        // Still downloading the PDF for the in-app viewer.
                        Row(verticalAlignment = androidx.compose.ui.Alignment.CenterVertically) {
                            CircularProgressIndicator(Modifier.size(18.dp), strokeWidth = 2.dp)
                            Spacer(Modifier.width(8.dp))
                            Text("Preparing datasheet…")
                        }
                        Spacer(Modifier.height(8.dp))
                    }
                    if (state.downloadFailed) {
                        Text(
                            "This vendor blocks in-app download. Open it in your browser instead.",
                            style = MaterialTheme.typography.bodyMedium,
                        )
                        Spacer(Modifier.height(8.dp))
                    }
                    // Always available: open the datasheet URL in the browser, which
                    // handles vendors (e.g. ST) that block direct download.
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
