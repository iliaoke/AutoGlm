package com.example.autoglm

import android.content.Context
import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.os.PowerManager
import android.provider.Settings
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import com.chaquo.python.PyException
import com.chaquo.python.Python
import com.chaquo.python.android.AndroidPlatform
import com.example.autoglm.ui.theme.PythonTheme
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.io.File
import kotlin.concurrent.thread

class MainActivity : ComponentActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        if (!Python.isStarted()) {
            Python.start(AndroidPlatform(this))
        }

        enableEdgeToEdge()
        setContent {
            PythonTheme {
                Scaffold(modifier = Modifier.fillMaxSize()) { innerPadding ->
                    PythonRunnerScreen(
                        modifier = Modifier.padding(innerPadding)
                    )
                }
            }
        }
    }
}

@Composable
fun PythonRunnerScreen(modifier: Modifier = Modifier) {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    val sharedPrefs = remember { context.getSharedPreferences("python_agent_prefs", Context.MODE_PRIVATE) }

    var logText by remember { mutableStateOf("") }
    var isRunning by remember { mutableStateOf(false) }
    var isBusy by remember { mutableStateOf(false) }
    val scrollState = rememberScrollState()

    var showBatteryDialog by remember { mutableStateOf(false) }

    // 使用记忆功能的配置状态
    var baseUrl by remember { mutableStateOf(sharedPrefs.getString("baseUrl", "https://open.bigmodel.cn/api/paas/v4") ?: "") }
    var modelName by remember { mutableStateOf(sharedPrefs.getString("modelName", "autoglm-phone") ?: "") }
    var apiKey by remember { mutableStateOf(sharedPrefs.getString("apiKey", "7cac4475c608078c12732a1550543a4e.YptHcHXkTcXm1irT") ?: "") }
    var taskInput by remember { mutableStateOf(sharedPrefs.getString("taskInput", "打开美团搜索附近的火锅店") ?: "") }

    // ADB UI State (同样增加记忆功能)
    var connectAddress by remember { mutableStateOf(sharedPrefs.getString("connectAddress", "") ?: "") }
    var pairAddress by remember { mutableStateOf(sharedPrefs.getString("pairAddress", "") ?: "") }
    var pairingCode by remember { mutableStateOf(sharedPrefs.getString("pairingCode", "") ?: "") }

    // 定义一个通用的保存函数
    val savePref = { key: String, value: String ->
        sharedPrefs.edit().putString(key, value).apply()
    }

    // 1. 启动即检查电池白名单
    LaunchedEffect(Unit) {
        val pm = context.getSystemService(Context.POWER_SERVICE) as PowerManager
        if (!pm.isIgnoringBatteryOptimizations(context.packageName)) {
            showBatteryDialog = true
        }
    }

    if (showBatteryDialog) {
        AlertDialog(
            onDismissRequest = { showBatteryDialog = false },
            title = { Text("后台运行保护") },
            text = { Text("为了保证 AI 自动化脚本在切换应用后不被系统冻结，请允许应用忽略电池优化。") },
            confirmButton = {
                Button(onClick = {
                    showBatteryDialog = false
                    val intent = Intent(Settings.ACTION_REQUEST_IGNORE_BATTERY_OPTIMIZATIONS).apply {
                        data = Uri.parse("package:${context.packageName}")
                    }
                    context.startActivity(intent)
                }) { Text("立即设置") }
            },
            dismissButton = {
                TextButton(onClick = { showBatteryDialog = false }) { Text("以后再说") }
            }
        )
    }

    // 自动运行 adb start-server
    LaunchedEffect(Unit) {
        withContext(Dispatchers.Main) { logText += "--- 自动初始化 ADB Server ---\n" }
        withContext(Dispatchers.IO) {
            Adb.exec(context, listOf("start-server")) { line ->
                scope.launch(Dispatchers.Main) { logText += "$line\n" }
            }
        }
        withContext(Dispatchers.Main) { logText += "ADB Server 初始化完成\n" }
    }

    LaunchedEffect(logText) {
        scrollState.animateScrollTo(scrollState.maxValue)
    }

    Column(
        modifier = modifier.fillMaxSize().padding(16.dp).verticalScroll(rememberScrollState())
    ) {
        Text("1. ADB 无线配对", style = MaterialTheme.typography.titleLarge)
        Spacer(modifier = Modifier.height(8.dp))
        OutlinedTextField(
            value = pairAddress,
            onValueChange = { pairAddress = it; savePref("pairAddress", it) },
            label = { Text("配对地址") },
            modifier = Modifier.fillMaxWidth(),
            singleLine = true,
            enabled = !isBusy
        )
        OutlinedTextField(
            value = pairingCode,
            onValueChange = { pairingCode = it; savePref("pairingCode", it) },
            label = { Text("6位配对码") },
            modifier = Modifier.fillMaxWidth(),
            singleLine = true,
            enabled = !isBusy
        )
        Button(onClick = {
            if (isBusy) return@Button
            isBusy = true
            scope.launch(Dispatchers.IO) {
                Adb.pair(context, pairAddress, pairingCode) { line -> scope.launch(Dispatchers.Main) { logText += "$line\n" } }
                withContext(Dispatchers.Main) { isBusy = false }
            }
        }, modifier = Modifier.fillMaxWidth(), enabled = !isBusy) { Text("立即配对") }

        Spacer(modifier = Modifier.height(16.dp))
        Text("2. ADB 无线连接", style = MaterialTheme.typography.titleLarge)
        Spacer(modifier = Modifier.height(8.dp))
        OutlinedTextField(
            value = connectAddress,
            onValueChange = { connectAddress = it; savePref("connectAddress", it) },
            label = { Text("连接地址") },
            modifier = Modifier.fillMaxWidth(),
            singleLine = true,
            enabled = !isBusy
        )
        Button(onClick = {
            if (isBusy) return@Button
            isBusy = true
            scope.launch(Dispatchers.IO) {
                Adb.connect(context, connectAddress) { line -> scope.launch(Dispatchers.Main) { logText += "$line\n" } }
                withContext(Dispatchers.Main) { isBusy = false }
            }
        }, modifier = Modifier.fillMaxWidth(), enabled = !isBusy) { Text("建立连接") }

        Spacer(modifier = Modifier.height(16.dp))
        HorizontalDivider()
        Spacer(modifier = Modifier.height(16.dp))

        Text("3. AI 代理参数配置", style = MaterialTheme.typography.titleLarge)
        Spacer(modifier = Modifier.height(8.dp))
        OutlinedTextField(
            value = baseUrl,
            onValueChange = { baseUrl = it; savePref("baseUrl", it) },
            label = { Text("API Base URL") },
            modifier = Modifier.fillMaxWidth(),
            singleLine = true
        )
        OutlinedTextField(
            value = modelName,
            onValueChange = { modelName = it; savePref("modelName", it) },
            label = { Text("模型名称") },
            modifier = Modifier.fillMaxWidth(),
            singleLine = true
        )
        OutlinedTextField(
            value = apiKey,
            onValueChange = { apiKey = it; savePref("apiKey", it) },
            label = { Text("API Key") },
            modifier = Modifier.fillMaxWidth(),
            singleLine = true
        )
        OutlinedTextField(
            value = taskInput,
            onValueChange = { taskInput = it; savePref("taskInput", it) },
            label = { Text("任务指令 (例如: 打开微信...)") },
            modifier = Modifier.fillMaxWidth(),
            minLines = 2
        )

        Spacer(modifier = Modifier.height(24.dp))
        Button(
            onClick = {
                if (isRunning || isBusy) return@Button
                isRunning = true
                logText += "开始执行 AI 任务...\n"
                runPython(
                    context = context,
                    baseUrl = baseUrl,
                    model = modelName,
                    apiKey = apiKey,
                    task = taskInput,
                    onLog = { msg -> logText += msg },
                    onFinish = { isRunning = false }
                )
            },
            modifier = Modifier.fillMaxWidth(),
            colors = ButtonDefaults.buttonColors(containerColor = MaterialTheme.colorScheme.secondary),
            enabled = !isRunning && !isBusy
        ) {
            Text(if (isRunning) "任务运行中..." else "开始执行任务")
        }

        Spacer(modifier = Modifier.height(12.dp))
        Surface(modifier = Modifier.fillMaxWidth().heightIn(min = 200.dp, max = 500.dp), color = MaterialTheme.colorScheme.surfaceVariant, shape = MaterialTheme.shapes.medium) {
            Box(modifier = Modifier.padding(8.dp).verticalScroll(scrollState)) { Text(text = logText, style = MaterialTheme.typography.bodySmall) }
        }
    }
}

private fun runPython(
    context: Context,
    baseUrl: String,
    model: String,
    apiKey: String,
    task: String,
    onLog: (String) -> Unit,
    onFinish: () -> Unit
) {
    thread {
        val pm = context.getSystemService(Context.POWER_SERVICE) as PowerManager
        val wakeLock = pm.newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, "Python:Run").apply { acquire(15*60*1000L) }
        try {
            val adbPath = File(context.applicationInfo.nativeLibraryDir, "libadb.so").absolutePath
            val py = Python.getInstance()
            val module = py.getModule("main")
            
            val result = module.callAttr(
                "main", 
                "--adb-path", adbPath, 
                "--base-url", baseUrl, 
                "--model", model, 
                "--apikey", apiKey, 
                "--device-type", "adb", 
                task
            )
            onLog("任务结束：\n$result\n")
        } catch (e: Exception) {
            onLog("运行错误：\n${e.message}\n")
        } finally {
            if (wakeLock.isHeld) wakeLock.release()
            onFinish()
        }
    }
}
