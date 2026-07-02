# Windows Android Build Skill

这是一个 Codex skill，用于在 Codex 运行于 WSL 时，调用 Windows 环境里的 Gradle/Android 构建工具。

适用场景：项目代码在 `/mnt/c/...` 这类 Windows 挂载路径下，Android SDK、JDK、Gradle wrapper、模拟器或正常构建环境都配置在 Windows 侧。

## 安装

把仓库 clone 到 Codex skills 目录：

```bash
mkdir -p ~/.codex/skills
git clone git@github.com:brainzouzou/windows-android-build.git ~/.codex/skills/windows-android-build
```

如果你是下载 zip 后解压，需要确认脚本有可执行权限：

```bash
chmod +x ~/.codex/skills/windows-android-build/scripts/run_windows_gradle.py
```

安装后重启 Codex，或者开启新的 Codex 会话，让 skill 元数据重新加载。

## 环境要求

- Codex 运行在 WSL 内。
- WSL interop 可用，也就是能在 WSL 里调用 `cmd.exe` 和 `wslpath`。
- Windows 侧已经配置好 Android 构建环境。
- 项目中有 `gradlew.bat`，或者系统 PATH 中有 `gradle.bat`。

这个 skill 会使用 Windows 默认 Gradle Home：`%USERPROFILE%\.gradle`，不会要求在 WSL 里安装 Android SDK/JDK。

## 使用方式

在 Android 项目目录下，让 Codex 使用这个 skill 进行构建验证。脚本调用形式如下：

```bash
python3 ~/.codex/skills/windows-android-build/scripts/run_windows_gradle.py --project . assembleDebug --stacktrace
```

常见的窄范围检查：

```bash
python3 ~/.codex/skills/windows-android-build/scripts/run_windows_gradle.py --project . testDebugUnitTest --stacktrace
python3 ~/.codex/skills/windows-android-build/scripts/run_windows_gradle.py --project . lintDebug --stacktrace
python3 ~/.codex/skills/windows-android-build/scripts/run_windows_gradle.py --project . :app:assembleDebug --stacktrace
```

## 脚本参数

```bash
python3 scripts/run_windows_gradle.py --project . :app:compileDebugKotlin --stacktrace
```

常用参数：

- `--pre-stop-count 0|1|2`：构建前执行几次 `gradle --stop`，默认是 `1`。
- `--verbose`：输出完整 Gradle 日志。默认只输出精简摘要。
- `--keep-log-on-success`：成功时保留 `.codex/windows-gradle` 下的日志。
- `--timeout-seconds N`：构建超时时间，默认 `1800` 秒。
- `--allow-daemon`：不自动追加 `--no-daemon`。

脚本运行时会把完整日志写到 `.codex/windows-gradle`。默认情况下，成功日志会自动清理；失败日志会保留，并在终端输出关键错误摘要。

## 说明

- 推荐优先跑最小相关 Gradle task，避免无意义的全量构建。
- 如果精简输出不足以定位问题，可以加 `--verbose`，或者查看失败时保留的完整日志路径。
- 如果遇到 Windows 文件锁或 Gradle daemon 占用问题，可以把 `--pre-stop-count` 调整为 `2`。
- 如果只改文档或非 Android 构建相关文件，通常不需要运行 Gradle。

## License

MIT
