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
    /** True when the PDF could not be downloaded for the in-app viewer (e.g. the
     *  vendor blocks direct download). The datasheet URL is still available to
     *  open in the browser. */
    val downloadFailed: Boolean = false,
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
        _state.update {
            it.copy(
                isLoading = true,
                notFound = false,
                error = null,
                datasheet = null,
                localPdfPath = null,
                downloadFailed = false,
            )
        }
        viewModelScope.launch {
            try {
                // Cache-first: if we've already resolved this part (e.g. opened
                // before, or prefetched on detection), skip the backend entirely.
                val cached = historyRepository.find(partNumber)
                if (cached != null) {
                    val ds = Datasheet(
                        cached.partNumber, cached.manufacturer, cached.datasheetUrl, emptyList(),
                    )
                    _state.update { it.copy(isLoading = false, datasheet = ds) }
                    serveOrDownload(ds)
                    return@launch
                }

                val sheet = componentRepository.datasheet(partNumber)
                if (sheet == null) {
                    _state.update { it.copy(isLoading = false, notFound = true) }
                    return@launch
                }
                historyRepository.record(sheet.partNumber, sheet.manufacturer, sheet.datasheetUrl, clock())
                // Surface the datasheet (and its URL) immediately so the viewer/
                // browser fallback works even if the download below is blocked.
                _state.update { it.copy(isLoading = false, datasheet = sheet) }
                serveOrDownload(sheet)
            } catch (e: Exception) {
                _state.update { it.copy(isLoading = false, error = e.message ?: "failed to load datasheet") }
            }
        }
    }

    /** Use the already-cached PDF instantly, otherwise download it (failure is
     *  non-fatal — the screen falls back to the WebView/browser viewer). */
    private suspend fun serveOrDownload(sheet: Datasheet) {
        val cachedFile = pdfCache.cachedFile(sheet.partNumber)
        if (cachedFile != null) {
            _state.update { it.copy(localPdfPath = cachedFile.absolutePath) }
            return
        }
        try {
            val file = pdfCache.getOrDownload(sheet.partNumber, sheet.datasheetUrl)
            _state.update { it.copy(localPdfPath = file.absolutePath) }
        } catch (e: Exception) {
            _state.update { it.copy(downloadFailed = true) }
        }
    }
}
