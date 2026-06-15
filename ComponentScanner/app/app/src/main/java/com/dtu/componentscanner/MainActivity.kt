package com.dtu.componentscanner

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import com.dtu.componentscanner.ui.MainNavGraph
import com.dtu.componentscanner.ui.theme.ComponentScannerTheme
import dagger.hilt.android.AndroidEntryPoint

@AndroidEntryPoint
class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            ComponentScannerTheme {
                MainNavGraph()
            }
        }
    }
}
