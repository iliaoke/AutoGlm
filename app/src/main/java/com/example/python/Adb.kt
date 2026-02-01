package com.example.autoglm

import android.content.Context
import java.io.File

object Adb {
    /**
     * 原始命令执行器：不带任何环境变量优化，仅透传参数和返回原始日志
     */
    fun exec(
        ctx: Context,
        args: List<String>,
        input: String? = null,
        onLine: ((String) -> Unit)? = null
    ): String {
        val adbPath = File(ctx.applicationInfo.nativeLibraryDir, "libadb.so").absolutePath
        
        val process = ProcessBuilder(listOf(adbPath) + args)
            .redirectErrorStream(true)
            .start()

        // 原始输入处理
        input?.let {
            try {
                process.outputStream.bufferedWriter().use { w ->
                    w.write(it)
                    w.newLine()
                    w.flush()
                }
            } catch (e: Exception) {}
        } ?: try { process.outputStream.close() } catch (e: Exception) {}

        val output = StringBuilder()
        // 原始输出读取
        process.inputStream.bufferedReader().forEachLine { line ->
            onLine?.invoke(line)
            output.append(line).append("\n")
        }
        
        process.waitFor()
        return output.toString().trim()
    }

    fun connect(ctx: Context, addr: String, onLine: ((String) -> Unit)? = null) = 
        exec(ctx, listOf("connect", addr), onLine = onLine)

    fun pair(ctx: Context, addr: String, code: String, onLine: ((String) -> Unit)? = null) = 
        exec(ctx, listOf("pair", addr), input = code, onLine = onLine)
}
