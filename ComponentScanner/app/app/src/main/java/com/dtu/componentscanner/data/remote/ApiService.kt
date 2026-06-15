package com.dtu.componentscanner.data.remote

import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.POST
import retrofit2.http.Query

interface ApiService {
    @POST("identify")
    suspend fun identify(@Body body: IdentifyRequest): IdentifyResponse

    @GET("datasheet")
    suspend fun datasheet(@Query("part") part: String): DatasheetResponse
}
