package com.dtu.componentscanner.data.repository

import com.dtu.componentscanner.data.remote.ApiService
import com.dtu.componentscanner.data.remote.IdentifyRequest
import com.dtu.componentscanner.data.remote.toDomain
import com.dtu.componentscanner.domain.model.Candidate
import com.dtu.componentscanner.domain.model.Datasheet
import retrofit2.HttpException
import javax.inject.Inject
import javax.inject.Singleton

sealed interface IdentifyOutcome {
    data class Success(val candidates: List<Candidate>) : IdentifyOutcome
    data class Error(val message: String) : IdentifyOutcome
}

@Singleton
class ComponentRepository @Inject constructor(
    private val api: ApiService,
) {
    suspend fun identify(imageBase64: String, mimeType: String, mode: String): IdentifyOutcome =
        try {
            val response = api.identify(IdentifyRequest(imageBase64, mimeType, mode))
            IdentifyOutcome.Success(response.candidates.map { it.toDomain() })
        } catch (e: Exception) {
            IdentifyOutcome.Error(e.message ?: "identify failed")
        }

    /** Returns null when no datasheet exists (backend 404) or on transport failure. */
    suspend fun datasheet(partNumber: String): Datasheet? =
        try {
            api.datasheet(partNumber).toDomain()
        } catch (e: HttpException) {
            if (e.code() == 404) null else throw e
        }
}
