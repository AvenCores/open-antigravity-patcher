import os
import ctypes
from patcher.constants import (
    VERSION, COLOR_RESET, COLOR_CYAN, COLOR_GREEN, COLOR_YELLOW, COLOR_BOLD,
    COLOR_DIM, COLOR_GRAY, COLOR_WHITE, COLOR_MAGENTA,
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
    # Внутренняя ширина баннера (между левой и правой рамками).
    # Паддинг считается автоматически, поэтому правая граница остаётся ровной
    # при любой длине названия или версии.
    width = 47

    def row(left, right=""):
        """Собирает строку баннера с точной видимой шириной `width`.

        left/right — уже окрашенные фрагменты. left прижимается влево (отступ 2),
        right — вправо (отступ 1 от правой рамки). При отсутствии right строка
        просто добивается пробелами до нужной ширины.
        """
        left_str = "  " + left
        right_str = right
        fill = width - _visible_len(left_str) - _visible_len(right_str) - 1
        if fill < 1:
            fill = 1
        body = left_str + (" " * fill) + right_str + " "
        # Корректируем до точной ширины на случай ошибок округления/ANSI.
        vis = _visible_len(body)
        if vis < width:
            body = left_str + (" " * (fill + width - vis)) + right_str + " "
        elif vis > width:
            while _visible_len(body) > width:
                body = body[:-1]
        return (
            color("║", COLOR_CYAN, COLOR_BOLD)
            + body
            + color("║", COLOR_CYAN, COLOR_BOLD)
        )

    def border(left_ch, fill_ch, right_ch):
        return color(left_ch + fill_ch * width + right_ch, COLOR_CYAN, COLOR_BOLD)

    title_left = color("Open AG Patcher", COLOR_BOLD)
    title_right = color(f"v{VERSION}", COLOR_GREEN, COLOR_BOLD)

    label_col = 12  # ширина колонки подписей (Telegram/YouTube) для ровной сетки
    telegram = color("Telegram".ljust(label_col), COLOR_YELLOW) + color("t.me/avencoresyt", COLOR_DIM)
    youtube = color("YouTube".ljust(label_col), COLOR_YELLOW) + color("youtube.com/@avencores", COLOR_DIM)

    print()
    print(f"  {border('╔', '═', '╗')}")
    print(f"  {row(title_left, title_right)}")
    print(f"  {row(color('Region bypass for Antigravity', COLOR_CYAN))}")
    print(f"  {row(color('Clean • No keys • No telemetry', COLOR_GREEN))}")
    print(f"  {border('╟', '─', '╢')}")
    print(f"  {row(telegram)}")
    print(f"  {row(youtube)}")
    print(f"  {border('╚', '═', '╝')}")
    print()


# ─── Menu UI helpers ──────────────────────────────────────────────────────────
# Ширина панели меню подбирается под внешнюю ширину баннера (49 символов),
# чтобы правый край разделителей меню совпадал с правой рамкой баннера.
MENU_WIDTH = 49


def _center_line(text, width=MENU_WIDTH):
    """Дополняет строку пробелами справа до полной ширины панели меню."""
    visible = _visible_len(text)
    if visible >= width:
        return text
    return text + " " * (width - visible)


def _visible_len(text):
    """Длина строки без ANSI-кодов (для выравнивания по ширине)."""
    if "\x1b[" not in text:
        return len(text)
    out = []
    i = 0
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
