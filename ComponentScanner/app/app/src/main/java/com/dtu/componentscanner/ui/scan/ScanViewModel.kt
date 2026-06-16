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

    // Rolling window of recent per-frame readings, used to stabilize the live
    // detection so it locks onto a confident part instead of flickering through
    // everything the camera momentarily reads.
    private val recentReadings = ArrayDeque<String>()

    /** Called continuously with on-device OCR text from the camera frame analyzer. */
    fun onOcrText(text: String) {
        val best = extractor.extractCandidates(text).firstOrNull() ?: return
        recentReadings.addLast(best)
        while (recentReadings.size > WINDOW_SIZE) recentReadings.removeFirst()

        // Only surface a part once it dominates the recent window — and keep it
        // shown until a different candidate becomes the new clear winner.
        val winner = recentReadings.groupingBy { it }.eachCount().maxByOrNull { it.value }
        if (winner != null && winner.value >= STABLE_THRESHOLD) {
            if (_state.value.liveDetectedPart != winner.key) {
                _state.update { it.copy(liveDetectedPart = winner.key) }
            }
        }
    }

    /** Switch between single-component and shelf (multi-component) scan modes. */
    fun setMode(mode: ScanMode) {
        recentReadings.clear()
        _state.update {
            it.copy(scanMode = mode, candidates = emptyList(), liveDetectedPart = null)
        }
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

    private companion object {
        const val WINDOW_SIZE = 12
        const val STABLE_THRESHOLD = 4
    }
}
