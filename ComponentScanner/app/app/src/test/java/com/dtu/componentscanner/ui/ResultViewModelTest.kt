package com.dtu.componentscanner.ui

import com.dtu.componentscanner.data.local.HistoryDao
import com.dtu.componentscanner.data.local.HistoryEntity
import com.dtu.componentscanner.data.pdf.PdfCache
import com.dtu.componentscanner.data.pdf.PdfDownloader
import com.dtu.componentscanner.data.remote.ApiService
import com.dtu.componentscanner.data.remote.DatasheetResponse
import com.dtu.componentscanner.data.remote.IdentifyRequest
import com.dtu.componentscanner.data.remote.IdentifyResponse
import com.dtu.componentscanner.data.repository.ComponentRepository
import com.dtu.componentscanner.data.repository.HistoryRepository
import com.dtu.componentscanner.ui.result.ResultViewModel
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
import org.junit.Assert.assertNotNull
import org.junit.Before
import org.junit.Rule
import org.junit.Test
import org.junit.rules.TemporaryFolder

class ResultViewModelTest {
    private val dispatcher = StandardTestDispatcher()
    @get:Rule val tmp = TemporaryFolder()

    @Before fun setUp() = Dispatchers.setMain(dispatcher)
    @After fun tearDown() = Dispatchers.resetMain()

    private class FakeDao : HistoryDao {
        val items = MutableStateFlow<List<HistoryEntity>>(emptyList())
        override fun observeAll(): Flow<List<HistoryEntity>> = items
        override suspend fun upsert(entity: HistoryEntity) { items.value = listOf(entity) }
        override suspend fun deleteByPart(partNumber: String) {}
    }

    private fun componentRepo() = ComponentRepository(object : ApiService {
        override suspend fun identify(body: IdentifyRequest) = IdentifyResponse(emptyList())
        override suspend fun datasheet(part: String) =
            DatasheetResponse("LM358N", "TI", "https://x/lm358.pdf")
    })

    @Test
    fun `load resolves datasheet, records history, and caches the pdf`() = runTest {
        val dao = FakeDao()
        val pdfCache = PdfCache(tmp.root, object : PdfDownloader {
            override suspend fun download(url: String) = byteArrayOf(9, 9, 9)
        })
        val vm = ResultViewModel(componentRepo(), HistoryRepository(dao), pdfCache) { 1234L }

        vm.load("LM358N")
        advanceUntilIdle()

        val state = vm.state.value
        assertEquals("TI", state.datasheet?.manufacturer)
        assertNotNull(state.localPdfPath)
        assertEquals("LM358N", dao.items.value.first().partNumber)
        assertEquals(1234L, dao.items.value.first().timestamp)
    }

    @Test
    fun `load sets notFound when there is no datasheet`() = runTest {
        val repo = ComponentRepository(object : ApiService {
            override suspend fun identify(body: IdentifyRequest) = IdentifyResponse(emptyList())
            override suspend fun datasheet(part: String): DatasheetResponse =
                throw retrofit2.HttpException(
                    retrofit2.Response.error<Any>(404, okhttp3.ResponseBody.create(null, "x"))
                )
        })
        val pdfCache = PdfCache(tmp.root, object : PdfDownloader {
            override suspend fun download(url: String) = byteArrayOf()
        })
        val vm = ResultViewModel(repo, HistoryRepository(FakeDao()), pdfCache) { 0L }
        vm.load("NOPART")
        advanceUntilIdle()
        assertEquals(true, vm.state.value.notFound)
    }
}
