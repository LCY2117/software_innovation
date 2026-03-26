# LifeReflexArc Android

## Environment Config
- Copy `env.example.properties` to `env.properties` for project-specific API and WebSocket addresses.
- `demoLocal` is intended for local demo use and defaults to `10.0.2.2:8080`.
- `release` is intended for distributable APKs and reads the `RELEASE_*` values from `env.properties`.
- Copy `keystore.example.properties` to `keystore.properties` to enable custom release signing. If missing, `release` falls back to the debug keystore for local packaging only.

## Preview How-To
- Open any screen file under `app/src/main/java/com/flag/lifereflexarc/ui/screens/`
- Use the `@Preview` at the bottom of each screen file
- Android Studio: Split or Design tab to render

Current screen previews:
- `SosCountdownScreen`
- `EmergencyAlertScreen`
- `PrimeNavigationScreen`
- `CprMetronomeScreen`
- `RunnerIdleScreen`
- `AedDeliveryScreen`
- `GuideIdleScreen`
- `GuideTaskScreen`
- `HandoverArchiveScreen`

## Run
- Android Studio: Run `app`
- Gradle demo build: `.\gradlew.bat assembleDemoLocal`
- Gradle release APK: `.\gradlew.bat assembleRelease`
- APK output directory: `app/build/outputs/apk/`

## Packaging Notes
- Demo and release API / WebSocket endpoints are centralized in `env.properties` via `BuildConfig -> AppConfig`; do not hardcode hostnames in Kotlin business code.
- If the local environment cannot download Android artifacts from `dl.google.com`, use the installed SDK `aapt2.exe` to finish packaging:
  - `.\gradlew.bat assembleDemoLocal "-Pandroid.aapt2FromMavenOverride=C:\Users\<you>\AppData\Local\Android\Sdk\build-tools\36.0.0\aapt2.exe"`
  - `.\gradlew.bat assembleRelease "-Pandroid.aapt2FromMavenOverride=C:\Users\<you>\AppData\Local\Android\Sdk\build-tools\36.0.0\aapt2.exe"`
- `assembleRelease` is configured to package even when release lint dependencies cannot be resolved in restricted networks.
- The Android subproject folder is now ASCII-only (`lifereflexarc-app`), so no path-check override is needed anymore.
