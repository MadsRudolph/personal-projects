package com.dtu.componentscanner.ui.scan

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.dtu.componentscanner.data.repository.ComponentRepository
import com.dtu.componentscanner.data.repository.IdentifyOutcome
import com.dtu.componentscanner.domain.PartNumberExtractor
import com.dtu.componentscanner.domain.model.Candidate
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class ScanUiState(
    val liveDetectedPart: String? = null,
    val candidates: List<Candidate> = emptyList(),
    val isScanning: Boolean = false,
    val error: String? = null,
)

class ScanViewModel(
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

    /** Cloud fallback: send a captured still to the backend for a high-quality read. */
    fun deepScan(imageBase64: String, mimeType: String) {
        _state.update { it.copy(isScanning = true, error = null) }
        viewModelScope.launch {
            when (val outcome = repository.identify(imageBase64, mimeType, "single")) {
                is IdentifyOutcome.Success ->
                    _state.update { it.copy(isScanning = false, candidates = outcome.candidates) }
                is IdentifyOutcome.Error ->
                    _state.update { it.copy(isScanning = false, error = outcome.message) }
            }
        }
    }

    fun clearError() = _state.update { it.copy(error = null) }
}
