# Windows Android Build Skill

[中文文档](README.zh-CN.md)

Codex skill for running Android/Gradle builds in the Windows environment while Codex is running inside WSL.

Use this when the Android SDK, JDK, Gradle wrapper, emulator, or normal build environment lives on Windows, but Codex edits the project through Linux paths such as `/mnt/c/...`.

## Install

Recommended: ask Codex to install this skill from the repository URL:

```text
Install this Codex skill:
https://github.com/brainzouzou/windows-android-build
```

Codex should install the repository into its skills directory and load it in a new session.

Manual fallback:

```bash
mkdir -p ~/.codex/skills
git clone git@github.com:brainzouzou/windows-android-build.git ~/.codex/skills/windows-android-build
```

If you download the repository as a zip instead of cloning, make the script executable after extracting:

```bash
chmod +x ~/.codex/skills/windows-android-build/scripts/run_windows_gradle.py
```

Restart Codex or start a new session so the skill metadata is loaded.

## Requirements

- Codex running inside WSL.
- Windows interop enabled, so `cmd.exe` and `wslpath` are available from WSL.
- A Windows-side Android build environment already configured.
- A Gradle wrapper (`gradlew.bat`) or `gradle.bat` available for the project.

The skill intentionally uses the normal Windows Gradle home, `%USERPROFILE%\.gradle`, and avoids Linux-side Android SDK/JDK setup.

## Usage

After installation, you normally do not need to explicitly ask Codex to use this skill. It should trigger automatically for Android/Gradle build requests in WSL/Windows-mounted projects, for example:

```text
Build this Android project.
Run assembleDebug.
Run :app:compileDebugKotlin.
Verify this /mnt/c/... Android project with Windows Gradle.
```

The skill guides Codex to run the bundled bridge script, such as:

```bash
python3 ~/.codex/skills/windows-android-build/scripts/run_windows_gradle.py --project . assembleDebug --stacktrace
```

For narrower checks:

```bash
python3 ~/.codex/skills/windows-android-build/scripts/run_windows_gradle.py --project . testDebugUnitTest --stacktrace
python3 ~/.codex/skills/windows-android-build/scripts/run_windows_gradle.py --project . lintDebug --stacktrace
python3 ~/.codex/skills/windows-android-build/scripts/run_windows_gradle.py --project . :app:assembleDebug --stacktrace
```

## Script Options

```bash
python3 scripts/run_windows_gradle.py --project . :app:compileDebugKotlin --stacktrace
```

Useful options:

- `--pre-stop-count 0|1|2`: choose how many `gradle --stop` commands run before the build. Default is `1`.
- `--verbose`: stream full Gradle output to the terminal. By default output is compact.
- `--keep-log-on-success`: keep successful build logs under `.codex/windows-gradle`.
- `--timeout-seconds N`: kill the build after `N` seconds. Default is `1800`.
- `--allow-daemon`: do not append `--no-daemon`.

Full logs are written to `.codex/windows-gradle` while the build runs. Successful logs are removed by default; failed logs are kept and summarized.

## License

MIT
