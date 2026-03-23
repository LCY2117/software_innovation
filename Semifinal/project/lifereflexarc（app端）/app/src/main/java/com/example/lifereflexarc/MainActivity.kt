package com.example.lifereflexarc

import android.os.Bundle
import android.provider.Settings
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Scaffold
import androidx.compose.runtime.Composable
import androidx.compose.runtime.remember
import androidx.compose.ui.Modifier
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.platform.LocalContext
import androidx.lifecycle.viewmodel.compose.viewModel
import com.example.lifereflexarc.ui.PhoneAppRoot
import com.example.lifereflexarc.ui.theme.LifeReflexArcTheme
import com.example.lifereflexarc.viewmodel.IncidentViewModel
import java.util.UUID

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContent {
            LifeReflexArcTheme {
                Scaffold(modifier = Modifier.fillMaxSize()) { innerPadding ->
                    DemoApp(modifier = Modifier.padding(innerPadding))
                }
            }
        }
    }
}

@Composable
fun DemoApp(modifier: Modifier = Modifier, vm: IncidentViewModel = viewModel()) {
    val context = LocalContext.current
    val userId = remember {
        Settings.Secure.getString(context.contentResolver, Settings.Secure.ANDROID_ID)
            ?: UUID.randomUUID().toString()
    }
    androidx.compose.foundation.layout.Box(modifier = modifier.fillMaxSize()) {
        PhoneAppRoot(viewModel = vm, userId = userId)
    }
}

@Preview(showBackground = true)
@Composable
fun AppPreview() {
    LifeReflexArcTheme {
        DemoApp()
    }
}
