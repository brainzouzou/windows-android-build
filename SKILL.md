---
name: windows-android-build
description: Run Android/Gradle builds in the Windows environment from Codex running under Linux/WSL. Use when the project source, Android SDK, JDK, Gradle wrapper, emulator, or build/runtime environment lives on Windows but Codex edits files from Linux paths such as /mnt/c; especially for Android tasks that require compiling, running Gradle tasks, checking assemble/test/lint output, or iterating on build errors that cannot be reproduced inside Linux.
---

# Windows Android Build

## Overview

Use this skill when Codex must verify an Android project whose working build environment is Windows, while Codex itself is running in Linux/WSL. Prefer the bundled script over manually composing `cmd.exe` calls.

Do not create, recommend, set, or fall back to `.codexgradlehome` for these builds. Windows Android builds should use the normal Windows Gradle user home, `%USERPROFILE%\.gradle`, unless the user explicitly asks for a different Gradle home. If an inherited environment points Gradle at `.codexgradlehome`, clear it before running Gradle.

## Workflow

1. Confirm the workspace is a Windows-mounted project path, typically `/mnt/c/...`, and locate the Android/Gradle root by looking for `gradlew.bat`, `settings.gradle`, `settings.gradle.kts`, or `local.properties`.
2. After editing code, run the Windows build from the project root. The bundled script must be used so it can release stale Gradle daemons, force Gradle to use the normal Windows Gradle home instead of `.codexgradlehome`, and keep terminal output compact:

```bash
python3 scripts/run_windows_gradle.py --project . assembleDebug --stacktrace
```

3. For common verification tasks, use the project's normal Gradle task names:

```bash
python3 scripts/run_windows_gradle.py --project . testDebugUnitTest --stacktrace
python3 scripts/run_windows_gradle.py --project . lintDebug --stacktrace
python3 scripts/run_windows_gradle.py --project . :app:assembleDebug --stacktrace
```

4. Read the compact command output. On failure, the script prints key failure lines and keeps the full log file path. Fix failures, then rerun the smallest relevant task.
5. Report the exact task, exit code, and key failure lines to the user. Do not claim the Android build passed unless the Windows Gradle command exited with code 0.

## Script Behavior

`scripts/run_windows_gradle.py`:

- Converts the Linux project path to a Windows path with `wslpath -w`.
- Runs `gradlew.bat` when present; otherwise falls back to `gradle.bat`.
- Executes through `cmd.exe` so Windows-side JDK, Android SDK, Gradle, and PATH configuration are used.
- Before the requested task, runs the selected Windows Gradle command with `--stop` once from the project root to release stale or occupied Gradle daemons. Pass `--pre-stop-count 0` to skip this, or `--pre-stop-count 2` for stubborn daemon/file-lock issues.
- Forces `GRADLE_USER_HOME` to `%USERPROFILE%\.gradle` and clears `GRADLE_OPTS`, `CODEX_GRADLE_HOME`, and `CODEXGRADLEHOME` for the Windows command, so builds do not use `.codexgradlehome`.
- Writes full combined stdout/stderr to `.codex/windows-gradle/`, while printing only compact summary lines by default. The default terminal output omits the long Windows command and normal `> Task ...` progress lines. Pass `--verbose` to stream full output and command details to Codex.
- On failure, extracts key error lines from the full log and prints them after the Gradle command exits.
- On success, removes the generated `.codex/windows-gradle` log directory by default when using the default log location. Pass `--keep-log-on-success` to keep successful build logs.
- Adds `--no-daemon` by default to avoid leaving Gradle daemons attached to the Codex session. Pass `--allow-daemon` if daemon behavior is required.

## Gradle Home Policy

- Do not use `.codexgradlehome` for Windows Android builds.
- Do not pass `-Dgradle.user.home=.codexgradlehome`.
- Do not set `GRADLE_USER_HOME` to `.codexgradlehome`.
- Do not troubleshoot Windows Gradle failures by switching to `.codexgradlehome`; keep `%USERPROFILE%\.gradle` and fix the actual Windows Gradle/JDK/Android SDK issue.

## Failure Handling

- If `cmd.exe` or `wslpath` is missing, explain that the skill requires WSL interop on a Windows host.
- If no Gradle root is found, search from the repository root and pass `--project <path-to-android-project>`.
- If Windows reports missing SDK/JDK/Gradle, treat it as a Windows environment issue; do not try to install Linux Android tooling unless the user explicitly asks.
- If a build times out, rerun with a narrower task or a larger `--timeout-seconds` value only when the previous output shows real progress.
- If the compact output is insufficient for debugging, rerun with `--verbose` or inspect the full log path printed for failed builds.
- If a pre-stop reports a transient Windows file-lock error but the requested Gradle task exits with code 0, treat the build as successful and mention the pre-stop warning only when it is relevant.
