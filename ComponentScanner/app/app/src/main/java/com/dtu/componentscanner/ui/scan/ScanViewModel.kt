package com.dtu.componentscanner.ui.scan

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.dtu.componentscanner.data.repository.ComponentRepository
import com.dtu.componentscanner.data.repository.IdentifyOutcome
import com.dtu.componentscanner.domain.PartNumberExtractor
import com.dtu.componentscanner.domain.model.Candidate
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import javax.inject.Inject

enum class ScanMode { SINGLE, SHELF }

data class ScanUiState(
    val liveDetectedPart: String? = null,
    val candidates: List<Candidate> = emptyList(),
    val isScanning: Boolean = false,
    val error: String? = null,
    val scanMode: ScanMode = ScanMode.SINGLE,
)

@HiltViewModel
class ScanViewModel @Inject constructor(
    private val repository: ComponentRepository,
    private val extractor: PartNumberExtractor,
) : ViewModel() {

    private val _state = MutableStateFlow(ScanUiState())
    val state: StateFlow<ScanUiState> = _state.asStateFlow()

    /** Called continuously with on-device OCR text from the camera frame analyzer. */
    fun onOcrText(text: String) {
        val best = extractor.extractCandidates(text).firstOrNull()
        _state.update { it.copy(liveDetectedPart = best) }
    }

    /** Switch between single-component and shelf (multi-component) scan modes. */
    fun setMode(mode: ScanMode) {
        _state.update { it.copy(scanMode = mode, candidates = emptyList()) }
    }

    /** Cloud fallback: send a captured still to the backend for a high-quality read. */
    fun deepScan(imageBase64: String, mimeType: String) {
        val mode = if (_state.value.scanMode == ScanMode.SHELF) "shelf" else "single"
        _state.update { it.copy(isScanning = true, error = null) }
        viewModelScope.launch {
            when (val outcome = repository.identify(imageBase64, mimeType, mode)) {
                is IdentifyOutcome.Success ->
                    _state.update { it.copy(isScanning = false, candidates = outcome.candidates) }
                is IdentifyOutcome.Error ->
                    _state.update { it.copy(isScanning = false, error = outcome.message) }
            }
        }
    }

    /**
     * Normalize a manually-entered part number.
     * Returns the normalized string when [text] is non-blank, null otherwise.
     */
    fun lookupManual(text: String): String? {
        val normalized = extractor.normalize(text)
        return if (normalized.isBlank()) null else normalized
    }

    fun clearError() = _state.update { it.copy(error = null) }

    fun reportError(message: String) = _state.update { it.copy(isScanning = false, error = message) }
}
