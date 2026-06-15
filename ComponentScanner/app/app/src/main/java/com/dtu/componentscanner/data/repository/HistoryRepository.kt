package com.dtu.componentscanner.data.repository

import com.dtu.componentscanner.data.local.HistoryDao
import com.dtu.componentscanner.data.local.HistoryEntity
import kotlinx.coroutines.flow.Flow
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class HistoryRepository @Inject constructor(
    private val dao: HistoryDao,
) {
    fun observeHistory(): Flow<List<HistoryEntity>> = dao.observeAll()

    suspend fun record(partNumber: String, manufacturer: String, datasheetUrl: String, timestamp: Long) {
        dao.upsert(HistoryEntity(partNumber, manufacturer, datasheetUrl, timestamp))
    }

    suspend fun delete(partNumber: String) = dao.deleteByPart(partNumber)
}
