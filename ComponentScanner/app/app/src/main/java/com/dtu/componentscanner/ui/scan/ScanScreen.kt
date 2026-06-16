package com.dtu.componentscanner.ui.scan

import android.Manifest
import android.content.pm.PackageManager
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.camera.core.CameraSelector
import androidx.camera.core.ImageAnalysis
import androidx.camera.core.ImageCapture
import androidx.camera.core.ImageCaptureException
import androidx.camera.core.ImageProxy
import androidx.camera.core.Preview
import androidx.camera.lifecycle.ProcessCameraProvider
import androidx.camera.view.PreviewView
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.CameraAlt
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.compose.ui.viewinterop.AndroidView
import androidx.core.content.ContextCompat
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.LocalLifecycleOwner
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.dtu.componentscanner.ocr.OcrAnalyzer
import com.dtu.componentscanner.util.downscaleJpegBase64
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.util.concurrent.Executors

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ScanScreen(
    onPartChosen: (String) -> Unit,
    onOpenHistory: () -> Unit,
    viewModel: ScanViewModel = hiltViewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    val context = LocalContext.current
    val scope = rememberCoroutineScope()

    var hasCamera by remember {
        mutableStateOf(
            ContextCompat.checkSelfPermission(context, Manifest.permission.CAMERA) ==
                PackageManager.PERMISSION_GRANTED
        )
    }
    val permLauncher = rememberLauncherForActivityResult(
        ActivityResultContracts.RequestPermission()
    ) { granted -> hasCamera = granted }

    LaunchedEffect(Unit) { if (!hasCamera) permLauncher.launch(Manifest.permission.CAMERA) }

    // Hoisted ImageCapture instance — populated once CameraPreview binds the use case.
    var imageCapture by remember { mutableStateOf<ImageCapture?>(null) }

    // Manual part-number entry state.
    var showManualEntry by remember { mutableStateOf(false) }
    var manualText by remember { mutableStateOf("") }

    // Sheet visibility: shown when shelf mode has candidates.
    var showSheet by remember { mutableStateOf(false) }
    val sheetState = rememberModalBottomSheetState(skipPartiallyExpanded = true)

    LaunchedEffect(state.candidates, state.scanMode) {
        if (state.scanMode == ScanMode.SHELF && state.candidates.isNotEmpty()) {
            showSheet = true
        }
    }

    if (showSheet && state.scanMode == ScanMode.SHELF && state.candidates.isNotEmpty()) {
        ModalBottomSheet(
            onDismissRequest = { showSheet = false },
            sheetState = sheetState,
        ) {
            Text(
                text = "Identified components",
                style = MaterialTheme.typography.titleMedium,
                modifier = Modifier.padding(horizontal = 16.dp, vertical = 8.dp),
            )
            LazyColumn(
                modifier = Modifier
                    .fillMaxWidth()
                    .navigationBarsPadding(),
                contentPadding = PaddingValues(bottom = 16.dp),
            ) {
                items(state.candidates) { candidate ->
                    ListItem(
                        headlineContent = { Text(candidate.partNumber) },
                        supportingContent = {
                            Text(
                                "${candidate.manufacturer ?: ""}" +
                                    " — ${(candidate.confidence * 100).toInt()}%"
                            )
                        },
                        modifier = Modifier
                            .fillMaxWidth()
                            .clickable {
                                showSheet = false
                                onPartChosen(candidate.partNumber)
                            },
                    )
                    HorizontalDivider()
                }
            }
        }
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Scan component") },
                actions = { TextButton(onClick = onOpenHistory) { Text("History") } },
            )
        },
        floatingActionButton = {
            if (hasCamera) {
                FloatingActionButton(
                    onClick = {
                        val ic = imageCapture
                        if (ic != null && !state.isScanning) {
                            showSheet = false // reset before new capture
                            ic.takePicture(
                                ContextCompat.getMainExecutor(context),
                                object : ImageCapture.OnImageCapturedCallback() {
                                    override fun onCaptureSuccess(image: ImageProxy) {
                                        scope.launch {
                                            try {
                                                val base64 = withContext(Dispatchers.Default) {
                                                    val buffer = image.planes[0].buffer
                                                    val bytes = ByteArray(buffer.remaining())
                                                    buffer.get(bytes)
                                                    downscaleJpegBase64(bytes)
                                                }
                                                viewModel.deepScan(base64, "image/jpeg")
                                            } finally {
                                                image.close()
                                            }
                                        }
                                    }

                                    override fun onError(exc: ImageCaptureException) {
                                        viewModel.reportError(exc.message ?: "Capture failed")
                                    }
                                }
                            )
                        }
                    }
                ) {
                    Icon(Icons.Filled.CameraAlt, contentDescription = "Deep scan")
                }
            }
        },
    ) { padding ->
        Box(Modifier.fillMaxSize().padding(padding), contentAlignment = Alignment.Center) {
            if (hasCamera) {
                CameraPreview(
                    onOcrText = viewModel::onOcrText,
                    onImageCaptureReady = { imageCapture = it },
                )
            } else {
                Column(
                    horizontalAlignment = Alignment.CenterHorizontally,
                    verticalArrangement = Arrangement.spacedBy(12.dp),
                    modifier = Modifier.padding(24.dp),
                ) {
                    Text("Camera permission is required to scan components.")
                    Button(onClick = { permLauncher.launch(Manifest.permission.CAMERA) }) {
                        Text("Grant camera permission")
                    }
                    OutlinedButton(onClick = {
                        val intent = android.content.Intent(
                            android.provider.Settings.ACTION_APPLICATION_DETAILS_SETTINGS,
                            android.net.Uri.fromParts("package", context.packageName, null)
                        )
                        context.startActivity(intent)
                    }) {
                        Text("Open settings")
                    }
                }
            }

            Column(
                Modifier.align(Alignment.TopCenter).padding(top = 8.dp),
                horizontalAlignment = Alignment.CenterHorizontally,
            ) {
                // Mode toggle
                SingleChoiceSegmentedButtonRow {
                    SegmentedButton(
                        selected = state.scanMode == ScanMode.SINGLE,
                        onClick = { viewModel.setMode(ScanMode.SINGLE) },
                        shape = SegmentedButtonDefaults.itemShape(index = 0, count = 2),
                    ) { Text("One") }
                    SegmentedButton(
                        selected = state.scanMode == ScanMode.SHELF,
                        onClick = { viewModel.setMode(ScanMode.SHELF) },
                        shape = SegmentedButtonDefaults.itemShape(index = 1, count = 2),
                    ) { Text("Shelf") }
                }
            }

            Column(
                Modifier.align(Alignment.BottomCenter).padding(16.dp),
                horizontalAlignment = Alignment.CenterHorizontally,
            ) {
                // Manual part-number entry affordance (visible in both camera states).
                if (showManualEntry) {
                    OutlinedTextField(
                        value = manualText,
                        onValueChange = { manualText = it },
                        label = { Text("Part number") },
                        singleLine = true,
                        modifier = Modifier.fillMaxWidth(),
                    )
                    Spacer(Modifier.height(4.dp))
                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        Button(onClick = {
                            val normalized = viewModel.lookupManual(manualText)
                            if (normalized != null) {
                                onPartChosen(normalized)
                                manualText = ""
                                showManualEntry = false
                            }
                        }) { Text("Look up") }
                        OutlinedButton(onClick = {
                            showManualEntry = false
                            manualText = ""
                        }) { Text("Cancel") }
                    }
                } else {
                    TextButton(onClick = { showManualEntry = true }) { Text("Enter part #") }
                }

                if (state.scanMode == ScanMode.SINGLE) {
                    state.liveDetectedPart?.let { part ->
                        AssistChip(onClick = { onPartChosen(part) }, label = { Text("Detected: $part") })
                        Spacer(Modifier.height(8.dp))
                    }
                    state.candidates.firstOrNull()?.let { c ->
                        Button(onClick = { onPartChosen(c.partNumber) }) {
                            Text("Open ${c.partNumber}")
                        }
                    }
                }
                if (state.isScanning) {
                    Spacer(Modifier.height(8.dp))
                    CircularProgressIndicator()
                }
                state.error?.let { errorMsg ->
                    Spacer(Modifier.height(8.dp))
                    Row(
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.spacedBy(8.dp),
                    ) {
                        Text("Error: $errorMsg", modifier = Modifier.weight(1f))
                        TextButton(onClick = viewModel::clearError) { Text("Dismiss") }
                    }
                }
            }
        }
    }
}

@Composable
private fun CameraPreview(
    onOcrText: (String) -> Unit,
    onImageCaptureReady: (ImageCapture) -> Unit,
) {
    val context = LocalContext.current
    val lifecycleOwner = LocalLifecycleOwner.current
    val analysisExecutor = remember { Executors.newSingleThreadExecutor() }

    DisposableEffect(Unit) {
        onDispose { analysisExecutor.shutdown() }
    }

    AndroidView(
        modifier = Modifier.fillMaxSize(),
        factory = { ctx ->
            val previewView = PreviewView(ctx)
            val providerFuture = ProcessCameraProvider.getInstance(ctx)
            providerFuture.addListener({
                val provider = providerFuture.get()
                val preview = Preview.Builder().build().also {
                    it.setSurfaceProvider(previewView.surfaceProvider)
                }
                // Higher analysis resolution so on-device OCR can read small chip
                // markings (the default ~640x480 is too low for tiny text).
                val resolutionSelector = androidx.camera.core.resolutionselector.ResolutionSelector.Builder()
                    .setResolutionStrategy(
                        androidx.camera.core.resolutionselector.ResolutionStrategy(
                            android.util.Size(1920, 1080),
                            androidx.camera.core.resolutionselector.ResolutionStrategy.FALLBACK_RULE_CLOSEST_HIGHER_THEN_LOWER,
                        )
                    )
                    .build()
                val analysis = ImageAnalysis.Builder()
                    .setResolutionSelector(resolutionSelector)
                    .setBackpressureStrategy(ImageAnalysis.STRATEGY_KEEP_ONLY_LATEST)
                    .build()
                    .also { it.setAnalyzer(analysisExecutor, OcrAnalyzer(onOcrText)) }
                val capture = ImageCapture.Builder()
                    .setCaptureMode(ImageCapture.CAPTURE_MODE_MINIMIZE_LATENCY)
                    .build()
                provider.unbindAll()
                provider.bindToLifecycle(
                    lifecycleOwner,
                    CameraSelector.DEFAULT_BACK_CAMERA,
                    preview,
                    analysis,
                    capture,
                )
                onImageCaptureReady(capture)
            }, ContextCompat.getMainExecutor(ctx))
            previewView
        },
    )
}
