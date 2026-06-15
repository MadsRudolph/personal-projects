package com.dtu.componentscanner.data

import com.dtu.componentscanner.data.local.HistoryDao
import com.dtu.componentscanner.data.local.HistoryEntity
import com.dtu.componentscanner.data.repository.HistoryRepository
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertEquals
import org.junit.Test

class HistoryRepositoryTest {

    private class FakeDao : HistoryDao {
        val items = MutableStateFlow<List<HistoryEntity>>(emptyList())
        override fun observeAll(): Flow<List<HistoryEntity>> = items
        override suspend fun upsert(entity: HistoryEntity) {
            items.value = listOf(entity) + items.value.filterNot { it.partNumber == entity.partNumber }
        }
        override suspend fun deleteByPart(partNumber: String) {
            items.value = items.value.filterNot { it.partNumber == partNumber }
        }
    }

    @Test
    fun `record adds an entry observable via the flow`() = runTest {
        val repo = HistoryRepository(FakeDao())
        repo.record("LM358N", "TI", "https://x/lm358.pdf", 1000L)
        val all = repo.observeHistory().first()
        assertEquals("LM358N", all.first().partNumber)
    }

    @Test
    fun `record of the same part replaces the prior entry`() = runTest {
        val dao = FakeDao()
        val repo = HistoryRepository(dao)
        repo.record("LM358N", "TI", "url1", 1000L)
        repo.record("LM358N", "TI", "url2", 2000L)
        val all = repo.observeHistory().first()
        assertEquals(1, all.size)
        assertEquals("url2", all.first().datasheetUrl)
    }
}
