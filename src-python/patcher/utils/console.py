import os
import ctypes
from patcher.constants import (
    VERSION, COLOR_RESET, COLOR_CYAN, COLOR_GREEN, COLOR_YELLOW, COLOR_RED,
    COLOR_BOLD, COLOR_DIM, COLOR_GRAY, COLOR_WHITE,
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


# Layout constants shared by banner, menu dividers, and summary panels.
# BANNER_INNER_WIDTH is the visible width inside a framed box.
# MENU_WIDTH is the matching outer menu width, including the frame columns.
BANNER_INNER_WIDTH = 47
MENU_WIDTH = BANNER_INNER_WIDTH + 2


def _visible_len(text):
    """Return visible text length without ANSI color escapes."""
    if "\x1b[" not in text:
        return len(text)
    out = []
    in_code = False
    for ch in text:
        if ch == "\x1b":
            in_code = True
            continue
        if in_code:
            if ch == "m":
                in_code = False
            continue
        out.append(ch)
    return len(out)


# Shared frame helpers for the banner and operation summary panels.
def _frame_border(left_ch, fill_ch, right_ch, accent=COLOR_CYAN):
    """Build a horizontal frame border."""
    return color(left_ch + fill_ch * BANNER_INNER_WIDTH + right_ch, accent, COLOR_BOLD)


def _frame_row(left, right="", accent=COLOR_CYAN):
    """Build a frame row with left text and optional right-aligned text."""
    left_str = "  " + left
    fill = BANNER_INNER_WIDTH - _visible_len(left_str) - _visible_len(right) - 1
    if fill < 1:
        fill = 1
    body = left_str + (" " * fill) + right + " "
    # Correct to exact visible width in case ANSI escapes skew the padding.
    vis = _visible_len(body)
    if vis < BANNER_INNER_WIDTH:
        body = left_str + (" " * (fill + BANNER_INNER_WIDTH - vis)) + right + " "
    elif vis > BANNER_INNER_WIDTH:
        while _visible_len(body) > BANNER_INNER_WIDTH:
            body = body[:-1]
    return color("║", accent, COLOR_BOLD) + body + color("║", accent, COLOR_BOLD)


def print_banner():
    title_left = color("Open AG Patcher", COLOR_BOLD)
    title_right = color(f"v{VERSION}", COLOR_GREEN, COLOR_BOLD)

    label_col = 12  # ширина колонки подписей (Telegram/YouTube) для ровной сетки
    telegram = color("Telegram".ljust(label_col), COLOR_YELLOW) + color("t.me/avencoresyt", COLOR_DIM)
    youtube = color("YouTube".ljust(label_col), COLOR_YELLOW) + color("youtube.com/@avencores", COLOR_DIM)

    print()
    print(f"  {_frame_border('╔', '═', '╗')}")
    print(f"  {_frame_row(title_left, title_right)}")
    print(f"  {_frame_row(color('Region bypass for Antigravity', COLOR_CYAN))}")
    print(f"  {_frame_row(color('Clean • No keys • No telemetry', COLOR_GREEN))}")
    print(f"  {_frame_border('╟', '─', '╢')}")
    print(f"  {_frame_row(telegram)}")
    print(f"  {_frame_row(youtube)}")
    print(f"  {_frame_border('╚', '═', '╝')}")
    print()


def print_panel(title, rows, accent=COLOR_GREEN):
    """Render a compact framed summary panel for operation results."""
    print()
    print(f"  {_frame_border('╔', '═', '╗', accent)}")
    print(f"  {_frame_row(color(title, COLOR_BOLD), accent=accent)}")
    print(f"  {_frame_border('╟', '─', '╢', accent)}")
    for label, value in rows:
        value = str(value)
        if "\x1b[" not in value:
            value = color(value, COLOR_CYAN)
        label_text = color(f"{label}:", COLOR_WHITE)
        print(f"  {_frame_row(label_text, value, accent=accent)}")
    print(f"  {_frame_border('╚', '═', '╝', accent)}")
    print()


# Shared marker helpers for all operation output.
def info(msg):
    """Neutral progress/status line."""
    print(f"  [*] {msg}")


def hint(msg):
    """Dim hint line."""
    print(color(f"  [i] {msg}", COLOR_DIM))


def ok(msg):
    """Green success line."""
    print(color(f"  [+] {msg}", COLOR_GREEN, COLOR_BOLD))


def warn(msg):
    """Yellow warning line."""
    print(color(f"  [!] {msg}", COLOR_YELLOW))


def err(msg):
    """Red error line."""
    print(color(f"  [!] {msg}", COLOR_RED))


def cancel(msg):
    """Dim cancellation line."""
    print(color(f"  [x] {msg}", COLOR_DIM))


def step(name, applied, detail=""):
    """Checklist row: green check, red cross, or dim neutral marker for skipped steps."""
    if applied is None:
        marker = color("•", COLOR_DIM)
    else:
        marker = color("✓", COLOR_GREEN) if applied else color("✗", COLOR_RED)
    line = f"  {marker} {name}"
    if detail:
        line += color(f" — {detail}", COLOR_DIM)
    print(line)


def _center_line(text, width=MENU_WIDTH):
    """Дополняет строку пробелами справа до полной ширины панели меню."""
    visible = _visible_len(text)
    if visible >= width:
        return text
    return text + " " * (width - visible)


# ─── Menu UI helpers ──────────────────────────────────────────────────────────
def print_menu_section(title):
    """Заголовок секции меню, обведённый тонкой линией.

    Пример:  ── PATCH ────────────────────────────────
    Ширина всей строки (включая ведущий ─) равна MENU_WIDTH,
    чтобы правый край совпадал с разделителями и рамкой баннера.
    """
    label = f" {title} "
    visible = len(label)
    dashes = "─" * max(1, MENU_WIDTH - visible - 1)  # -1 под ведущий «─»
    line = color("─", COLOR_GRAY) + color(label, COLOR_CYAN, COLOR_BOLD) + color(dashes, COLOR_GRAY)
    print(f"  {line}")


def print_menu_row(number, label, hint="", accent=COLOR_GREEN):
    """Строка пункта меню.

    Формат:    [1]  Apply Antigravity IDE patch      Apply / enable bypass
    number — строка-номер (может быть пустой для разделителей-подсказок).
    hint — короткое описание справа, рисуется приглушённым цветом.
    accent — цвет метки номера.
    """
    num_part = color(f"[{number}]", accent, COLOR_BOLD) if number != "" else color("  ", COLOR_GRAY)
    label_part = color(label, COLOR_WHITE)
    left = f"  {num_part}  {label_part}"
    if not hint:
        print(left)
        return

    left_visible = _visible_len(left)
    gap = max(2, MENU_WIDTH + 2 - left_visible - _visible_len(hint))
    print(f"{left}{' ' * gap}{color(hint, COLOR_DIM)}")


def print_menu_divider():
    """Тонкий горизонтальный разделитель."""
    print(f"  {color('─' * MENU_WIDTH, COLOR_GRAY)}")


def print_menu_footer(note=""):
    """Подвал под списком пунктов: тёмная линия и заметка."""
    print(f"  {color('─' * MENU_WIDTH, COLOR_GRAY)}")
    if note:
        print(f"  {color(note, COLOR_DIM)}")
