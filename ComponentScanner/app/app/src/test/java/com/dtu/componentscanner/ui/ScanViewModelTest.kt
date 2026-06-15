package com.dtu.componentscanner.ui

import com.dtu.componentscanner.data.remote.ApiService
import com.dtu.componentscanner.data.remote.CandidateDto
import com.dtu.componentscanner.data.remote.DatasheetResponse
import com.dtu.componentscanner.data.remote.IdentifyRequest
import com.dtu.componentscanner.data.remote.IdentifyResponse
import com.dtu.componentscanner.data.repository.ComponentRepository
import com.dtu.componentscanner.domain.PartNumberExtractor
import com.dtu.componentscanner.ui.scan.ScanMode
import com.dtu.componentscanner.ui.scan.ScanUiState
import com.dtu.componentscanner.ui.scan.ScanViewModel
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.test.StandardTestDispatcher
import kotlinx.coroutines.test.advanceUntilIdle
import kotlinx.coroutines.test.resetMain
import kotlinx.coroutines.test.runTest
import kotlinx.coroutines.test.setMain
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test

class ScanViewModelTest {
    private val dispatcher = StandardTestDispatcher()

    @Before fun setUp() = Dispatchers.setMain(dispatcher)
    @After fun tearDown() = Dispatchers.resetMain()

    private fun repo(candidates: List<CandidateDto>) = ComponentRepository(object : ApiService {
        override suspend fun identify(body: IdentifyRequest) = IdentifyResponse(candidates)
        override suspend fun datasheet(part: String) = DatasheetResponse("X", "Y", "https://x/y.pdf")
    })

    @Test
    fun `onOcrText updates the live detected part from the best candidate`() = runTest {
        val vm = ScanViewModel(repo(emptyList()), PartNumberExtractor())
        vm.onOcrText("TEXAS\nLM358N\n2143")
        assertEquals("LM358N", vm.state.value.liveDetectedPart)
    }

    @Test
    fun `deepScan sets candidates from the backend`() = runTest {
        val vm = ScanViewModel(
            repo(listOf(CandidateDto("STM32F103", "ST", null, 0.95))),
            PartNumberExtractor(),
        )
        vm.deepScan("BASE64", "image/jpeg")
        advanceUntilIdle()
        val state = vm.state.value
        assertTrue(state.candidates.isNotEmpty())
        assertEquals("STM32F103", state.candidates.first().partNumber)
        assertEquals(false, state.isScanning)
    }

    @Test
    fun `deepScan toggles isScanning during the call`() = runTest {
        val vm = ScanViewModel(repo(emptyList()), PartNumberExtractor())
        vm.deepScan("B", "image/jpeg")
        assertEquals(true, vm.state.value.isScanning) // before dispatcher runs
        advanceUntilIdle()
        assertEquals(false, vm.state.value.isScanning)
    }

    @Test
    fun `setMode switches mode and clears candidates`() = runTest {
        val vm = ScanViewModel(repo(emptyList()), PartNumberExtractor())
        vm.setMode(ScanMode.SHELF)
        assertEquals(ScanMode.SHELF, vm.state.value.scanMode)
        assertTrue(vm.state.value.candidates.isEmpty())
        vm.setMode(ScanMode.SINGLE)
        assertEquals(ScanMode.SINGLE, vm.state.value.scanMode)
    }

    @Test
    fun `lookupManual returns null for blank input`() = runTest {
        val vm = ScanViewModel(repo(emptyList()), PartNumberExtractor())
        assertNull(vm.lookupManual(""))
        assertNull(vm.lookupManual("   "))
        assertNull(vm.lookupManual("\t\n"))
    }

    @Test
    fun `lookupManual returns normalized part number for non-blank input`() = runTest {
        val vm = ScanViewModel(repo(emptyList()), PartNumberExtractor())
        assertEquals("LM358N", vm.lookupManual("lm358n"))
        assertEquals("LM358N", vm.lookupManual("  lm358n  "))
        assertEquals("STM32F103", vm.lookupManual("stm32f103"))
    }

    @Test
    fun `reportError sets the error message and clears scanning`() = runTest {
        val vm = ScanViewModel(repo(emptyList()), PartNumberExtractor())
        // Simulate a scan in-flight
        vm.deepScan("B", "image/jpeg")
        assertEquals(true, vm.state.value.isScanning)
        // A capture error arrives before the backend responds
        vm.reportError("Capture failed")
        assertEquals(false, vm.state.value.isScanning)
        assertEquals("Capture failed", vm.state.value.error)
    }

    @Test
    fun `deepScan in SHELF mode requests shelf and stores all candidates`() = runTest {
        var capturedMode: String? = null
        val fakeRepo = ComponentRepository(object : ApiService {
            override suspend fun identify(body: IdentifyRequest): IdentifyResponse {
                capturedMode = body.mode
                return IdentifyResponse(
                    listOf(
                        CandidateDto("LM358N", "TI", null, 0.9),
                        CandidateDto("LM741", "NS", null, 0.7),
                    )
                )
            }
            override suspend fun datasheet(part: String) =
                DatasheetResponse("X", "Y", "https://x/y.pdf")
        })
        val vm = ScanViewModel(fakeRepo, PartNumberExtractor())
        vm.setMode(ScanMode.SHELF)
        vm.deepScan("BASE64", "image/jpeg")
        advanceUntilIdle()
        assertEquals("shelf", capturedMode)
        assertEquals(2, vm.state.value.candidates.size)
    }
}
