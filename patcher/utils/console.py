import os
import ctypes
from patcher.constants import (
    VERSION, COLOR_RESET, COLOR_CYAN, COLOR_GREEN, COLOR_YELLOW, COLOR_BOLD
)

USE_COLOR = False


def enable_ansi():
    if os.name != "nt":
        return True
    try:
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.GetStdHandle(-11)  # STD_OUTPUT_HANDLE
        mode = ctypes.c_uint32()
        if not kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
            return False
        new_mode = mode.value | 0x0004  # ENABLE_VIRTUAL_TERMINAL_PROCESSING
        if new_mode == mode.value:
            return True
        return bool(kernel32.SetConsoleMode(handle, new_mode))
    except Exception:
        return False


def setup_console():
    global USE_COLOR
    if os.name == "nt":
        os.system("chcp 65001 >nul")
    USE_COLOR = enable_ansi()


def color(text, *styles):
    if not USE_COLOR or not styles:
        return text
    return "".join(styles) + text + COLOR_RESET


def clear_screen():
    os.system("cls" if os.name == "nt" else "clear")


def print_banner():
    print()
    print(color("  ╔═══════════════════════════════════════════════╗", COLOR_CYAN, COLOR_BOLD))
    print(
        color("  ║  ", COLOR_CYAN, COLOR_BOLD)
        + color("Open AG Patcher", COLOR_BOLD)
        + color(" v", COLOR_CYAN)
        + color(VERSION, COLOR_GREEN, COLOR_BOLD)
        + color("                       ║", COLOR_CYAN, COLOR_BOLD)
    )
    print(
        color("  ║  ", COLOR_CYAN, COLOR_BOLD)
        + color("Region bypass for Antigravity", COLOR_CYAN)
        + color("                ║", COLOR_CYAN, COLOR_BOLD)
    )
    print(
        color("  ║  ", COLOR_CYAN, COLOR_BOLD)
        + color("Clean", COLOR_GREEN)
        + color(" • ", COLOR_CYAN)
        + color("No keys", COLOR_GREEN)
        + color(" • ", COLOR_CYAN)
        + color("No telemetry", COLOR_GREEN)
        + color("               ║", COLOR_CYAN, COLOR_BOLD)
    )
    print(
        color("  ║  ", COLOR_CYAN, COLOR_BOLD)
        + color("Telegram Channel: ", COLOR_YELLOW)
        + color("t.me/avencoresyt", COLOR_GREEN)
        + color("           ║", COLOR_CYAN, COLOR_BOLD)
    )
    print(
        color("  ║  ", COLOR_CYAN, COLOR_BOLD)
        + color("YouTube Channel:  ", COLOR_YELLOW)
        + color("youtube.com/@avencores", COLOR_GREEN)
        + color("     ║", COLOR_CYAN, COLOR_BOLD)
    )
    print(color("  ╚═══════════════════════════════════════════════╝", COLOR_CYAN, COLOR_BOLD))
    print()
