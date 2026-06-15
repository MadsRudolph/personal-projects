package com.dtu.componentscanner.ui.history

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.dtu.componentscanner.data.local.HistoryEntity
import com.dtu.componentscanner.data.repository.HistoryRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch
import javax.inject.Inject

@HiltViewModel
class HistoryViewModel @Inject constructor(
    private val repository: HistoryRepository,
) : ViewModel() {

    val state: StateFlow<List<HistoryEntity>> =
        repository.observeHistory()
            .stateIn(viewModelScope, SharingStarted.Eagerly, emptyList())

    fun delete(partNumber: String) {
        viewModelScope.launch { repository.delete(partNumber) }
    }
}
