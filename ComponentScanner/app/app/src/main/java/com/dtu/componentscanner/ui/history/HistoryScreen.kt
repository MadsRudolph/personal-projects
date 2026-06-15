package com.dtu.componentscanner.ui.history

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun HistoryScreen(
    onOpenPart: (String) -> Unit,
    onBack: () -> Unit,
    viewModel: HistoryViewModel = hiltViewModel(),
) {
    val items by viewModel.state.collectAsStateWithLifecycle()
    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Scan history") },
                navigationIcon = { TextButton(onClick = onBack) { Text("Back") } },
            )
        }
    ) { padding ->
        if (items.isEmpty()) {
            Box(Modifier.fillMaxSize().padding(padding)) { Text("No scans yet.", Modifier.padding(16.dp)) }
        } else {
            LazyColumn(Modifier.fillMaxSize().padding(padding)) {
                items(items, key = { it.partNumber }) { item ->
                    ListItem(
                        headlineContent = { Text(item.partNumber) },
                        supportingContent = { Text(item.manufacturer) },
                        trailingContent = {
                            TextButton(onClick = { viewModel.delete(item.partNumber) }) { Text("Delete") }
                        },
                        modifier = Modifier.clickable { onOpenPart(item.partNumber) },
                    )
                    HorizontalDivider()
                }
            }
        }
    }
}
