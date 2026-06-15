package com.dtu.componentscanner.ui.result

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
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
                state.error != null -> Text("Error: ${state.error}")
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
                    }
                }
            }
        }
    }
}
