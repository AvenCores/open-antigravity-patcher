import os
import sys
import webbrowser
import locale

from patcher.constants import (
    VERSION,
    COLOR_CYAN,
    COLOR_GREEN,
    COLOR_YELLOW,
    COLOR_RED,
    COLOR_BOLD,
)
from patcher.utils.console import color, clear_screen, print_banner
from patcher.utils.file import file_size, format_bytes

from patcher.ide.discovery import (
    find_install_root,
    find_main_js,
    get_ag_version,
    assign_custom_path,
    resolve_target_path,
)
from patcher.asar.discovery import (
    find_antigravity_root,
    resolve_antigravity_paths,
    is_antigravity_patched,
    read_package_json_from_asar,
)
from patcher.ide.patcher import is_already_patched, do_patch, do_restore, do_fix_429
from patcher.asar.patcher import do_patch_antigravity, do_restore_antigravity


def pause():
    input("  Press Enter to return to menu...")


def print_launch_examples():
    script_name = os.path.basename(sys.argv[0]) or "main.py"
    cmd = script_name if getattr(sys, "frozen", False) else f"python {script_name}"
    windows_example = f'{cmd} "C:\\Path\\To\\Antigravity IDE"'
    macos_example = f'{cmd} "/Applications/Antigravity IDE.app"'
    linux_example = f'{cmd} "/usr/share/antigravity-ide"'

    print(f"  [i] Usage examples with custom path:")
    print(f"      Windows: {color(windows_example, COLOR_YELLOW)}")
    print(f"      macOS:   {color(macos_example, COLOR_YELLOW)}")
    print(f"      Linux:   {color(linux_example, COLOR_YELLOW)}")


def print_path_examples():
    windows_path = r"C:\Users\Name\AppData\Local\Programs\Antigravity IDE"
    macos_path = "/Applications/Antigravity IDE.app"
    linux_path = "/usr/share/antigravity-ide"

    print("  [i] Path examples:")
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


def print_target_info(main_js_path, antigravity_root="", show_search_line=False):
    if show_search_line:
        print("  [*] Searching for installations...")
    
    # 1. Antigravity IDE Info
    print(f"  [*] Antigravity IDE Target: {color(main_js_path if main_js_path else 'Not found', COLOR_CYAN)}")
    if main_js_path and os.path.exists(main_js_path):
        exists = os.path.exists(main_js_path)
        is_dir = os.path.isdir(main_js_path) if exists else False
        if is_dir:
            print(f"      Status:  {color('directory (missing main.js)', COLOR_YELLOW)}")
        else:
            try:
                with open(main_js_path, "r", encoding="utf-8") as f:
                    content = f.read()
                print(f"      Status:  {color('found', COLOR_GREEN)}")
                if is_already_patched(content):
                    patch_text = color("already patched", COLOR_YELLOW)
                else:
                    patch_text = color("not patched", COLOR_GREEN)
                print(f"      Patch:   {patch_text}")
            except Exception:
                print(f"      Status:  {color('unreadable', COLOR_RED)}")
                print(f"      Patch:   {color('unreadable', COLOR_RED)}")
            
            ver_str, _ = get_ag_version(main_js_path)
            if ver_str:
                print(f"      Version: {color(ver_str, COLOR_GREEN)}")
            else:
                print(color("      Version: not detected", COLOR_YELLOW))
            
            size = file_size(main_js_path)
            print(f"      Size:    {color(format_bytes(size), COLOR_GREEN if size > 0 else COLOR_YELLOW)}")
    else:
        print(f"      Status:  {color('not found', COLOR_RED)}")

    print()

    # 2. Antigravity Info
    print(f"  [*] Antigravity Target:     {color(antigravity_root if antigravity_root else 'Not found', COLOR_CYAN)}")
    if antigravity_root and os.path.isdir(antigravity_root):
        asar_path, _ = resolve_antigravity_paths(antigravity_root)
        if os.path.exists(asar_path):
            print(f"      Status:  {color('found', COLOR_GREEN)}")
            if is_antigravity_patched(asar_path):
                patch_text = color("already patched", COLOR_YELLOW)
            else:
                patch_text = color("not patched", COLOR_GREEN)
            print(f"      Patch:   {patch_text}")
            
            ver_str = read_package_json_from_asar(asar_path)
            if ver_str:
                print(f"      Version: {color(ver_str, COLOR_GREEN)}")
            else:
                print(color("      Version: not detected", COLOR_YELLOW))
                
            size = file_size(asar_path)
            print(f"      Size:    {color(format_bytes(size), COLOR_GREEN if size > 0 else COLOR_YELLOW)}")
        else:
            print(f"      Status:  {color('ASAR missing', COLOR_RED)}")
    else:
        print(f"      Status:  {color('not found', COLOR_RED)}")


def redraw_main_screen(main_js_path, antigravity_root="", show_search_line=False):
    clear_screen()
    print_banner()
    print_target_info(main_js_path, antigravity_root, show_search_line=show_search_line)
    print()


def run_cli():
    main_js_path = ""
    antigravity_root = ""
    searched = False

    # 1. Проверяем аргументы командной строки
    if len(sys.argv) > 1:
        args = [a for a in sys.argv[1:] if a not in ("--rollback", "-r")]
        if args:
            arg = " ".join(args)
            main_js_path, antigravity_root = assign_custom_path(arg)
            if not main_js_path and not antigravity_root:
                print(color(f"  [!] Provided path does not exist or invalid: {arg}", COLOR_RED))

    # 2. Проверяем текущую директорию (для Antigravity IDE)
    if not main_js_path and not antigravity_root:
        local = os.path.join(os.getcwd(), "main.js")
        if os.path.exists(local):
            main_js_path = local
            print("  [*] Found main.js in current directory")

    # 3. Авто-поиск в системе
    if not main_js_path and not antigravity_root:
        print("  [*] Searching for installations...")
        searched = True
        
        ide_root = find_install_root()
        if ide_root:
            main_js_path = find_main_js(ide_root)
            
        antigravity_root = find_antigravity_root()

    # Если ничего не нашли вообще, просим ввести вручную сразу
    if not main_js_path and not antigravity_root:
        print(color("  [!] No installations found automatically.", COLOR_YELLOW))
        print("  [i] Please specify the path to Antigravity IDE, Antigravity, or main.js.")
        print_path_examples()
        raw = input(color("\n  Path > ", COLOR_CYAN, COLOR_BOLD)).strip()
        if raw:
            main_js_path, antigravity_root = assign_custom_path(raw)

    redraw_main_screen(main_js_path, antigravity_root, show_search_line=searched)

    while True:
        print(color("  1. Apply Antigravity IDE patch", COLOR_GREEN))
        print(color("  2. Apply Antigravity patch", COLOR_GREEN))
        print(color("  3. Restore Antigravity IDE from backup", COLOR_YELLOW))
        print(color("  4. Restore Antigravity from backup", COLOR_YELLOW))
        print(color("  5. Fix HTTP 429 (Too Many Requests)", COLOR_CYAN))
        print(color("  6. Open GitHub repository", COLOR_CYAN))
        print(color("  7. Select custom path", COLOR_CYAN))
        print(color("  0. Exit", COLOR_RED))

        choice = input(color("\n  > ", COLOR_CYAN, COLOR_BOLD)).strip()
        print()

        if choice in ("0", ""):
            return

        handled = True
        clear_screen()
        print_banner()

        if choice == "1":
            if main_js_path:
                do_patch(main_js_path, show_search_line=searched)
            else:
                print(color("  [!] Antigravity IDE path is not set. Please select custom path (Option 7) first.", COLOR_RED))
        elif choice == "2":
            if antigravity_root:
                do_patch_antigravity(antigravity_root)
            else:
                print(color("  [!] Antigravity path is not set. Please select custom path (Option 7) first.", COLOR_RED))
        elif choice == "3":
            if main_js_path:
                do_restore(main_js_path, show_search_line=searched)
            else:
                print(color("  [!] Antigravity IDE path is not set. Please select custom path (Option 7) first.", COLOR_RED))
        elif choice == "4":
            if antigravity_root:
                do_restore_antigravity(antigravity_root)
            else:
                print(color("  [!] Antigravity path is not set. Please select custom path (Option 7) first.", COLOR_RED))
        elif choice == "5":
            do_fix_429()
        elif choice == "6":
            print_target_info(main_js_path, antigravity_root, show_search_line=searched)
            print()
            if confirmed("Open GitHub repository in browser?"):
                url = "https://github.com/AvenCores/open-antigravity-unlock"
                webbrowser.open(url)
                print(f"  [+] Opening: {color(url, COLOR_CYAN)}")
            else:
                print("  [x] Cancelled.")
        elif choice == "7":
            while True:
                redraw_main_screen(main_js_path, antigravity_root, show_search_line=searched)
                print(color("  1. Select Antigravity IDE path", COLOR_GREEN))
                print(color("  2. Select Antigravity path", COLOR_GREEN))
                print(color("  0. Back", COLOR_RED))

                sub_choice = input(color("\n  > ", COLOR_CYAN, COLOR_BOLD)).strip()
                if sub_choice == "0":
                    break
                
                if sub_choice == "1":
                    print("\n  [i] Enter the path to Antigravity IDE folder or main.js file.")
                    print_path_examples()
                    raw = input(color("\n  IDE Path > ", COLOR_CYAN, COLOR_BOLD)).strip()
                    if raw:
                        new_main_js, _ = assign_custom_path(raw)
                        if new_main_js:
                            main_js_path = new_main_js
                            searched = False
                            print(color("  [+] Antigravity IDE path updated!", COLOR_GREEN))
                        else:
                            print(color("  [!] Could not resolve a valid Antigravity IDE target.", COLOR_RED))
                    pause()
                elif sub_choice == "2":
                    print("\n  [i] Enter the path to Antigravity folder.")
                    print_path_examples()
                    raw = input(color("\n  Antigravity Path > ", COLOR_CYAN, COLOR_BOLD)).strip()
                    if raw:
                        _, new_ag_root = assign_custom_path(raw)
                        if new_ag_root:
                            antigravity_root = new_ag_root
                            searched = False
                            print(color("  [+] Antigravity path updated!", COLOR_GREEN))
                        else:
                            print(color("  [!] Could not resolve a valid Antigravity target.", COLOR_RED))
                    pause()
            handled = True
        else:
            handled = False
            print("  [!] Invalid choice")
        print()

        if handled:
            pause()
            redraw_main_screen(main_js_path, antigravity_root, show_search_line=searched)
