package com.dtu.componentscanner.ui

import com.dtu.componentscanner.data.local.HistoryDao
import com.dtu.componentscanner.data.local.HistoryEntity
import com.dtu.componentscanner.data.repository.HistoryRepository
import com.dtu.componentscanner.ui.history.HistoryViewModel
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.test.StandardTestDispatcher
import kotlinx.coroutines.test.advanceUntilIdle
import kotlinx.coroutines.test.resetMain
import kotlinx.coroutines.test.runTest
import kotlinx.coroutines.test.setMain
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Before
import org.junit.Test

class HistoryViewModelTest {
    private val dispatcher = StandardTestDispatcher()
    @Before fun setUp() = Dispatchers.setMain(dispatcher)
    @After fun tearDown() = Dispatchers.resetMain()

    private class FakeDao(initial: List<HistoryEntity>) : HistoryDao {
        val items = MutableStateFlow(initial)
        override fun observeAll(): Flow<List<HistoryEntity>> = items
        override suspend fun upsert(entity: HistoryEntity) {}
        override suspend fun deleteByPart(partNumber: String) {
            items.value = items.value.filterNot { it.partNumber == partNumber }
        }
    }

    @Test
    fun `exposes history items from the repository`() = runTest {
        val dao = FakeDao(listOf(HistoryEntity("LM358N", "TI", "url", 1L)))
        val vm = HistoryViewModel(HistoryRepository(dao))
        advanceUntilIdle()
        assertEquals(1, vm.state.value.size)
        assertEquals("LM358N", vm.state.value.first().partNumber)
    }

    @Test
    fun `delete removes an item`() = runTest {
        val dao = FakeDao(listOf(HistoryEntity("LM358N", "TI", "url", 1L)))
        val vm = HistoryViewModel(HistoryRepository(dao))
        advanceUntilIdle()
        vm.delete("LM358N")
        advanceUntilIdle()
        assertEquals(0, vm.state.value.size)
    }
}
