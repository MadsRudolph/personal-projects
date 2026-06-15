package com.dtu.componentscanner.data.remote

import com.dtu.componentscanner.domain.model.Candidate
import com.dtu.componentscanner.domain.model.Datasheet
import com.dtu.componentscanner.domain.model.KeySpec
import kotlinx.serialization.Serializable

@Serializable
data class IdentifyRequest(
    val imageBase64: String,
    val mimeType: String,
    val mode: String, // "single" | "shelf"
)

@Serializable
data class CandidateDto(
    val partNumber: String,
    val manufacturer: String? = null,
    val packageType: String? = null,
    val confidence: Double,
)

@Serializable
data class IdentifyResponse(
    val candidates: List<CandidateDto> = emptyList(),
    val cached: Boolean = false,
)

@Serializable
data class KeySpecDto(val name: String, val value: String)

@Serializable
data class DatasheetResponse(
    val partNumber: String,
    val manufacturer: String,
    val datasheetUrl: String,
    val keySpecs: List<KeySpecDto> = emptyList(),
)

fun CandidateDto.toDomain() = Candidate(partNumber, manufacturer, packageType, confidence)
fun DatasheetResponse.toDomain() =
    Datasheet(partNumber, manufacturer, datasheetUrl, keySpecs.map { KeySpec(it.name, it.value) })
