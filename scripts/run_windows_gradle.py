#!/usr/bin/env python3
"""Run a Windows Gradle build from WSL and write a compact terminal summary."""

from __future__ import annotations

import argparse
import datetime as _dt
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
from typing import Iterable


ROOT_MARKERS = (
    "gradlew.bat",
    "settings.gradle",
    "settings.gradle.kts",
    "local.properties",
)

SUMMARY_PATTERNS = (
    re.compile(r"^\s*> Task .*FAILED"),
    re.compile(r"BUILD (SUCCESSFUL|FAILED)"),
    re.compile(r"^\s*(e:|error:|w:) "),
    re.compile(r"^\s*(FAILURE:|Caused by:|\* What went wrong:|\* Try:)"),
    re.compile(r"Execution failed for task"),
    re.compile(r"Compilation error"),
    re.compile(r"Exception"),
)

ERROR_PATTERNS = (
    re.compile(r"^\s*(e:|error:) "),
    re.compile(r"^\s*(FAILURE:|Caused by:|\* What went wrong:)"),
    re.compile(r"Execution failed for task"),
    re.compile(r"Compilation error"),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run Gradle in the Windows environment from a WSL/Linux path."
    )
    parser.add_argument(
        "--project",
        default=".",
        help="Project directory or any directory inside the Gradle project.",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=int,
        default=1800,
        help="Kill the build after this many seconds. Default: 1800.",
    )
    parser.add_argument(
        "--log-dir",
        default=None,
        help="Directory for logs. Default: <project-root>/.codex/windows-gradle.",
    )
    parser.add_argument(
        "--allow-daemon",
        action="store_true",
        help="Do not append --no-daemon automatically.",
    )
    parser.add_argument(
        "--pre-stop-count",
        type=int,
        default=1,
        choices=(0, 1, 2),
        help="How many Gradle --stop commands to run before the build. Default: 1.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Stream full Gradle output to the terminal. Logs always contain full output.",
    )
    parser.add_argument(
        "--keep-log-on-success",
        action="store_true",
        help="Keep the log file after a successful build. Failure logs are always kept.",
    )
    parser.add_argument(
        "gradle_args",
        nargs=argparse.REMAINDER,
        help="Gradle task and options, for example: assembleDebug --stacktrace.",
    )
    return parser.parse_args()


def find_project_root(start: Path) -> Path:
    current = start.resolve()
    if current.is_file():
        current = current.parent

    for candidate in (current, *current.parents):
        if any((candidate / marker).exists() for marker in ROOT_MARKERS):
            return candidate

    raise FileNotFoundError(
        f"No Gradle/Android project root found from {start}. "
        f"Expected one of: {', '.join(ROOT_MARKERS)}"
    )


def wsl_to_windows(path: Path) -> str:
    completed = subprocess.run(
        ["wslpath", "-w", str(path)],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return completed.stdout.strip()


def cmd_quote(value: str) -> str:
    return subprocess.list2cmdline([value])


def command_line(win_root: str, win_gradle: str, gradle_args: Iterable[str]) -> str:
    args = " ".join(cmd_quote(arg) for arg in gradle_args)
    env_setup = (
        'set "GRADLE_USER_HOME=%USERPROFILE%\\.gradle" '
        '&& set "GRADLE_OPTS=" '
        '&& set "CODEX_GRADLE_HOME=" '
        '&& set "CODEXGRADLEHOME="'
    )
    command = f"cd /d {cmd_quote(win_root)} && {env_setup} && {cmd_quote(win_gradle)}"
    if args:
        command += f" {args}"
    return command


def open_log(root: Path, log_dir: str | None) -> tuple[Path, object]:
    base = Path(log_dir).expanduser() if log_dir else root / ".codex" / "windows-gradle"
    base.mkdir(parents=True, exist_ok=True)
    stamp = _dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    log_path = base / f"gradle-{stamp}.log"
    return log_path, log_path.open("w", encoding="utf-8", errors="replace")


def should_print_summary(line: str) -> bool:
    return any(pattern.search(line) for pattern in SUMMARY_PATTERNS)


def extract_error_summary(log_path: Path, context: int = 3, limit: int = 80) -> list[str]:
    try:
        lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []

    selected: list[int] = []
    for index, line in enumerate(lines):
        if any(pattern.search(line) for pattern in ERROR_PATTERNS):
            start = max(0, index - context)
            end = min(len(lines), index + context + 1)
            selected.extend(range(start, end))

    if not selected:
        return []

    output: list[str] = []
    previous = -2
    for index in sorted(set(selected)):
        if len(output) >= limit:
            output.append("... error summary truncated ...")
            break
        if previous != -2 and index > previous + 1:
            output.append("...")
        output.append(lines[index])
        previous = index
    return output


def run_cmd(cmd: str, timeout_seconds: int, log_file: object, verbose: bool) -> int:
    try:
        process = subprocess.Popen(
            ["cmd.exe", "/d", "/s", "/c", cmd],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
        )
    except FileNotFoundError:
        print("[windows-android-build] cmd.exe not found; WSL interop is required.", file=sys.stderr)
        return 127

    assert process.stdout is not None
    try:
        for line in process.stdout:
            if verbose or should_print_summary(line):
                print(line, end="")
            log_file.write(line)
        return process.wait(timeout=timeout_seconds)
    except subprocess.TimeoutExpired:
        process.kill()
        message = f"\n[windows-android-build] timed out after {timeout_seconds} seconds\n"
        print(message, end="", file=sys.stderr)
        log_file.write(message)
        return 124


def main() -> int:
    args = parse_args()
    project_arg = Path(args.project).expanduser()
    root = find_project_root(project_arg)

    gradle_args = [arg for arg in args.gradle_args if arg != "--"]
    if not gradle_args:
        gradle_args = ["assembleDebug", "--stacktrace"]
    if not args.allow_daemon and "--no-daemon" not in gradle_args:
        gradle_args.append("--no-daemon")

    wrapper = root / "gradlew.bat"
    if wrapper.exists():
        win_gradle = wsl_to_windows(wrapper)
    else:
        win_gradle = "gradle.bat"

    win_root = wsl_to_windows(root)
    cmd = command_line(win_root, win_gradle, gradle_args)
    stop_cmds = [command_line(win_root, win_gradle, ["--stop"]) for _ in range(args.pre_stop_count)]
    log_path, log_file = open_log(root, args.log_dir)

    print(f"[windows-android-build] project: {root}")
    print(f"[windows-android-build] windows project: {win_root}")
    print(f"[windows-android-build] gradle args: {' '.join(gradle_args)}")
    print(f"[windows-android-build] pre-stop count: {len(stop_cmds)}")
    if args.verbose:
        for index, stop_cmd in enumerate(stop_cmds, start=1):
            print(f"[windows-android-build] pre-stop {index}: {stop_cmd}")
        print(f"[windows-android-build] command: {cmd}")
    print(f"[windows-android-build] log: {log_path}")
    print("")

    log_file.write(f"project: {root}\n")
    log_file.write(f"windows project: {win_root}\n")
    for index, stop_cmd in enumerate(stop_cmds, start=1):
        log_file.write(f"pre-stop {index}: {stop_cmd}\n")
    log_file.write(f"command: {cmd}\n\n")
    log_file.flush()

    try:
        for index, stop_cmd in enumerate(stop_cmds, start=1):
            print(f"[windows-android-build] running pre-stop {index}/{len(stop_cmds)}")
            log_file.write(f"[windows-android-build] running pre-stop {index}/{len(stop_cmds)}\n")
            stop_code = run_cmd(stop_cmd, args.timeout_seconds, log_file, args.verbose)
            print(f"[windows-android-build] pre-stop {index} exit code: {stop_code}")
            log_file.write(f"[windows-android-build] pre-stop {index} exit code: {stop_code}\n")
            log_file.flush()
            if stop_code in (124, 127):
                return_code = stop_code
                break
        else:
            print("[windows-android-build] running requested Gradle task")
            log_file.write("[windows-android-build] running requested Gradle task\n")
            return_code = run_cmd(cmd, args.timeout_seconds, log_file, args.verbose)
    finally:
        log_file.flush()
        log_file.close()

    print("")
    if return_code != 0:
        summary = extract_error_summary(log_path)
        if summary:
            print("[windows-android-build] key failure lines:")
            for line in summary:
                print(line)
            print("")
    print(f"[windows-android-build] exit code: {return_code}")
    print(f"[windows-android-build] log: {log_path}")
    if return_code == 0 and not args.keep_log_on_success and args.log_dir is None:
        try:
            shutil.rmtree(log_path.parent.parent)
            print("[windows-android-build] cleaned log directory after successful build")
        except OSError as exc:
            print(f"[windows-android-build] log cleanup failed: {exc}")
    return return_code


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except FileNotFoundError as exc:
        print(f"[windows-android-build] {exc}", file=sys.stderr)
        raise SystemExit(2)
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.strip() if exc.stderr else str(exc)
        print(f"[windows-android-build] path conversion failed: {stderr}", file=sys.stderr)
        raise SystemExit(exc.returncode or 1)
