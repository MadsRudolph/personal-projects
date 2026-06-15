package com.dtu.componentscanner.di

import android.content.Context
import androidx.room.Room
import com.dtu.componentscanner.data.local.AppDatabase
import com.dtu.componentscanner.data.local.HistoryDao
import com.dtu.componentscanner.data.pdf.OkHttpPdfDownloader
import com.dtu.componentscanner.data.pdf.PdfCache
import com.dtu.componentscanner.data.pdf.PdfDownloader
import com.dtu.componentscanner.data.remote.ApiService
import com.dtu.componentscanner.data.remote.BackendConfig
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.android.qualifiers.ApplicationContext
import dagger.hilt.components.SingletonComponent
import kotlinx.serialization.json.Json
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import com.jakewharton.retrofit2.converter.kotlinx.serialization.asConverterFactory
import retrofit2.Retrofit
import java.io.File
import javax.inject.Singleton

@Module
@InstallIn(SingletonComponent::class)
object AppModule {

    @Provides @Singleton
    fun provideJson(): Json = Json { ignoreUnknownKeys = true }

    @Provides @Singleton
    fun provideOkHttp(): OkHttpClient = OkHttpClient.Builder().build()

    @Provides @Singleton
    fun provideRetrofit(client: OkHttpClient, json: Json): Retrofit =
        Retrofit.Builder()
            .baseUrl(BackendConfig.baseUrl)
            .client(client)
            .addConverterFactory(json.asConverterFactory("application/json".toMediaType()))
            .build()

    @Provides @Singleton
    fun provideApiService(retrofit: Retrofit): ApiService = retrofit.create(ApiService::class.java)

    @Provides @Singleton
    fun provideDatabase(@ApplicationContext ctx: Context): AppDatabase =
        Room.databaseBuilder(ctx, AppDatabase::class.java, "component-scanner.db").build()

    @Provides
    fun provideHistoryDao(db: AppDatabase): HistoryDao = db.historyDao()

    @Provides @Singleton
    fun providePdfDownloader(impl: OkHttpPdfDownloader): PdfDownloader = impl

    @Provides @Singleton
    fun providePdfCache(@ApplicationContext ctx: Context, downloader: PdfDownloader): PdfCache =
        PdfCache(File(ctx.cacheDir, "datasheets"), downloader)

    @Provides @Singleton
    fun provideClock(): () -> Long = { System.currentTimeMillis() }
}
