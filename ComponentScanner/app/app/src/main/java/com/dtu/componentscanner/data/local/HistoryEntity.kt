package com.dtu.componentscanner.data.local

import androidx.room.Entity
import androidx.room.PrimaryKey

@Entity(tableName = "scan_history")
data class HistoryEntity(
    @PrimaryKey val partNumber: String,
    val manufacturer: String,
    val datasheetUrl: String,
    val timestamp: Long,
)
