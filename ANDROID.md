# TikuLocal Android

Android builds use the **same Rust question-bank engine** as the Windows/Linux/macOS edition. The touch UI in `ui/mobile.slint` is compiled with Slint's official Material style.

## Features

- ARM64 native Android app (Android 8.0 / API 26 or newer).
- Search the offline SQLite question bank, manage entries, and import DOCX/JSON.
- Android Storage Access Framework file picker: multi-select supported; selected documents are copied into the app's private directory.
- Android system Save As picker for JSON export (no broad storage permissions).
- Same `127.0.0.1:8060/adapter-service/search` local API on the device. Only the INTERNET permission is requested.
- Material light/dark/system theme support and a mobile single-column layout.

## Build Android APK

Install Android Studio, SDK Platform 35, Android SDK Build Tools 35, NDK **24.0.8215888**, Java 17 or later, and Rust. In addition:

```sh
rustup target add aarch64-linux-android
cargo install cargo-ndk --locked
cd android
./gradlew :app:assembleDebug
```

The built debug-signed APK is `android/app/build/outputs/apk/debug/app-debug.apk`. It contains the release-optimized Rust library. **Preview signing note:** Debug APKs built on different CI runners may have different signing keys. If an update fails with `INSTALL_FAILED_UPDATE_INCOMPATIBLE`, export your answers to JSON first, uninstall the previous preview, then install the new one. Production upgrades should use a stable private release-signing key. To install when a device is connected:

```sh
adb install -r android/app/build/outputs/apk/debug/app-debug.apk
adb shell am start -n com.e7g.tikulocal/.TikuActivity
```

For Windows use `android\gradlew.bat :app:assembleDebug`. Set `ANDROID_HOME` to the Android SDK root. The Gradle build will resolve the SDK platform and NDK paths.

The GitHub Action `Rust release` builds a preview APK (`tikulocal-android-arm64.apk`) and attaches it to tagged GitHub releases.

## Design / privacy

The Android UI is separate from the desktop layout to avoid multi-column tables on narrow screens. The Rust model, imports, search, database and API remain shared. Documents are imported by the user through Android's system picker. No media storage, accessibility, or all-files permission is needed.

Android APK compilation and package structure can be verified without a connected device, but **installation, touch interaction, document picker callbacks, and real-device performance still require a connected device or running Android emulator**.

## Details

- Package: `com.e7g.tikulocal`
- Native library: `lib/arm64-v8a/libtikulocal.so`
- Entrypoint: `com.e7g.tikulocal.TikuActivity` (NativeActivity)
- Rust entry: `src/lib.rs::android_main`
- SAF/JNI bridge: `android/app/src/main/java/com/e7g/tikulocal/TikuActivity.java` and `src/android.rs`
