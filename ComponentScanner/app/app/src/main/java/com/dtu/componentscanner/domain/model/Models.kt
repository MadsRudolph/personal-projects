package com.dtu.componentscanner.domain.model

data class Candidate(
    val partNumber: String,
    val manufacturer: String? = null,
    val packageType: String? = null,
    val confidence: Double,
)

data class KeySpec(val name: String, val value: String)

data class Datasheet(
    val partNumber: String,
    val manufacturer: String,
    val datasheetUrl: String,
    val keySpecs: List<KeySpec> = emptyList(),
)
