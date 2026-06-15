package com.dtu.componentscanner.data

import com.dtu.componentscanner.data.remote.ApiService
import com.dtu.componentscanner.data.remote.CandidateDto
import com.dtu.componentscanner.data.remote.DatasheetResponse
import com.dtu.componentscanner.data.remote.IdentifyRequest
import com.dtu.componentscanner.data.remote.IdentifyResponse
import com.dtu.componentscanner.data.repository.ComponentRepository
import com.dtu.componentscanner.data.repository.IdentifyOutcome
import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class ComponentRepositoryTest {

    private class FakeApi(
        val identifyResult: () -> IdentifyResponse = { IdentifyResponse(emptyList()) },
        val datasheetResult: () -> DatasheetResponse = {
            DatasheetResponse("LM358N", "TI", "https://x/lm358.pdf")
        },
    ) : ApiService {
        var lastRequest: IdentifyRequest? = null
        override suspend fun identify(body: IdentifyRequest): IdentifyResponse {
            lastRequest = body; return identifyResult()
        }
        override suspend fun datasheet(part: String): DatasheetResponse = datasheetResult()
    }

    @Test
    fun `identify maps candidates and forwards the request`() = runTest {
        val api = FakeApi(identifyResult = {
            IdentifyResponse(listOf(CandidateDto("lm358n", "TI", "DIP-8", 0.9)))
        })
        val repo = ComponentRepository(api)

        val outcome = repo.identify("BASE64", "image/jpeg", "single")

        assertTrue(outcome is IdentifyOutcome.Success)
        val success = outcome as IdentifyOutcome.Success
        assertEquals("lm358n", success.candidates.first().partNumber)
        assertEquals("BASE64", api.lastRequest?.imageBase64)
    }

    @Test
    fun `identify returns Error on exception`() = runTest {
        val api = object : ApiService {
            override suspend fun identify(body: IdentifyRequest) = throw RuntimeException("boom")
            override suspend fun datasheet(part: String) = throw RuntimeException("boom")
        }
        val repo = ComponentRepository(api)
        val outcome = repo.identify("B", "image/jpeg", "single")
        assertTrue(outcome is IdentifyOutcome.Error)
    }

    @Test
    fun `datasheet maps the response to domain`() = runTest {
        val repo = ComponentRepository(FakeApi())
        val sheet = repo.datasheet("LM358N")
        assertEquals("TI", sheet?.manufacturer)
        assertEquals("https://x/lm358.pdf", sheet?.datasheetUrl)
    }

    @Test
    fun `datasheet returns null when the backend 404s`() = runTest {
        val api = object : ApiService {
            override suspend fun identify(body: IdentifyRequest) = IdentifyResponse(emptyList())
            override suspend fun datasheet(part: String): DatasheetResponse =
                throw retrofit2.HttpException(
                    retrofit2.Response.error<Any>(404, okhttp3.ResponseBody.create(null, "not found"))
                )
        }
        val repo = ComponentRepository(api)
        assertEquals(null, repo.datasheet("NOPART"))
    }
}
