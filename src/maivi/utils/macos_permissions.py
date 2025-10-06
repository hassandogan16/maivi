"""Helpers for handling macOS accessibility and input monitoring permissions."""

from __future__ import annotations

import ctypes
import platform
import subprocess
import time
from typing import Optional

_CF_STRING_ENCODING_UTF8 = 0x08000100
_APPLICATION_SERVICES = "/System/Library/Frameworks/ApplicationServices.framework/ApplicationServices"
_CORE_FOUNDATION = "/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation"


def _is_macos() -> bool:
    """Return True when running on macOS."""
    return platform.system() == "Darwin"


def _load_framework(path: str) -> Optional[ctypes.CDLL]:
    """Safely load a macOS framework, returning None on failure."""
    try:
        return ctypes.cdll.LoadLibrary(path)
    except OSError:
        return None


def _check_accessibility(quartz: ctypes.CDLL) -> Optional[bool]:
    """Check whether the current process is trusted for accessibility."""
    try:
        quartz.AXIsProcessTrusted.restype = ctypes.c_bool
        quartz.AXIsProcessTrusted.argtypes = []
    except AttributeError:
        return None

    try:
        return bool(quartz.AXIsProcessTrusted())
    except OSError:
        return None


def _prompt_accessibility(quartz: ctypes.CDLL) -> bool:
    """Request accessibility permission via the system prompt."""
    try:
        prompt_fn = quartz.AXIsProcessTrustedWithOptions
    except AttributeError:
        return False

    core_foundation = _load_framework(_CORE_FOUNDATION)
    if core_foundation is None:
        return False

    core_foundation.CFStringCreateWithCString.restype = ctypes.c_void_p
    core_foundation.CFStringCreateWithCString.argtypes = [
        ctypes.c_void_p,
        ctypes.c_char_p,
        ctypes.c_uint32,
    ]

    key = core_foundation.CFStringCreateWithCString(
        None,
        b"AXTrustedCheckOptionPrompt",
        _CF_STRING_ENCODING_UTF8,
    )
    if not key:
        return False

    try:
        kCFBooleanTrue = ctypes.c_void_p.in_dll(core_foundation, "kCFBooleanTrue")
    except ValueError:
        core_foundation.CFRelease(key)
        return False

    keys = (ctypes.c_void_p * 1)(key)
    values = (ctypes.c_void_p * 1)(kCFBooleanTrue.value)

    core_foundation.CFDictionaryCreate.restype = ctypes.c_void_p
    core_foundation.CFDictionaryCreate.argtypes = [
        ctypes.c_void_p,
        ctypes.POINTER(ctypes.c_void_p),
        ctypes.POINTER(ctypes.c_void_p),
        ctypes.c_long,
        ctypes.c_void_p,
        ctypes.c_void_p,
    ]

    options = core_foundation.CFDictionaryCreate(None, keys, values, 1, None, None)
    if not options:
        core_foundation.CFRelease(key)
        return False

    prompt_fn.restype = ctypes.c_bool
    prompt_fn.argtypes = [ctypes.c_void_p]

    try:
        result = bool(prompt_fn(options))
    except OSError:
        result = False

    core_foundation.CFRelease(options)
    core_foundation.CFRelease(key)
    return result


def ensure_accessibility_permissions(prompt: bool = False, retry_delay: float = 0.5) -> bool:
    """Check (and optionally prompt for) macOS accessibility permission.

    Returns True when accessibility monitoring is already permitted or when the
    prompt succeeds. On non-macOS platforms this always returns True.
    """

    if not _is_macos():
        return True

    quartz = _load_framework(_APPLICATION_SERVICES)
    if quartz is None:
        # If we cannot load the framework, err on the side of not blocking
        return True

    trusted = _check_accessibility(quartz)
    if trusted:
        return True

    if prompt:
        try:
            _prompt_accessibility(quartz)
        except Exception:
            # Never allow an unexpected failure to bubble up to the caller
            pass
        time.sleep(max(retry_delay, 0.0))
        trusted = _check_accessibility(quartz)

    return bool(trusted)


def open_system_settings_privacy(anchor: str) -> bool:
    """Best-effort helper to open System Settings to a specific privacy pane."""

    if not _is_macos() or not anchor:
        return False

    script = f'''
    tell application "System Settings"
        activate
        try
            reveal anchor "{anchor}" of pane id "com.apple.preference.security"
        end try
    end tell
    '''

    try:
        subprocess.run(
            ["osascript", "-e", script],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return True
    except FileNotFoundError:
        return False
    except Exception:
        return False


__all__ = [
    "ensure_accessibility_permissions",
    "open_system_settings_privacy",
]
