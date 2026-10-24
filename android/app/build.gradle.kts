plugins { id("com.android.application") version "8.3.2" }
android {
    namespace = "com.e7g.tikulocal"
    compileSdk = 35
    ndkVersion = "24.0.8215888"
    defaultConfig {
        applicationId = "com.e7g.tikulocal"
        minSdk = 26
        targetSdk = 35
        versionCode = 3
        versionName = "0.3.0"
        ndk { abiFilters += "arm64-v8a" }
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    sourceSets.getByName("main").jniLibs.srcDir("src/main/jniLibs")
    packaging { jniLibs { useLegacyPackaging = true } }
}
val rustRoot = rootProject.projectDir.parentFile
val buildRust by tasks.registering(Exec::class) {
    workingDir = rustRoot
    val sdkHome = System.getenv("ANDROID_HOME") ?: System.getenv("ANDROID_SDK_ROOT") ?: error("ANDROID_HOME required")
    environment("ANDROID_JAR", file("$sdkHome/platforms/android-35/android.jar").absolutePath)
    environment("ANDROID_NDK_HOME", file("$sdkHome/ndk/24.0.8215888").absolutePath)
    environment("ANDROID_NDK_ROOT", file("$sdkHome/ndk/24.0.8215888").absolutePath)
    val cargo = if (System.getProperty("os.name").lowercase().contains("windows")) "cargo.exe" else "cargo"
    commandLine(cargo, "ndk", "-t", "arm64-v8a", "-o", file("src/main/jniLibs").absolutePath, "build", "--lib", "--release")
    inputs.files(fileTree(rustRoot.resolve("src")) { include("**/*.rs") }, fileTree(rustRoot.resolve("ui")) { include("**/*.slint") }, rustRoot.resolve("build.rs"), rustRoot.resolve("Cargo.toml"), rustRoot.resolve("Cargo.lock"))
    outputs.file(file("src/main/jniLibs/arm64-v8a/libtikulocal.so"))
}
tasks.named("preBuild").configure { dependsOn(buildRust) }
