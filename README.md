# AutoGlm

一个**直接运行在安卓手机上**的 AutoGLM（[Open-AutoGLM](https://github.com/zai-org/Open-AutoGLM)）客户端。
无需电脑：App 内置 ADB 与 Python 运行时，通过「无线调试」连接本机，再调用视觉语言模型理解屏幕并自动操作手机。

> ⚠️ 本项目仅供研究和学习使用，严禁用于非法获取信息、干扰系统或任何违法活动。自动化操作可能产生真实后果（发消息、下单等），请在了解风险后使用。

## 工作原理

```
自然语言任务 ──► Compose 界面 (MainActivity)
                    │  Chaquopy 调用
                    ▼
              Python: main.py ──► PhoneAgent（截图 → 模型推理 → 解析动作 → 执行）
                    │                         │
                    │ OpenAI 兼容接口          │ adb 命令
                    ▼                         ▼
             AutoGLM 模型服务          内置 libadb.so ──(无线调试)──► 本机
```

1. 每一步截取当前屏幕，连同任务描述发送给模型（OpenAI 兼容 API）。
2. 模型返回思考过程和动作（如 `Launch` / `Tap` / `Swipe` / `Type` / `Back` / `Home` / `Wait` / `Take_over` / `finish` 等）。
3. 通过 ADB 执行动作，循环直到模型输出 `finish` 或达到最大步数（默认 100）。

## 功能

- 📱 纯手机端运行，内置 `libadb.so`（arm64-v8a），启动时自动执行 `adb start-server`
- 🔗 应用内完成 ADB 无线配对 / 连接
- 🤖 支持任何 OpenAI 兼容的 AutoGLM 服务（智谱 BigModel 云端或自部署 vLLM / SGLang）
- 🔋 运行时持有 WakeLock，并引导用户关闭电池优化，避免切到其它应用后被系统冻结
- 🌐 中英文提示词（`--lang cn|en`），Python 侧同时包含 Android / HarmonyOS(HDC) / iOS(WDA) 的适配代码（本 App 目前只使用 ADB）

## 环境要求

| 项目 | 要求 |
| --- | --- |
| 手机系统 | Android 10+（`minSdk 29`），需支持**无线调试**（Android 11+ 提供配对码功能） |
| CPU 架构 | arm64-v8a |
| 网络 | 手机与自身处于同一 WiFi（无线调试要求）；并能访问模型 API |
| 输入法 | 需要输入文字时，建议安装并启用 [ADB Keyboard](https://github.com/senzhk/ADBKeyBoard) |

## 使用方法

### 1. 准备手机

1. 开启开发者模式：`设置 → 关于手机 → 版本号` 连续点击约 10 次。
2. 开启 `开发者选项 → 无线调试`（需已连接 WiFi）。
3. 安装并启用 ADB Keyboard（用于文字输入）。

### 2. 配对与连接

1. 进入 `无线调试 → 使用配对码配对设备`，记下**配对地址**（`IP:端口`）和 **6 位配对码**。
2. 在 App 的「1. ADB 无线配对」中填入并点击「立即配对」。
   > 配对弹窗需保持显示；可使用分屏/小窗，或先在通知栏中输入。
3. 回到 `无线调试` 主页面，记下页面上的 **IP 地址和端口**（与配对端口不同），在「2. ADB 无线连接」中填入并点击「建立连接」。

### 3. 配置模型并运行

在「3. AI 代理参数配置」中填写：

| 字段 | 说明 | 默认值 |
| --- | --- | --- |
| API Base URL | OpenAI 兼容接口地址 | `https://open.bigmodel.cn/api/paas/v4` |
| 模型名称 | 服务端模型名 | `autoglm-phone` |
| API Key | 你自己的密钥 | 无 |

填写任务指令（例如：`打开微信，给文件传输助手发送你好`），点击「开始执行任务」，下方日志区会实时显示运行过程。
参数会保存在本地 SharedPreferences 中，下次无需重填。

**使用自部署模型**：模型下载地址见 [AutoGLM-Phone-9B](https://huggingface.co/zai-org/AutoGLM-Phone-9B) / [Multilingual 版](https://huggingface.co/zai-org/AutoGLM-Phone-9B-Multilingual)，按 Open-AutoGLM 文档用 vLLM/SGLang 部署后，把 Base URL 改为 `http://<服务器IP>:<端口>/v1` 即可。

## 构建

### 依赖

- Android Studio（AGP 9.0.0）、JDK 17、compileSdk 36
- [Chaquopy](https://chaquo.com/chaquopy/) 17.0.0（Gradle 插件，仓库已在 `settings.gradle.kts` 中配置）
- 构建机需安装 **Python 3.13**（Chaquopy 用其安装 pip 依赖）

### 步骤

1. 修改 `app/build.gradle.kts` 中的 `buildPython(...)` 为你本机 Python 3.13 的路径（当前是作者的 Windows 路径，**必须修改**；macOS/Linux 例如 `/usr/bin/python3.13`）。
2. 用 Android Studio 打开项目，等待 Gradle 同步完成。
3. 连接设备或模拟器（arm64）运行；或命令行：

   ```bash
   ./gradlew assembleDebug
   # 产物：app/build/outputs/apk/debug/app-debug.apk
   ```

## 项目结构

```
AutoGlm/
├── app/
│   ├── build.gradle.kts              # Chaquopy / pip 依赖 / 构建配置
│   └── src/main/
│       ├── AndroidManifest.xml
│       ├── java/com/example/python/
│       │   ├── MainActivity.kt       # Compose 界面、配对/连接、调用 Python
│       │   ├── Adb.kt                # 封装 libadb.so 的执行
│       │   └── ui/theme/
│       ├── jniLibs/arm64-v8a/libadb.so   # 内置 ADB 二进制
│       └── python/
│           ├── main.py               # 入口：参数解析、环境/模型检查、启动 Agent
│           ├── phone_agent/          # Agent 核心
│           │   ├── agent.py          # 主循环 (Android/鸿蒙)
│           │   ├── agent_ios.py
│           │   ├── model/            # 模型客户端
│           │   ├── actions/          # 动作解析与执行
│           │   ├── adb/              # 截图、输入、设备、连接
│           │   ├── config/           # 提示词、应用包名映射、时序、i18n
│           │   └── xctest/           # iOS 支持
│           └── scripts/              # 部署检查脚本与示例
└── gradle/ …
```

## `main.py` 参数

App 内部以如下参数调用 `main.main(...)`，也可在电脑上直接运行：

| 参数 | 说明 | 默认 |
| --- | --- | --- |
| `--base-url` | 模型服务地址 | — |
| `--model` | 模型名称 | — |
| `--apikey` | API Key | — |
| `--max-steps` | 最大执行步数 | 100 |
| `--device-id, -d` | 设备 ID；不填则自动选择第一个在线设备 | 自动 |
| `--adb-path` | adb 可执行文件路径 | `adb` |
| `--device-type` | `adb` / `hdc` / `ios` | `adb` |
| `--lang` | `cn` / `en` | `cn` |
| `--quiet, -q` | 精简输出 | 否 |
| `task` | 任务描述（位置参数） | — |

```bash
cd app/src/main/python
pip install -r requirements.txt && pip install -e . openai
python main.py --base-url http://localhost:8000/v1 --model autoglm-phone-9b --apikey EMPTY "打开设置"
```

## 权限说明

| 权限 | 用途 |
| --- | --- |
| `INTERNET` | 调用模型 API |
| `WAKE_LOCK` | 任务运行期间防止 CPU 休眠 |
| `REQUEST_IGNORE_BATTERY_OPTIMIZATIONS` | 引导用户关闭电池优化 |
| `MANAGE_EXTERNAL_STORAGE` | 访问外部存储 |

## 常见问题

- **配对失败**：确认配对弹窗仍在显示、地址端口正确、配对码未过期；手机需连接 WiFi。
- **连接后提示无设备 / `more than one device`**：先在日志中确认连接成功；程序会自动选择第一个状态为 `device` 的设备。
- **文字无法输入**：检查 ADB Keyboard 是否已安装并启用。
- **切换应用后任务中断**：在系统设置中允许本 App 忽略电池优化、允许后台运行。
- **`Model API unreachable`**：检查 Base URL（需包含 `/v1` 或 `/api/paas/v4` 等路径）、模型名与密钥、网络。
- **Gradle 同步失败（找不到 Python）**：修改 `buildPython` 路径。
- **敏感页面（支付、密码等）截图为黑屏**：属系统限制，模型会请求人工接管。

## 已知问题 / 待改进

- `MainActivity.kt` 中包含**硬编码的默认 API Key**，请立即在智谱后台**作废该密钥**并改为空默认值，避免泄露后被滥用。
- `buildPython` 为绝对路径，建议改为从 `local.properties` 读取。
- 源码目录为 `com/example/python`，但 `package`/`namespace` 为 `com.example.autoglm`，建议统一。
- `python/build/`、`*.egg-info/` 为构建产物，建议加入 `.gitignore`。

## 致谢与许可

基于 [Open-AutoGLM](https://github.com/zai-org/Open-AutoGLM)、[Chaquopy](https://chaquo.com/chaquopy/)、[ADB Keyboard](https://github.com/senzhk/ADBKeyBoard)。
使用前请遵守上游项目的使用条款；本仓库暂未声明许可证，请补充 LICENSE 文件。
