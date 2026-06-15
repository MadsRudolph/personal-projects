package com.dtu.componentscanner.ui.result

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.dtu.componentscanner.data.pdf.PdfCache
import com.dtu.componentscanner.data.repository.ComponentRepository
import com.dtu.componentscanner.data.repository.HistoryRepository
import com.dtu.componentscanner.domain.model.Datasheet
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import javax.inject.Inject

data class ResultUiState(
    val isLoading: Boolean = false,
    val datasheet: Datasheet? = null,
    val localPdfPath: String? = null,
    val notFound: Boolean = false,
    val error: String? = null,
)

@HiltViewModel
class ResultViewModel @Inject constructor(
    private val componentRepository: ComponentRepository,
    private val historyRepository: HistoryRepository,
    private val pdfCache: PdfCache,
    private val clock: () -> Long,
) : ViewModel() {

    private val _state = MutableStateFlow(ResultUiState())
    val state: StateFlow<ResultUiState> = _state.asStateFlow()

    fun load(partNumber: String) {
        _state.update { it.copy(isLoading = true, notFound = false, error = null) }
        viewModelScope.launch {
            try {
                val sheet = componentRepository.datasheet(partNumber)
                if (sheet == null) {
                    _state.update { it.copy(isLoading = false, notFound = true) }
                    return@launch
                }
                historyRepository.record(sheet.partNumber, sheet.manufacturer, sheet.datasheetUrl, clock())
                val file = pdfCache.getOrDownload(sheet.partNumber, sheet.datasheetUrl)
                _state.update {
                    it.copy(isLoading = false, datasheet = sheet, localPdfPath = file.absolutePath)
                }
            } catch (e: Exception) {
                _state.update { it.copy(isLoading = false, error = e.message ?: "failed to load datasheet") }
            }
        }
    }
}
