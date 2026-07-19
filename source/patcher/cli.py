import os
import sys
import webbrowser
import locale

from patcher.constants import (
    COLOR_CYAN,
    COLOR_GREEN,
    COLOR_YELLOW,
    COLOR_RED,
    COLOR_BOLD,
)
from patcher.utils.console import (
    color,
    clear_screen,
    print_banner,
    print_menu_section,
    print_menu_row,
    print_menu_footer,
    info,
    hint,
    ok,
    warn,
    err,
    cancel,
)
from patcher.utils.file import file_size, format_bytes

from patcher.ide.discovery import (
    find_install_root,
    find_main_js,
    get_ag_version,
    resolve_target_path,
)
from patcher.ide.patcher import is_already_patched, do_patch, do_restore, do_fix_429
from patcher.agy.discovery import find_agy_binary, resolve_agy_path
from patcher.agy.patcher import is_already_patched as is_agy_patched, do_patch_agy, do_restore_agy

from patcher.manager.discovery import find_manager_binary, resolve_manager_path, get_antigravity_version
from patcher.manager.patcher import is_already_patched as is_mgr_patched, do_patch_manager, do_restore_manager


def pause():
    input("  Press Enter to return to menu...")


def print_launch_examples():
    script_name = os.path.basename(sys.argv[0]) or "main.py"
    cmd = script_name if getattr(sys, "frozen", False) else f"python {script_name}"
    windows_example = f'{cmd} "C:\\Path\\To\\Antigravity IDE"'
    macos_example = f'{cmd} "/Applications/Antigravity IDE.app"'
    linux_example = f'{cmd} "/usr/share/antigravity-ide"'

    hint("Usage examples with custom path:")
    print(f"      Windows: {color(windows_example, COLOR_YELLOW)}")
    print(f"      macOS:   {color(macos_example, COLOR_YELLOW)}")
    print(f"      Linux:   {color(linux_example, COLOR_YELLOW)}")


def print_path_examples():
    windows_path = r"C:\Users\Name\AppData\Local\Programs\Antigravity IDE"
    macos_path = "/Applications/Antigravity IDE.app"
    linux_path = "/usr/share/antigravity-ide"

    hint("Path examples:")
    print(f"      Windows: {color(windows_path, COLOR_YELLOW)}")
    print(f"      macOS:   {color(macos_path, COLOR_YELLOW)}")
    print(f"      Linux:   {color(linux_path, COLOR_YELLOW)}")


def _read_console_line(prompt):
    print(prompt, end="", flush=True)

    stdin_buffer = getattr(sys.stdin, "buffer", None)
    if stdin_buffer is None:
        return sys.stdin.readline().rstrip("\r\n")

    raw = stdin_buffer.readline()
    if not raw:
        return ""

    encodings = [
        sys.stdin.encoding,
        locale.getpreferredencoding(False),
        "utf-8",
        "cp1251",
        "latin-1",
    ]
    for encoding in [e for e in encodings if e]:
        try:
            return raw.decode(encoding).rstrip("\r\n")
        except UnicodeDecodeError:
            pass

    return raw.decode("utf-8", errors="replace").rstrip("\r\n")


def prompt_yn(question):
    question = question.rstrip()
    prompt = f"  [?] {question} ({color('y', COLOR_GREEN)}/{color('n', COLOR_RED)}): "
    return _read_console_line(prompt).strip().lower()


def confirmed(question):
    """Возвращает True, если пользователь ответил 'y'."""
    return prompt_yn(question) in ("y", "yes", "\u0434", "\u0434\u0430")


def _kv(label, value_text, value_color):
    """Отформатированная пара ключ/значение с выравниванием меток."""
    print(f"      {label:<9}{color(value_text, value_color)}")


def print_target_info(main_js_path, manager_path="", agy_path="", show_search_line=False):
    if show_search_line:
        info("Searching for installations...")

    # 1. Antigravity IDE Info
    print_menu_section("ANTIGRAVITY IDE")
    _kv("Target:", main_js_path if main_js_path else "Not found", COLOR_CYAN)
    if main_js_path and os.path.exists(main_js_path):
        try:
            with open(main_js_path, "r", encoding="utf-8") as f:
                content = f.read()
            _kv("Status:", "found", COLOR_GREEN)
            patched = is_already_patched(content)
            _kv("Patch:", "already patched" if patched else "not patched",
                COLOR_YELLOW if patched else COLOR_GREEN)
        except Exception:
            _kv("Status:", "unreadable", COLOR_RED)
            _kv("Patch:", "unreadable", COLOR_RED)

        ver_str, _ = get_ag_version(main_js_path)
        _kv("Version:", ver_str if ver_str else "not detected",
            COLOR_GREEN if ver_str else COLOR_YELLOW)

        size = file_size(main_js_path)
        _kv("Size:", format_bytes(size), COLOR_GREEN if size > 0 else COLOR_YELLOW)
    else:
        _kv("Status:", "not found", COLOR_RED)

    print()

    # 2. Antigravity 2.0 Info
    print_menu_section("ANTIGRAVITY 2.0")
    _kv("Target:", manager_path if manager_path else "Not found", COLOR_CYAN)
    if manager_path and os.path.isfile(manager_path):
        _kv("Status:", "found", COLOR_GREEN)
        patched = is_mgr_patched(manager_path)
        _kv("Patch:", "already patched" if patched else "not patched",
            COLOR_YELLOW if patched else COLOR_GREEN)
        
        ver_str = get_antigravity_version(manager_path)
        _kv("Version:", ver_str if ver_str else "not detected",
            COLOR_GREEN if ver_str else COLOR_YELLOW)

        size = file_size(manager_path)
        _kv("Size:", format_bytes(size), COLOR_GREEN if size > 0 else COLOR_YELLOW)
    else:
        _kv("Status:", "not found", COLOR_YELLOW)

    print()

    # 3. Antigravity CLI Info
    print_menu_section("ANTIGRAVITY CLI")
    _kv("Target:", agy_path if agy_path else "Not found", COLOR_CYAN)
    if agy_path and os.path.isfile(agy_path):
        _kv("Status:", "found", COLOR_GREEN)
        patched = is_agy_patched(agy_path)
        _kv("Patch:", "already patched" if patched else "not patched",
            COLOR_YELLOW if patched else COLOR_GREEN)
        size = file_size(agy_path)
        _kv("Size:", format_bytes(size), COLOR_GREEN if size > 0 else COLOR_YELLOW)
    else:
        _kv("Status:", "not found", COLOR_YELLOW)


def redraw_main_screen(main_js_path, manager_path="", agy_path="", show_search_line=False):
    clear_screen()
    print_banner()
    print_target_info(main_js_path, manager_path, agy_path, show_search_line=show_search_line)
    print()


def run_cli():
    main_js_path = ""
    manager_path = ""
    agy_path = ""
    searched = False

    # 1. Проверяем аргументы командной строки
    if len(sys.argv) > 1:
        args = [a for a in sys.argv[1:] if a not in ("--rollback", "-r")]
        if args:
            arg = " ".join(args)
            # Пытаемся определить тип цели
            ide_path = resolve_target_path(arg)
            if ide_path and os.path.isdir(ide_path):
                ide_path = find_main_js(ide_path)
            
            if ide_path and os.path.isfile(ide_path) and ide_path.endswith("main.js"):
                main_js_path = ide_path
            else:
                # Пробуем как Antigravity 2.0 (Manager / language_server)
                mgr_path = resolve_manager_path(arg)
                if mgr_path and os.path.isfile(mgr_path):
                    manager_path = mgr_path
                else:
                    # Пробуем как CLI (agy)
                    agy_p = resolve_agy_path(arg)
                    if agy_p and os.path.isfile(agy_p):
                        agy_path = agy_p
                    else:
                        err(f"Provided path does not exist or invalid: {arg}")

    # 2. Проверяем текущую директорию (для Antigravity IDE)
    if not main_js_path and not manager_path and not agy_path:
        local = os.path.join(os.getcwd(), "main.js")
        if os.path.exists(local):
            main_js_path = local
            info("Found main.js in current directory")

    # 3. Авто-поиск в системе
    if not main_js_path and not manager_path and not agy_path:
        info("Searching for installations...")
        searched = True

        ide_root = find_install_root()
        if ide_root:
            main_js_path = find_main_js(ide_root)

        manager_path = find_manager_binary()
        agy_path = find_agy_binary()

    # Если ничего не нашли вообще, просим ввести вручную сразу
    if not main_js_path and not manager_path and not agy_path:
        warn("No installations found automatically.")
        hint("Please specify the path to Antigravity IDE, Antigravity 2.0, or agy.")
        print_path_examples()
        raw = input(color("\n  Path > ", COLOR_CYAN, COLOR_BOLD)).strip()
        if raw:
            ide_path = resolve_target_path(raw)
            if ide_path and os.path.isdir(ide_path):
                ide_path = find_main_js(ide_path)
            
            if ide_path and os.path.isfile(ide_path) and ide_path.endswith("main.js"):
                main_js_path = ide_path
            else:
                mgr_path = resolve_manager_path(raw)
                if mgr_path and os.path.isfile(mgr_path):
                    manager_path = mgr_path
                else:
                    agy_p = resolve_agy_path(raw)
                    if agy_p and os.path.isfile(agy_p):
                        agy_path = agy_p

    redraw_main_screen(main_js_path, manager_path, agy_path, show_search_line=searched)

    while True:
        print_menu_section("PATCH")
        print_menu_row("1", "Antigravity IDE patch", "bypass region lock (isGoogleInternal)", COLOR_GREEN)
        print_menu_row("2", "Antigravity 2.0 patch", "patch language_server binary", COLOR_GREEN)
        print_menu_row("3", "Antigravity CLI (agy) patch", "unlock agy tool", COLOR_GREEN)

        print_menu_section("RESTORE")
        print_menu_row("4", "Antigravity IDE", "from backup", COLOR_YELLOW)
        print_menu_row("5", "Antigravity 2.0", "from backup", COLOR_YELLOW)
        print_menu_row("6", "Antigravity CLI", "from backup", COLOR_YELLOW)

        print_menu_section("TOOLS")
        print_menu_row("7", "Fix HTTP 429", "rate-limit / too many requests", COLOR_CYAN)
        print_menu_row("8", "Open GitHub repository", "source & updates", COLOR_CYAN)
        print_menu_row("9", "Select custom path", "override auto-detected target", COLOR_CYAN)

        print()
        print_menu_row("0", "Exit", "quit the patcher", COLOR_RED)
        print_menu_footer("Tip: patches are reversible — use RESTORE any time.")

        choice = input(color("\n  Select option > ", COLOR_CYAN, COLOR_BOLD)).strip()
        print()

        if choice == "0":
            return

        # Пустой ввод — не выходим, просто перерисовываем меню
        if choice == "":
            redraw_main_screen(main_js_path, manager_path, agy_path, show_search_line=searched)
            continue

        valid_choices = {str(i) for i in range(1, 10)}
        if choice not in valid_choices:
            err("Invalid choice")
            print()
            pause()
            redraw_main_screen(main_js_path, manager_path, agy_path, show_search_line=searched)
            continue

        handled = True
        clear_screen()
        print_banner()

        if choice == "1":
            if main_js_path:
                do_patch(main_js_path, show_search_line=searched)
            else:
                err("Antigravity IDE path is not set. Please select custom path (Option 9) first.")
        elif choice == "2":
            if manager_path:
                do_patch_manager(manager_path)
            else:
                err("Antigravity 2.0 (language_server) path is not set. Please select custom path (Option 9) first.")
        elif choice == "3":
            if agy_path:
                do_patch_agy(agy_path)
            else:
                err("Antigravity CLI path is not set. Please select custom path (Option 9) first.")
        elif choice == "4":
            if main_js_path:
                do_restore(main_js_path, show_search_line=searched)
            else:
                err("Antigravity IDE path is not set. Please select custom path (Option 9) first.")
        elif choice == "5":
            if manager_path:
                do_restore_manager(manager_path)
            else:
                err("Antigravity 2.0 (language_server) path is not set. Please select custom path (Option 9) first.")
        elif choice == "6":
            if agy_path:
                do_restore_agy(agy_path)
            else:
                err("Antigravity CLI path is not set. Please select custom path (Option 9) first.")
        elif choice == "7":
            do_fix_429()
        elif choice == "8":
            print_target_info(main_js_path, manager_path, agy_path, show_search_line=searched)
            print()
            if confirmed("Open GitHub repository in browser?"):
                url = "https://github.com/AvenCores/open-antigravity-unlock"
                webbrowser.open(url)
                ok(f"Opening: {color(url, COLOR_CYAN)}")
            else:
                cancel("Cancelled.")
        elif choice == "9":
            while True:
                redraw_main_screen(main_js_path, manager_path, agy_path, show_search_line=searched)
                print_menu_section("SELECT CUSTOM PATH")
                print_menu_row("1", "Antigravity IDE path", "folder or main.js", COLOR_GREEN)
                print_menu_row("2", "Antigravity 2.0 path", "folder or language_server binary", COLOR_GREEN)
                print_menu_row("3", "Antigravity CLI path", "agy.exe or folder", COLOR_GREEN)
                print()
                print_menu_row("0", "Back", "return to main menu", COLOR_RED)
                print_menu_footer("Leaves auto-detection results intact for other targets.")

                sub_choice = input(color("\n  Select option > ", COLOR_CYAN, COLOR_BOLD)).strip()
                if sub_choice == "0":
                    handled = False
                    break

                if sub_choice == "1":
                     print()
                     hint("Enter the path to Antigravity IDE folder or main.js file.")
                     print_path_examples()
                     raw = input(color("\n  IDE Path > ", COLOR_CYAN, COLOR_BOLD)).strip()
                     if raw:
                         new_path = resolve_target_path(raw)
                         if new_path and os.path.exists(new_path):
                             if os.path.isdir(new_path):
                                 new_path = find_main_js(new_path)
                             if new_path and os.path.isfile(new_path):
                                 main_js_path = new_path
                                 searched = False
                                 ok("Antigravity IDE path updated!")
                             else:
                                 err("Could not resolve a valid Antigravity IDE target (main.js not found).")
                         else:
                             err("Path does not exist.")
                     pause()
                elif sub_choice == "2":
                     print()
                     hint("Enter the path to Antigravity 2.0 app folder or language_server binary.")
                     print_path_examples()
                     raw = input(color("\n  Antigravity 2.0 Path > ", COLOR_CYAN, COLOR_BOLD)).strip()
                     if raw:
                         new_path = resolve_manager_path(raw)
                         if new_path and os.path.isfile(new_path):
                             manager_path = new_path
                             searched = False
                             ok("Antigravity 2.0 path updated!")
                         else:
                             err("Could not resolve a valid Antigravity 2.0 target (language_server not found).")
                     pause()
                elif sub_choice == "3":
                     print()
                     hint("Enter the path to the agy binary (agy.exe) or its folder.")
                     print_path_examples()
                     raw = input(color("\n  AGY Path > ", COLOR_CYAN, COLOR_BOLD)).strip()
                     if raw:
                         new_path = resolve_agy_path(raw)
                         if new_path and os.path.isfile(new_path):
                             agy_path = new_path
                             searched = False
                             ok("Antigravity CLI path updated!")
                         else:
                             err("Could not resolve a valid Antigravity CLI target.")
                     pause()
            handled = True

        print()

        if handled:
            pause()
        redraw_main_screen(main_js_path, manager_path, agy_path, show_search_line=searched)
