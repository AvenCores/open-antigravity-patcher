import os
import sys
import re
import json
import shutil
import hashlib
import time
import ctypes
import webbrowser
import subprocess
from enum import Enum
from packaging.version import Version

VERSION = "1.0.6"
MIN_AG_VERSION = "1.20.5"
USE_COLOR = False

# Единственное место, где хранится GUID установщика Antigravity
AG_REGISTRY_SUBKEY = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\{AA73B3E3-C6C8-45C8-B1DC-4AE56C751432}_is1"

CSI = "\x1b["
COLOR_RESET = CSI + "0m"
COLOR_CYAN = CSI + "36m"
COLOR_GREEN = CSI + "32m"
COLOR_YELLOW = CSI + "33m"
COLOR_RED = CSI + "31m"
COLOR_BOLD = CSI + "1m"


class VersionStatus(Enum):
    OK = "ok"
    TOO_OLD = "too_old"
    NOT_FOUND = "not_found"
    PARSE_ERROR = "parse_error"


# ---------------------------------------------------------------------------
# Консоль / цвет
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Права администратора
# ---------------------------------------------------------------------------

def is_admin():
    try:
        if os.name == "posix":
            return os.getuid() == 0
        return ctypes.windll.shell32.IsUserAnAdmin()
    except Exception:
        return False


def run_as_admin():
    if os.name != "nt":
        return True
    if is_admin():
        return True

    # Автоматическое повышение прав с обработкой путей с пробелами
    if getattr(sys, "frozen", False):
        executable = sys.executable
        args_str = " ".join([f'"{a}"' for a in sys.argv[1:]])
    else:
        executable = sys.executable
        script = sys.argv[0]
        args_str = " ".join([f'"{a}"' for a in [script] + sys.argv[1:]])

    try:
        ret = ctypes.windll.shell32.ShellExecuteW(None, "runas", executable, args_str, None, 1)
        return ret > 32
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Поиск установки
# ---------------------------------------------------------------------------

def find_install_root():
    candidates = []

    if os.name == "posix":
        candidates.append("/usr/share/antigravity")

    if os.name == "nt":
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
            for hive in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
                try:
                    with winreg.OpenKey(hive, AG_REGISTRY_SUBKEY) as key:
                        install_loc, _ = winreg.QueryValueEx(key, "InstallLocation")
                        if install_loc and install_loc.strip():
                            candidates.append(install_loc.strip())
                except OSError:
                    pass
        except ImportError:
            pass

    for path in candidates:
        for sub in [
            os.path.join("resources", "app", "out", "main.js"),
            os.path.join("resources", "app", "main.js"),
        ]:
            if os.path.exists(os.path.join(path, sub)):
                return path
    return ""


def find_main_js(root):
    for sub in [
        os.path.join("resources", "app", "out", "main.js"),
        os.path.join("resources", "app", "main.js"),
        "main.js",
    ]:
        p = os.path.join(root, sub)
        if os.path.exists(p):
            return p
    return ""


# ---------------------------------------------------------------------------
# Определение версии AG
# ---------------------------------------------------------------------------

def get_ag_version(main_js_path):
    """Читает версию Antigravity из реестра Windows или package.json на Linux."""
    if os.name == "posix":
        # Сначала пробуем dpkg (apt-установка)
        try:
            result = subprocess.run(
                ["dpkg-query", "-W", "-f=${Version}", "antigravity"],
                capture_output=True, text=True,
            )
            if result.returncode == 0:
                ver = result.stdout.strip()
                if ver:
                    return ver
        except Exception:
            pass

        # rpm-based (Fedora, RHEL, openSUSE и др.)
        try:
            result = subprocess.run(
                ["rpm", "-q", "--queryformat", "%{VERSION}", "antigravity"],
                capture_output=True, text=True,
            )
            if result.returncode == 0:
                ver = result.stdout.strip()
                if ver:
                    return ver
        except Exception:
            pass

        # Fallback: package.json (portable / snap / flatpak)
        for rel in (
            os.path.join(os.path.dirname(main_js_path), "..", "package.json"),
            os.path.join(os.path.dirname(main_js_path), "package.json"),
        ):
            pkg = os.path.normpath(rel)
            if os.path.exists(pkg):
                try:
                    with open(pkg, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    ver = data.get("version", "").strip()
                    if ver:
                        return ver
                except Exception:
                    pass
        return None

    if os.name == "nt":
        try:
            import winreg
            for hive in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
                try:
                    with winreg.OpenKey(hive, AG_REGISTRY_SUBKEY) as key:
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
    Проверяет версию Antigravity.
    Возвращает (VersionStatus, detected_version_str | None).
    """
    ver_str = get_ag_version(main_js_path)

    if ver_str is None:
        return VersionStatus.NOT_FOUND, None

    try:
        detected = Version(ver_str)
        minimum = Version(MIN_AG_VERSION)
        status = VersionStatus.OK if detected >= minimum else VersionStatus.TOO_OLD
        return status, ver_str
    except Exception:
        return VersionStatus.PARSE_ERROR, ver_str


def parse_version_safe(ver_str):
    if not ver_str:
        return None
    try:
        return Version(ver_str)
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Бэкап: метаданные версии и хэш
# ---------------------------------------------------------------------------

def load_backup_version(backup_path):
    meta_path = backup_path + ".version"
    if not os.path.exists(meta_path):
        return None
    try:
        with open(meta_path, "r", encoding="utf-8") as f:
            ver_str = f.read().strip()
        return ver_str or None
    except Exception:
        return None


def save_backup_version(backup_path, version_str):
    if not version_str:
        return
    meta_path = backup_path + ".version"
    try:
        with open(meta_path, "w", encoding="utf-8") as f:
            f.write(version_str.strip())
    except Exception as e:
        print(color(f"  [!] Could not save backup version metadata: {e}", COLOR_YELLOW))


def save_backup_hash(backup_path):
    h = file_hash(backup_path)
    if h is not None:
        try:
            with open(backup_path + ".sha256", "w", encoding="utf-8") as f:
                f.write(h)
        except Exception as e:
            print(color(f"  [!] Could not save backup hash: {e}", COLOR_YELLOW))


def verify_backup_hash(backup_path):
    hash_file = backup_path + ".sha256"
    if not os.path.exists(hash_file):
        return None  # нет данных — не проверяем
    try:
        with open(hash_file, "r", encoding="utf-8") as f:
            saved = f.read().strip()
        return file_hash(backup_path) == saved
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Файловые утилиты
# ---------------------------------------------------------------------------

def file_hash(path):
    """Возвращает SHA-256 файла или None при ошибке."""
    try:
        with open(path, "rb") as f:
            data = f.read()
        return hashlib.sha256(data).hexdigest()
    except Exception:
        return None


def file_size(path):
    try:
        return os.path.getsize(path)
    except Exception:
        return 0


def format_bytes(size_bytes):
    if size_bytes >= 1024 * 1024:
        return f"{size_bytes / 1024 / 1024:.1f} MB"
    if size_bytes >= 1024:
        return f"{size_bytes / 1024:.1f} KB"
    return f"{size_bytes} B"


# ---------------------------------------------------------------------------
# Патчи (каждый патч — отдельная функция)
# ---------------------------------------------------------------------------

def _patch_is_google_internal(content):
    """if(isGoogleInternal) → if(true)"""
    re_if_internal = re.compile(r"if\(this\.([a-zA-Z_$]+)\.isGoogleInternal\)")
    matches = [m.group(0) for m in re_if_internal.finditer(content)]
    new_content = re_if_internal.sub("if(true)", content)
    applied = new_content != content
    detail = f"replaced {len(matches)} occurrences: {list(set(matches))}" if applied else ""
    return new_content, {
        "Name": "if(isGoogleInternal) → if(true)",
        "Applied": applied,
        "Detail": detail,
    }


def _patch_onboard_user(content):
    """onboardUser injection после loadCodeAssist."""
    # Вариант 1: с немедленно следующим ;const{settings}
    re_internal_block = re.compile(
        r"(await\s+this\.([a-zA-Z_$]+)\.loadCodeAssist\(([a-zA-Z_$]+)\))(;const\{settings)"
    )
    internal_match = re_internal_block.search(content)

    if internal_match:
        var_svc = internal_match.group(2)
        arg_name = internal_match.group(3)
        injection = (
            f';try{{await this.{var_svc}.onboardUser("standard-tier",{arg_name})}}'
            f'catch(_e){{try{{await this.{var_svc}.onboardUser("free-tier",{arg_name})}}catch(_e2){{}}}}'
        )
        replacement = internal_match.group(1) + injection + internal_match.group(4)
        new_content = content.replace(internal_match.group(0), replacement, 1)
        return new_content, {
            "Name": "onboardUser injection (internal path)",
            "Applied": new_content != content,
            "Detail": f"this.{var_svc}.onboardUser() before refreshUserStatus",
        }

    # Вариант 2: просто после loadCodeAssist
    re_load_ca = re.compile(r"(await\s+this\.([a-zA-Z_$]+)\.loadCodeAssist\(([a-zA-Z_$]+)\))")
    lca_match = re_load_ca.search(content)
    if lca_match:
        var_svc = lca_match.group(2)
        arg_name = lca_match.group(3)
        injection = (
            f';try{{await this.{var_svc}.onboardUser("standard-tier",{arg_name})}}'
            f'catch(_e){{try{{await this.{var_svc}.onboardUser("free-tier",{arg_name})}}catch(_e2){{}}}}'
        )
        replacement = lca_match.group(1) + injection
        new_content = content.replace(lca_match.group(0), replacement, 1)
        return new_content, {
            "Name": "onboardUser injection (fallback)",
            "Applied": new_content != content,
            "Detail": f"this.{var_svc}.onboardUser() after loadCodeAssist",
        }

    return content, {
        "Name": "onboardUser injection",
        "Applied": False,
        "Detail": "loadCodeAssist not found",
    }


def _patch_ide_name(content):
    """ideName → antigravity-insiders"""
    new_content = content.replace('ideName:"antigravity"', 'ideName:"antigravity-insiders"')
    return new_content, {
        "Name": "ideName → antigravity-insiders",
        "Applied": new_content != content,
        "Detail": "",
    }


def _patch_refresh_user_status(content):
    """refreshUserStatus wrapper с fallback на pro-tier."""
    re_refresh = re.compile(r"await this\.(([a-zA-Z_$]+\.)?refreshUserStatus\(([a-zA-Z_$]+)\))")
    refresh_matches = list(re_refresh.finditer(content))

    if not refresh_matches:
        return content, {"Name": "refreshUserStatus wrapper", "Applied": False, "Detail": ""}

    # Итерируем в обратном порядке, чтобы замены не сдвигали индексы
    new_content = content
    for rm in reversed(refresh_matches):
        inner_call = rm.group(1)
        arg_r = rm.group(3)
        wrapped = f'await(async()=>{{try{{return await this.{inner_call}}}catch(_e){{return{{settings:{{}},userTier:"pro",oauthTokenInfo:{arg_r}}}}}}})()'
        start, end = rm.start(), rm.end()
        new_content = new_content[:start] + wrapped + new_content[end:]

    return new_content, {
        "Name": "refreshUserStatus → wrapped with fallback",
        "Applied": new_content != content,
        "Detail": f"{len(refresh_matches)} calls wrapped",
    }


def apply_patches(content):
    results = []
    for patch_fn in (
        _patch_is_google_internal,
        _patch_onboard_user,
        _patch_ide_name,
        _patch_refresh_user_status,
    ):
        content, result = patch_fn(content)
        results.append(result)
    return content, results


def is_already_patched(content):
    # Проверяем конкретные строки, внедрённые патчем
    return 'ideName:"antigravity-insiders"' in content and "onboardUser(" in content


def backup_matches_current_main_js(backup_content, current_content):
    """Проверяет, соответствует ли backup текущему main.js."""
    if current_content is None:
        return False

    if backup_content == current_content:
        return True

    if is_already_patched(current_content) and not is_already_patched(backup_content):
        patched_backup_content, _ = apply_patches(backup_content)
        return patched_backup_content == current_content

    return False


# ---------------------------------------------------------------------------
# UI-утилиты
# ---------------------------------------------------------------------------

def prompt_yn(question):
    question = question.rstrip()
    prompt = f"  [?] {question} ({color('y', COLOR_GREEN)}/{color('n', COLOR_RED)}): "
    return input(prompt).strip().lower()


def confirmed(question):
    """Возвращает True, если пользователь ответил 'y'."""
    return prompt_yn(question) == "y"


def print_target_info(main_js_path, show_search_line=False):
    if show_search_line:
        print("  [*] Searching for Antigravity installation...")
    print(f"  [*] Target: {color(main_js_path, COLOR_CYAN)}")
    ver_str = get_ag_version(main_js_path)
    if ver_str:
        print(f"  [*] Antigravity version: {color(ver_str, COLOR_GREEN)}")
    else:
        print(color("  [!] Antigravity version: not detected", COLOR_YELLOW))
    print(f"  [*] Size:   {color(format_bytes(file_size(main_js_path)), COLOR_GREEN)}")


def redraw_main_screen(main_js_path, show_search_line=False):
    clear_screen()
    print_banner()
    print_target_info(main_js_path, show_search_line=show_search_line)
    print()


# ---------------------------------------------------------------------------
# Предупреждения о небезопасном бэкапе
# ---------------------------------------------------------------------------

def warn_about_unsafe_backup(main_js_path, installed_version_str=None, current_content=None):
    backup_path = main_js_path + ".bak"
    if not os.path.exists(backup_path):
        return True, False

    installed_version_str = installed_version_str or get_ag_version(main_js_path)
    installed_version = parse_version_safe(installed_version_str)
    backup_version_str = load_backup_version(backup_path)
    backup_version = parse_version_safe(backup_version_str)
    backup_size = file_size(backup_path)
    current_size = file_size(main_js_path)
    warnings = []

    if installed_version and backup_version and backup_version < installed_version:
        warnings.append(
            f"backup version {backup_version_str} is older than installed {installed_version_str}"
        )

    try:
        with open(backup_path, "r", encoding="utf-8") as f:
            backup_content = f.read()
    except Exception as e:
        print(color(f"  [!] Backup check error: {e}", COLOR_YELLOW))
        return False, False

    if backup_size <= 2048 or len(backup_content.strip()) <= 512:
        warnings.append(
            f"backup size is only {format_bytes(backup_size)} and it looks almost empty"
        )
    elif current_size and backup_size < max(4096, current_size // 10):
        warnings.append(
            f"backup is much smaller than current main.js "
            f"({format_bytes(backup_size)} vs {format_bytes(current_size)})"
        )

    if current_content is not None:
        if backup_matches_current_main_js(backup_content, current_content):
            if installed_version_str and not backup_version_str:
                save_backup_version(backup_path, installed_version_str)
        elif not is_already_patched(current_content):
            warnings.append("backup does not match the current unpatched main.js")
        else:
            warnings.append(
                "backup does not match the current (patched) main.js — it may be from a different version"
            )

    if not warnings:
        return True, False

    for warning in warnings:
        print(color(f"  [!] Backup warning: {warning}", COLOR_YELLOW))
    print(color("  [!] Restoring this backup may break Antigravity.", COLOR_YELLOW))
    print(color(f"  [i] Backup kept: {os.path.basename(backup_path)}", COLOR_YELLOW))
    return True, True


# ---------------------------------------------------------------------------
# Операции: патч и восстановление
# ---------------------------------------------------------------------------

def do_patch(main_js_path, show_search_line=False):
    ver_status, ver_str = check_ag_version(main_js_path)

    if ver_status == VersionStatus.TOO_OLD:
        print(color(f"  [!] Unsupported version: {ver_str}", COLOR_RED))
        print(color(f"  [!] Minimum required: {MIN_AG_VERSION}", COLOR_RED))
        print("  [i] Please update Antigravity and try again.")
        if not confirmed("Proceed anyway?"):
            return
    elif ver_status == VersionStatus.NOT_FOUND:
        print(color("  [!] Could not detect Antigravity version (registry key not found).", COLOR_YELLOW))
        if not confirmed("Proceed without version check?"):
            return
    elif ver_status == VersionStatus.PARSE_ERROR:
        print(color(f"  [!] Could not parse version string: {ver_str}", COLOR_YELLOW))
        if not confirmed("Proceed anyway?"):
            return
    # VersionStatus.OK — продолжаем без вопросов

    try:
        with open(main_js_path, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        print(f"  [!] Read error: {e}")
        return

    current_is_patched = is_already_patched(content)

    if current_is_patched:
        print("  [i] File appears already patched.")
        if not confirmed("Apply anyway?"):
            clear_screen()
            print_banner()
            print_target_info(main_js_path, show_search_line=show_search_line)
            return

    backup_path = main_js_path + ".bak"

    need_new_backup = True
    if os.path.exists(backup_path):
        backup_size = file_size(backup_path)
        backup_version_str = load_backup_version(backup_path)
        backup_version = parse_version_safe(backup_version_str)
        installed_version = parse_version_safe(ver_str)
        try:
            with open(backup_path, "r", encoding="utf-8") as f:
                backup_content = f.read()
            backup_looks_empty = backup_size <= 2048 or len(backup_content.strip()) <= 512
        except Exception:
            backup_looks_empty = True

        if backup_looks_empty and current_is_patched:
            print(color("  [!] Existing backup looks empty or corrupted, but current main.js is already patched - keeping it because a clean backup cannot be rebuilt now.", COLOR_YELLOW))
            need_new_backup = False
        elif is_already_patched(backup_content) and current_is_patched:
            print(color("  [!] Existing backup is itself patched, but current main.js is already patched too - keeping it because a clean backup cannot be rebuilt now.", COLOR_YELLOW))
            need_new_backup = False
        elif not current_is_patched and backup_content != content:
            if installed_version and backup_version and backup_version < installed_version:
                print(color(f"  [!] Existing backup is from older version {backup_version_str} - replacing it.", COLOR_YELLOW))
            else:
                print(color("  [!] Existing backup does not match the current clean main.js - replacing it.", COLOR_YELLOW))
        elif current_is_patched and not backup_matches_current_main_js(backup_content, content):
            print(color("  [!] Existing backup does not match the current patched build - keeping it because a clean backup cannot be rebuilt now.", COLOR_YELLOW))
            need_new_backup = False
        elif backup_looks_empty:
            print(color("  [!] Existing backup looks empty or corrupted — replacing it.", COLOR_YELLOW))
        elif is_already_patched(backup_content):
            print(color("  [!] Existing backup is itself patched — replacing it with clean copy.", COLOR_YELLOW))
        else:
            need_new_backup = False
            print("  [i] Backup already exists")

    if need_new_backup:
        if current_is_patched:
            print(color("  [!] main.js is already patched - skipping backup creation because a clean backup cannot be created from a patched file.", COLOR_YELLOW))
        else:
            print("  [*] Creating backup...")
            try:
                with open(backup_path, "w", encoding="utf-8") as f:
                    f.write(content)
                save_backup_version(backup_path, ver_str)
                save_backup_hash(backup_path)
                print(f"  [+] Backup: {os.path.basename(backup_path)}")
            except Exception as e:
                print(f"  [!] Backup error: {e}")
                return

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
    if hash_before and hash_after:
        print(f"  [+] Before:  {hash_before[:8]}...{hash_before[56:]}")
        print(f"  [+] After:   {hash_after[:8]}...{hash_after[56:]}")
    print(f"  [+] Done at  {time.strftime('%H:%M:%S')}")
    print()
    print("  Restart Antigravity and sign in.")


def do_restore(main_js_path, show_search_line=False):
    current_content = None
    try:
        with open(main_js_path, "r", encoding="utf-8") as f:
            current_content = f.read()
    except Exception:
        pass

    backup_ok, backup_has_warnings = warn_about_unsafe_backup(
        main_js_path, current_content=current_content
    )
    if not backup_ok:
        return

    backup_path = main_js_path + ".bak"

    # Разделяем "не найден" и "нечитаем"
    if not os.path.exists(backup_path):
        print(f"  [!] Backup file not found: {backup_path}")
        return
    try:
        with open(backup_path, "r", encoding="utf-8") as f:
            data = f.read()
    except Exception as e:
        print(f"  [!] Could not read backup: {e}")
        return

    # Проверка целостности по хэшу
    hash_ok = verify_backup_hash(backup_path)
    if hash_ok is False:
        print(color("  [!] Backup hash mismatch — file may be corrupted!", COLOR_RED))
        if not confirmed("Restore anyway?"):
            print("  [i] Restore cancelled.")
            return

    # Предупреждение, если бэкап сам является пропатченной версией
    if is_already_patched(data):
        print(color("  [!] Backup itself appears to be patched!", COLOR_YELLOW))
        if not confirmed("Restore this patched backup?"):
            print("  [i] Restore cancelled.")
            return

    restore_question = "Restore this backup anyway?" if backup_has_warnings else "Restore backup?"
    if not confirmed(restore_question):
        print("  [i] Restore cancelled.")
        return

    hash_before = file_hash(main_js_path)

    # Атомарная запись через временный файл
    tmp_path = main_js_path + ".tmp"
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            f.write(data)
        shutil.move(tmp_path, main_js_path)
    except Exception as e:
        print(f"\n  [!] Restore error: {e}")
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass
        return

    hash_after = file_hash(main_js_path)

    # Удаляем мета-файлы бэкапа — после восстановления они уже неактуальны
    for ext in (".version", ".sha256"):
        meta = backup_path + ext
        if os.path.exists(meta):
            try:
                os.remove(meta)
            except Exception:
                pass

    print_target_info(main_js_path, show_search_line=show_search_line)
    print()
    if hash_before and hash_after and hash_before != hash_after:
        print(f"  [+] Before: {hash_before[:8]}...{hash_before[56:]}")
        print(f"  [+] After:  {hash_after[:8]}...{hash_after[56:]}")
    print(f"  [+] Done at {time.strftime('%H:%M:%S')}")
    print("\n  [+] Restored from backup!")


# ---------------------------------------------------------------------------
# Точка входа
# ---------------------------------------------------------------------------

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
        if os.name == "nt":
            print("      python ag_patcher.py C:\\path\\to\\Antigravity")
        else:
            print("      python ag_patcher.py /usr/share/antigravity")
        input("\n  Press Enter to exit...")
        return

    redraw_main_screen(main_js_path, show_search_line=searched)

    while True:
        print(color("  1. Apply patch", COLOR_GREEN))
        print(color("  2. Restore from backup", COLOR_YELLOW))
        print(color("  3. Open GitHub repository", COLOR_CYAN))
        print(color("  0. Exit", COLOR_RED))

        choice = input(color("\n  > ", COLOR_CYAN, COLOR_BOLD)).strip()
        print()

        if choice in ("0", ""):
            return

        handled = True
        clear_screen()
        print_banner()

        if choice == "1":
            do_patch(main_js_path, show_search_line=searched)
        elif choice == "2":
            do_restore(main_js_path, show_search_line=searched)
        elif choice == "3":
            print_target_info(main_js_path, show_search_line=searched)
            print()
            url = "https://github.com/AvenCores/open-antigravity-unlock"
            webbrowser.open(url)
            print(f"  [+] Opening: {color(url, COLOR_CYAN)}")
        else:
            handled = False
            print("  [!] Invalid choice")
        print()

        if handled:
            input("  Press Enter to return to menu...")
            redraw_main_screen(main_js_path, show_search_line=searched)


if __name__ == "__main__":
    setup_console()
    if os.name == "nt" and not is_admin():
        if run_as_admin():
            sys.exit(0)
        else:
            print("  [!] Could not elevate privileges. The script may fail to modify files.")
    elif os.name == "posix" and not is_admin():
        print("  [!] Root access is required to patch files in /usr/share/antigravity.")
        if confirmed("Re-launch with sudo?"):
            try:
                os.execvp("sudo", ["sudo", sys.executable] + sys.argv)
            except Exception as e:
                print(f"  [!] Failed to re-launch with sudo: {e}")
                sys.exit(1)
        else:
            print(color("  [!] Proceeding without root. Write errors are possible.", COLOR_YELLOW))
            print()

    try:
        main()
    except KeyboardInterrupt:
        print("\n  [i] Exiting...")
        sys.exit(0)
