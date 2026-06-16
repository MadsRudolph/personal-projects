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
        override suspend fun getByPart(partNumber: String): HistoryEntity? =
            items.value.firstOrNull { it.partNumber == partNumber }
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
            override suspend fun download(url: String) = "%PDF-1.7\n...".toByteArray()
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

    @Test
    fun `load uses cache and skips the backend for a known part`() = runTest {
        val dao = FakeDao().apply {
            items.value = listOf(HistoryEntity("LM358N", "TI", "https://x/lm358.pdf", 1L))
        }
        java.io.File(tmp.root, "LM358N.pdf").writeBytes("%PDF-1.7".toByteArray())
        val repo = ComponentRepository(object : ApiService {
            override suspend fun identify(body: IdentifyRequest) = IdentifyResponse(emptyList())
            override suspend fun datasheet(part: String): DatasheetResponse =
                throw IllegalStateException("backend must not be called for a cached part")
        })
        val pdfCache = PdfCache(tmp.root, object : PdfDownloader {
            override suspend fun download(url: String): ByteArray =
                throw IllegalStateException("must not download a cached part")
        })
        val vm = ResultViewModel(repo, HistoryRepository(dao), pdfCache) { 0L }

        vm.load("LM358N")
        advanceUntilIdle()

        val state = vm.state.value
        assertEquals("TI", state.datasheet?.manufacturer)
        assertNotNull(state.localPdfPath)
        assertEquals(null, state.error)
    }

    @Test
    fun `load keeps datasheet url when in-app download fails`() = runTest {
        val pdfCache = PdfCache(tmp.root, object : PdfDownloader {
            override suspend fun download(url: String): ByteArray =
                throw java.io.IOException("blocked")
        })
        val vm = ResultViewModel(componentRepo(), HistoryRepository(FakeDao()), pdfCache) { 0L }

        vm.load("L7805CV")
        advanceUntilIdle()

        val state = vm.state.value
        assertNotNull(state.datasheet)            // URL still available for the browser
        assertEquals(true, state.downloadFailed)
        assertEquals(null, state.localPdfPath)
        assertEquals(null, state.error)           // download failure is not fatal
    }
}
