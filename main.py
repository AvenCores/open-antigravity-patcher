import os
import sys
import re
import hashlib
import time
import ctypes
from packaging.version import Version

VERSION = "1.0.1"
MIN_AG_VERSION = "1.20.5"
USE_COLOR = False

CSI = "\x1b["
COLOR_RESET = CSI + "0m"
COLOR_CYAN = CSI + "36m"
COLOR_GREEN = CSI + "32m"
COLOR_YELLOW = CSI + "33m"
COLOR_RED = CSI + "31m"
COLOR_BOLD = CSI + "1m"

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
    print("  ╔═══════════════════════════════════════════════╗")
    print("  ║  Open AG Patcher v" + VERSION + "                       ║")
    print("  ║  Region bypass for Antigravity                ║")
    print("  ║  Clean • No keys • No telemetry               ║")
    print("  ║  Telegram Channel: t.me/avencoresyt           ║")
    print("  ║  YouTube Channel: youtube.com/@avencores      ║")
    print("  ╚═══════════════════════════════════════════════╝")
    print()

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except Exception:
        return False

def run_as_admin():
    if os.name != 'nt':
        return True

    if is_admin():
        return True
    
    # Автоматическое повышение прав с обработкой путей с пробелами
    if getattr(sys, 'frozen', False):
        executable = sys.executable
        args_str = ' '.join([f'"{a}"' for a in sys.argv[1:]])
    else:
        executable = sys.executable
        args_str = ' '.join([f'"{a}"' for a in sys.argv])
    
    try:
        ret = ctypes.windll.shell32.ShellExecuteW(None, "runas", executable, args_str, None, 1)
        return ret > 32
    except Exception:
        return False

def find_install_root():
    candidates =[]

    if os.name == 'nt':
        local_app_data = os.environ.get("LOCALAPPDATA")
        if local_app_data:
            candidates.append(os.path.join(local_app_data, "Programs", "Antigravity"))
        pf = os.environ.get("PROGRAMFILES")
        if pf:
            candidates.append(os.path.join(pf, "Antigravity"))
        pfx86 = os.environ.get("PROGRAMFILES(X86)")
        if pfx86:
            candidates.append(os.path.join(pfx86, "Antigravity"))

        try:
            import winreg
            for hive, key_path in[
                (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\Antigravity"),
                (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\Antigravity")
            ]:
                try:
                    with winreg.OpenKey(hive, key_path) as key:
                        install_loc, _ = winreg.QueryValueEx(key, "InstallLocation")
                        if install_loc and install_loc.strip():
                            candidates.append(install_loc.strip())
                except OSError:
                    pass
        except ImportError:
            pass

    for path in candidates:
        for sub in[
            os.path.join("resources", "app", "out", "main.js"),
            os.path.join("resources", "app", "main.js")
        ]:
            if os.path.exists(os.path.join(path, sub)):
                return path
    return ""

def find_main_js(root):
    for sub in[
        os.path.join("resources", "app", "out", "main.js"),
        os.path.join("resources", "app", "main.js"),
        "main.js"
    ]:
        p = os.path.join(root, sub)
        if os.path.exists(p):
            return p
    return ""

def get_ag_version(main_js_path):
    """
    Читает версию Antigravity только из реестра Windows.
    """
    if os.name == 'nt':
        try:
            import winreg
            for hive, key_path in[
                (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Uninstall\{AA73B3E3-C6C8-45C8-B1DC-4AE56C751432}_is1"),
                (winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\Uninstall\{AA73B3E3-C6C8-45C8-B1DC-4AE56C751432}_is1")
            ]:
                try:
                    with winreg.OpenKey(hive, key_path) as key:
                        display_ver, _ = winreg.QueryValueEx(key, "DisplayVersion")
                        if display_ver and display_ver.strip():
                            return display_ver.strip()
                except OSError:
                    pass
        except ImportError:
            pass

    return None

def check_ag_version(main_js_path):
    """
    Проверяет, что версия Antigravity не ниже MIN_AG_VERSION.
    Возвращает (ok, detected_version_str):
      ok = True   — версия подходит
      ok = False  — версия слишком старая
      ok = None   — не удалось определить / распарсить
    """
    ver_str = get_ag_version(main_js_path)

    if ver_str is None:
        return None, None

    try:
        detected = Version(ver_str)
        minimum  = Version(MIN_AG_VERSION)
        return detected >= minimum, ver_str
    except Exception:
        return None, ver_str

def apply_patches(content):
    results =[]
    original = content

    # 1. if(isGoogleInternal) -> if(true)
    re_if_internal = re.compile(r'if\(this\.([a-zA-Z_$]+)\.isGoogleInternal\)')
    matches =[m.group(0) for m in re_if_internal.finditer(content)]
    old = content
    content = re_if_internal.sub('if(true)', content)
    if content != old:
        unique_matches = list(set(matches))
        results.append({
            "Name": "if(isGoogleInternal) → if(true)",
            "Applied": True,
            "Detail": f"replaced {len(matches)} occurrences: {unique_matches}"
        })
    else:
        results.append({"Name": "if(isGoogleInternal) → if(true)", "Applied": False, "Detail": ""})

    # 2. onboardUser injection
    re_internal_block = re.compile(r'(await\s+this\.([a-zA-Z_$]+)\.loadCodeAssist\(([a-zA-Z_$]+)\))(;const\{settings)')
    internal_match = re_internal_block.search(content)

    if internal_match:
        var_svc = internal_match.group(2)
        arg_name = internal_match.group(3)

        onboard_code = f';try{{await this.{var_svc}.onboardUser("standard-tier",{arg_name})}}catch(_e){{try{{await this.{var_svc}.onboardUser("free-tier",{arg_name})}}catch(_e2){{}}}}'

        old = content
        replacement = internal_match.group(1) + onboard_code + internal_match.group(4)
        content = content.replace(internal_match.group(0), replacement, 1)

        results.append({
            "Name": "onboardUser injection (internal path)",
            "Applied": content != old,
            "Detail": f"this.{var_svc}.onboardUser() before refreshUserStatus"
        })
    else:
        re_load_ca = re.compile(r'(await\s+this\.([a-zA-Z_$]+)\.loadCodeAssist\(([a-zA-Z_$]+)\))')
        lca_match = re_load_ca.search(content)
        if lca_match:
            var_svc = lca_match.group(2)
            arg_name = lca_match.group(3)
            injection = f';try{{await this.{var_svc}.onboardUser("standard-tier",{arg_name})}}catch(_e){{try{{await this.{var_svc}.onboardUser("free-tier",{arg_name})}}catch(_e2){{}}}}'
            
            old = content
            replacement = lca_match.group(1) + injection
            content = content.replace(lca_match.group(0), replacement, 1)
            
            results.append({
                "Name": "onboardUser injection (fallback)",
                "Applied": content != old,
                "Detail": f"this.{var_svc}.onboardUser() after loadCodeAssist"
            })
        else:
            results.append({"Name": "onboardUser injection", "Applied": False, "Detail": "loadCodeAssist not found"})

    # 3. ideName -> antigravity-insiders
    old = content
    content = content.replace('ideName:"antigravity"', 'ideName:"antigravity-insiders"')
    results.append({
        "Name": "ideName → antigravity-insiders",
        "Applied": content != old,
        "Detail": ""
    })

    # 4. refreshUserStatus wrapper
    re_refresh = re.compile(r'await this\.(([a-zA-Z_$]+\.)?refreshUserStatus\(([a-zA-Z_$]+)\))')
    refresh_matches = list(re_refresh.finditer(content))
    
    if refresh_matches:
        old = content
        for rm in refresh_matches:
            full = rm.group(0)
            inner_call = rm.group(1)
            arg_r = rm.group(3)

            wrapped = f'await(async()=>{{try{{return await this.{inner_call}}}catch(_e){{return{{settings:{{}},userTier:"pro",oauthTokenInfo:{arg_r}}}}}}})()'
            content = content.replace(full, wrapped, 1)

        results.append({
            "Name": "refreshUserStatus → wrapped with fallback",
            "Applied": content != old,
            "Detail": f"{len(refresh_matches)} calls wrapped"
        })
    else:
        results.append({"Name": "refreshUserStatus wrapper", "Applied": False, "Detail": ""})

    return content, results

def is_already_patched(content):
    return "if(true)" in content and '"antigravity-insiders"' in content

def file_hash(path):
    try:
        with open(path, "rb") as f:
            data = f.read()
        return hashlib.sha256(data).hexdigest()
    except Exception:
        return "?"

def file_size(path):
    try:
        return os.path.getsize(path)
    except Exception:
        return 0

def format_size_mb(path):
    size_mb = file_size(path) / 1024 / 1024
    return f"{size_mb:.1f} MB"

def print_target_info(main_js_path, show_search_line=False):
    if show_search_line:
        print("  [*] Searching for Antigravity installation...")
    print(f"  [*] Target: {color(main_js_path, COLOR_CYAN)}")
    ver_str = get_ag_version(main_js_path)
    if ver_str:
        print(f"  [*] Antigravity version: {color(ver_str, COLOR_GREEN)}")
    else:
        print(color("  [!] Antigravity version: not detected", COLOR_YELLOW))
    print(f"  [*] Size:   {color(format_size_mb(main_js_path), COLOR_GREEN)}")

def prompt_yn(question):
    question = question.rstrip()
    prompt = f"  [?] {question} ({color('y', COLOR_GREEN)}/{color('n', COLOR_RED)}): "
    return input(prompt).strip().lower()

def do_patch(main_js_path, show_search_line=False):
    # --- Проверка минимальной версии ---
    ver_ok, ver_str = check_ag_version(main_js_path)

    if ver_str is not None:
        print(f"  [*] Antigravity version: {color(ver_str, COLOR_GREEN)}")

    if ver_ok is False:
        # Версия определена, но ниже минимальной
        print(color(f"  [!] Unsupported version: {ver_str}", COLOR_RED))
        print(color(f"  [!] Minimum required: {MIN_AG_VERSION}", COLOR_RED))
        print("  [i] Please update Antigravity and try again.")
        c = prompt_yn("Proceed anyway?")
        if c != 'y':
            return
    elif ver_ok is None and ver_str is None:
        # Версия в реестре не найдена
        print(color("  [!] Could not detect Antigravity version (registry key not found).", COLOR_YELLOW))
        c = prompt_yn("Proceed without version check?")
        if c != 'y':
            return
    elif ver_ok is None and ver_str is not None:
        # Версия найдена, но не удалось распарсить
        print(color(f"  [!] Could not parse version string: {ver_str}", COLOR_YELLOW))
        c = prompt_yn("Proceed anyway?")
        if c != 'y':
            return
    # else: ver_ok is True — версия подходит, продолжаем

    try:
        with open(main_js_path, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        print(f"  [!] Read error: {e}")
        return

    if is_already_patched(content):
        print("  [i] File appears already patched.")
        c = prompt_yn("Apply anyway?")
        if c != 'y':
            clear_screen()
            print_banner()
            print_target_info(main_js_path, show_search_line=show_search_line)
            return

    backup_path = main_js_path + ".bak"
    if not os.path.exists(backup_path):
        print("  [*] Creating backup...")
        try:
            with open(backup_path, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"  [+] Backup: {os.path.basename(backup_path)}")
        except Exception as e:
            print(f"  [!] Backup error: {e}")
            return
    else:
        print("  [i] Backup already exists")

    hash_before = file_hash(main_js_path)

    print("  [*] Applying patches...")
    print()

    new_content, results = apply_patches(content)

    applied = 0
    for r in results:
        icon = "  ✓" if r.get("Applied") else "  ✗"
        if r.get("Applied"):
            applied += 1
        detail = f" — {r.get('Detail')}" if r.get("Detail") else ""
        print(f"{icon} {r['Name']}{detail}")
    print()

    if applied == 0:
        print("  [!] No patches applied.")
        return

    try:
        with open(main_js_path, "w", encoding="utf-8") as f:
            f.write(new_content)
    except Exception as e:
        print(f"  [!] Write error: {e}")
        return

    hash_after = file_hash(main_js_path)
    print(f"  [+] Patches: {applied}/{len(results)} applied")
    if hash_before != "?":
        print(f"  [+] Before:  {hash_before[:8]}...{hash_before[56:]}")
        print(f"  [+] After:   {hash_after[:8]}...{hash_after[56:]}")
    print(f"  [+] Done at  {time.strftime('%H:%M:%S')}")
    print()
    print("  Restart Antigravity and sign in.")

def do_restore(main_js_path, show_search_line=False):
    backup_path = main_js_path + ".bak"
    try:
        with open(backup_path, "r", encoding="utf-8") as f:
            data = f.read()
    except Exception as e:
        print(f"  [!] Backup not found: {backup_path}")
        return

    try:
        with open(main_js_path, "w", encoding="utf-8") as f:
            f.write(data)
    except Exception as e:
        print(f"\n  [!] Restore error: {e}")
        return

    print_target_info(main_js_path, show_search_line=show_search_line)
    print("\n  [+] Restored from backup!")

def main():
    setup_console()
    print_banner()

    main_js_path = ""
    root = ""

    if len(sys.argv) > 1:
        arg = sys.argv[1]
        if arg.endswith("main.js"):
            main_js_path = arg
        else:
            root = arg
            main_js_path = find_main_js(root)

    if not main_js_path:
        cwd = os.getcwd()
        local = os.path.join(cwd, "main.js")
        if os.path.exists(local):
            main_js_path = local
            print("  [*] Found main.js in current directory")

    searched = False
    if not main_js_path:
        print("  [*] Searching for Antigravity installation...")
        searched = True
        root = find_install_root()
        if root:
            main_js_path = find_main_js(root)

    if not main_js_path:
        print("  [!] main.js not found!")
        print("  [i] Put main.js next to ag_patcher.py, or specify path:")
        print("      python ag_patcher.py C:\\path\\to\\Antigravity")
        input("\n  Press Enter to exit...")
        return

    print_target_info(main_js_path, show_search_line=False)
    print()

    while True:
        print(color("  1. Apply patch", COLOR_GREEN))
        print(color("  2. Restore from backup", COLOR_YELLOW))
        print(color("  0. Exit", COLOR_RED))
        
        choice = input(color("\n  > ", COLOR_CYAN, COLOR_BOLD)).strip()
        print()

        if choice in ("0", ""):
            return

        clear_screen()
        print_banner()

        if choice == "1":
            do_patch(main_js_path, show_search_line=searched)
        elif choice == "2":
            do_restore(main_js_path, show_search_line=searched)
        else:
            print("  [!] Invalid choice")
        print()

if __name__ == "__main__":
    if os.name == 'nt' and not is_admin():
        if run_as_admin():
            sys.exit(0)
        else:
            print("  [!] Could not elevate privileges. The script may fail to modify files.")
    
    try:
        main()
    except KeyboardInterrupt:
        print("\n  [i] Exiting...")
        sys.exit(0)
