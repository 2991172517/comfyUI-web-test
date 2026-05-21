"""在资源管理器中打开 ComfyUI models 子目录（需本机后端，浏览器无法直接打开本地路径）。"""
from __future__ import annotations

import logging
import os
import platform
import subprocess
import time
from pathlib import Path

from model_preview_service import VALID_FOLDERS, models_folder_dir

log = logging.getLogger("custom_project.model_folder")

_EXPLORER_WINDOW_CLASSES = frozenset({"CabinetWClass", "ExploreWClass"})


def resolve_model_folder(folder: str) -> Path:
    path = models_folder_dir(folder).resolve()
    path.mkdir(parents=True, exist_ok=True)
    return path


def list_folder_paths() -> dict[str, str]:
    return {name: str(resolve_model_folder(name)) for name in sorted(VALID_FOLDERS)}


def _win_bring_to_front(hwnd: int) -> bool:
    import ctypes

    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32

    if not hwnd or not user32.IsWindow(hwnd):
        return False

    user32.ShowWindow(hwnd, 9)  # SW_RESTORE
    user32.BringWindowToTop(hwnd)

    fg = user32.GetForegroundWindow()
    if fg == hwnd:
        return True

    fg_thread = user32.GetWindowThreadProcessId(fg, None)
    cur_thread = kernel32.GetCurrentThreadId()
    attached = False
    try:
        if fg_thread and fg_thread != cur_thread:
            attached = bool(user32.AttachThreadInput(cur_thread, fg_thread, True))
        ok = bool(user32.SetForegroundWindow(hwnd))
        if not ok:
            # 任务栏闪烁，提示用户切换
            class FLASHWINFO(ctypes.Structure):
                _fields_ = [
                    ("cbSize", ctypes.c_uint),
                    ("hwnd", ctypes.c_void_p),
                    ("dwFlags", ctypes.c_uint),
                    ("uCount", ctypes.c_uint),
                    ("dwTimeout", ctypes.c_uint),
                ]

            fi = FLASHWINFO()
            fi.cbSize = ctypes.sizeof(FLASHWINFO)
            fi.hwnd = hwnd
            fi.dwFlags = 3  # FLASHW_ALL
            fi.uCount = 3
            user32.FlashWindowEx(ctypes.byref(fi))
        return ok
    finally:
        if attached:
            user32.AttachThreadInput(cur_thread, fg_thread, False)


def _win_list_explorer_hwnds() -> list[int]:
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.windll.user32
    hwnds: list[int] = []

    def enum_cb(hwnd, _):
        if not user32.IsWindowVisible(hwnd):
            return True
        cls = ctypes.create_unicode_buffer(256)
        user32.GetClassNameW(hwnd, cls, 256)
        if cls.value in _EXPLORER_WINDOW_CLASSES:
            hwnds.append(int(hwnd))
        return True

    WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    user32.EnumWindows(WNDENUMPROC(enum_cb), 0)
    return hwnds


def _win_find_explorer_hwnd(folder_path: str, before: set[int]) -> int | None:
    import ctypes

    folder_path = os.path.normpath(folder_path)
    folder_name = os.path.basename(folder_path.rstrip("\\/")).lower()
    after = _win_list_explorer_hwnds()
    new_hwnds = [h for h in after if h not in before]

    user32 = ctypes.windll.user32

    def title_matches(hwnd: int) -> bool:
        length = user32.GetWindowTextLengthW(hwnd) + 1
        if length <= 1:
            return False
        buf = ctypes.create_unicode_buffer(length)
        user32.GetWindowTextW(hwnd, buf, length)
        title = buf.value.lower()
        return folder_name in title or folder_path.lower() in title

    for hwnd in new_hwnds:
        if title_matches(hwnd):
            return hwnd

    for hwnd in reversed(after):
        if title_matches(hwnd):
            return hwnd

    return new_hwnds[-1] if new_hwnds else (after[-1] if after else None)


def _open_folder_windows(path: Path) -> str:
    import ctypes

    norm = os.path.normpath(str(path))
    user32 = ctypes.windll.user32
    shell32 = ctypes.windll.shell32

    before = set(_win_list_explorer_hwnds())

    # 允许本进程尝试将新窗口带到前台（从浏览器触发的 API 场景）
    user32.AllowSetForegroundWindow(0xFFFFFFFF)

    ret = shell32.ShellExecuteW(None, "explore", norm, None, None, 1)
    if ret <= 32:
        raise OSError(f"ShellExecuteW failed ({ret})")

    time.sleep(0.6)
    hwnd = _win_find_explorer_hwnd(norm, before)
    if hwnd and _win_bring_to_front(hwnd):
        return "explorer+foreground"

    if hwnd:
        _win_bring_to_front(hwnd)
        return "explorer+flash"

    # 回退：cmd start 有时能抢到前台
    subprocess.run(
        ["cmd", "/c", "start", "", "explorer", norm],
        check=False,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    time.sleep(0.5)
    hwnd2 = _win_find_explorer_hwnd(norm, before)
    if hwnd2:
        _win_bring_to_front(hwnd2)
    return "explorer+start"


def open_in_file_manager(folder: str) -> dict:
    if folder not in VALID_FOLDERS:
        raise ValueError(f"不支持的目录: {folder}")

    path = resolve_model_folder(folder)
    system = platform.system()
    method: str | None = None
    error: str | None = None

    try:
        if system == "Windows":
            method = _open_folder_windows(path)
        elif system == "Darwin":
            subprocess.run(["open", str(path)], check=True)
            method = "open"
        else:
            subprocess.run(["xdg-open", str(path)], check=True)
            method = "xdg-open"
    except Exception as e:
        error = str(e)
        log.warning("open folder failed folder=%s path=%s err=%s", folder, path, e)

    return {
        "ok": error is None,
        "folder": folder,
        "path": str(path),
        "opened": error is None,
        "method": method,
        "platform": system,
        "error": error,
        "hint": "已通过本机后端调用系统文件管理器；纯远程部署时请手动复制路径打开。",
    }
