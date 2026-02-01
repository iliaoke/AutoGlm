plugins {
    alias(libs.plugins.android.application)
    alias(libs.plugins.kotlin.compose)
    id("com.chaquo.python")
}

android {
    packaging {
        jniLibs {
            // 强制将 .so 文件提取到磁盘上，而不是留在 APK 中
            // 这样 context.applicationInfo.nativeLibraryDir 目录下才会有真实文件
            useLegacyPackaging = true
        }
    }

    namespace = "com.example.autoglm"
    compileSdk {
        version = release(36)
    }

    defaultConfig {
        ndk {
            abiFilters += listOf("arm64-v8a")
        }
        applicationId = "com.example.autoglm"
        minSdk = 29
        targetSdk = 36
        versionCode = 1
        versionName = "1.0"

        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
    }

    buildTypes {
        release {
            isMinifyEnabled = false
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro"
            )
        }
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    buildFeatures {
        compose = true
    }
}

dependencies {
    implementation(libs.androidx.core.ktx)
    implementation(libs.androidx.lifecycle.runtime.ktx)
    implementation(libs.androidx.activity.compose)
    implementation(platform(libs.androidx.compose.bom))
    implementation(libs.androidx.compose.ui)
    implementation(libs.androidx.compose.ui.graphics)
    implementation(libs.androidx.compose.ui.tooling.preview)
    implementation(libs.androidx.compose.material3)
    testImplementation(libs.junit)
    androidTestImplementation(libs.androidx.junit)
    androidTestImplementation(libs.androidx.espresso.core)
    androidTestImplementation(platform(libs.androidx.compose.bom))
    androidTestImplementation(libs.androidx.compose.ui.test.junit4)
    debugImplementation(libs.androidx.compose.ui.tooling)
    debugImplementation(libs.androidx.compose.ui.test.manifest)
}
chaquopy {
    defaultConfig {
        pip {
            install( "openai==1.39.0")
            install("-r", "src/main/python/requirements.txt")
            install( "src/main/python/.")
            install("httpx==0.27.2")
        }
        buildPython("C:/Users/Administrator/AppData/Local/Programs/Python/Python313/python.exe")
        version = "3.13"
    }
}