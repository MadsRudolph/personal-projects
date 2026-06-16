package com.dtu.componentscanner.ui

import androidx.compose.runtime.Composable
import androidx.navigation.NavType
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import androidx.navigation.navArgument
import com.dtu.componentscanner.ui.history.HistoryScreen
import com.dtu.componentscanner.ui.pdf.PdfViewerScreen
import com.dtu.componentscanner.ui.pdf.WebPdfViewerScreen
import com.dtu.componentscanner.ui.result.ResultScreen
import com.dtu.componentscanner.ui.scan.ScanScreen
import java.net.URLDecoder
import java.net.URLEncoder

object Routes {
    const val SCAN = "scan"
    const val HISTORY = "history"
    const val RESULT = "result/{part}"
    const val PDF = "pdf/{path}"
    const val PDFWEB = "pdfweb/{url}"
    fun result(part: String) = "result/$part"
    fun pdf(path: String) = "pdf/${URLEncoder.encode(path, "UTF-8")}"
    fun pdfWeb(url: String) = "pdfweb/${URLEncoder.encode(url, "UTF-8")}"
}

@Composable
fun MainNavGraph() {
    val nav = rememberNavController()
    NavHost(navController = nav, startDestination = Routes.SCAN) {
        composable(Routes.SCAN) {
            ScanScreen(
                onPartChosen = { part -> nav.navigate(Routes.result(part)) },
                onOpenHistory = { nav.navigate(Routes.HISTORY) },
            )
        }
        composable(Routes.HISTORY) {
            HistoryScreen(
                onOpenPart = { part -> nav.navigate(Routes.result(part)) },
                onBack = { nav.popBackStack() },
            )
        }
        composable(
            Routes.RESULT,
            arguments = listOf(navArgument("part") { type = NavType.StringType }),
        ) { entry ->
            val part = entry.arguments?.getString("part").orEmpty()
            ResultScreen(
                partNumber = part,
                onOpenPdf = { path -> nav.navigate(Routes.pdf(path)) },
                onOpenPdfWeb = { url -> nav.navigate(Routes.pdfWeb(url)) },
                onBack = { nav.popBackStack() },
            )
        }
        composable(
            Routes.PDF,
            arguments = listOf(navArgument("path") { type = NavType.StringType }),
        ) { entry ->
            val path = URLDecoder.decode(entry.arguments?.getString("path").orEmpty(), "UTF-8")
            PdfViewerScreen(filePath = path, onBack = { nav.popBackStack() })
        }
        composable(
            Routes.PDFWEB,
            arguments = listOf(navArgument("url") { type = NavType.StringType }),
        ) { entry ->
            val url = URLDecoder.decode(entry.arguments?.getString("url").orEmpty(), "UTF-8")
            WebPdfViewerScreen(pdfUrl = url, onBack = { nav.popBackStack() })
        }
    }
}
