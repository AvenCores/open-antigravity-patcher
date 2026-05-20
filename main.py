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
import struct
import tempfile
from enum import Enum
from packaging.version import Version

try:
    import pwd
except ImportError:
    pwd = None

VERSION = "1.1.3"
MIN_AG_VERSION = "1.22.2"
USE_COLOR = False
AUTH_PATCH_SWITCH_VERSION = Version("1.23")
RUNTIME_SETTINGS_SWITCH_VERSION = Version("1.23")
CLOUD_CODE_ENDPOINT = "https://cloudcode-pa.googleapis.com"
RUNTIME_EXPERIMENTS_TO_DISABLE = (
    "CASCADE_DEFAULT_MODEL_OVERRIDE",
    "CASCADE_USE_EXPERIMENT_CHECKPOINTER",
    "CASCADE_NEW_MODELS_NUX",
    "CASCADE_NEW_WAVE_2_MODELS_NUX",
)
RUNTIME_EXPERIMENTS_VALUE = ",".join(RUNTIME_EXPERIMENTS_TO_DISABLE)

# Единственное место, где хранится GUID установщика Antigravity IDE
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
        + color("Region bypass for Antigravity IDE", COLOR_CYAN)
        + color("            ║", COLOR_CYAN, COLOR_BOLD)
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

    if sys.platform == "darwin":
        # На macOS приложение — .app-бандл, main.js лежит внутри Contents/Resources/app
        mac_candidates = [
            "/Applications/Antigravity IDE.app",
            os.path.expanduser("~/Applications/Antigravity IDE.app"),
        ]
        for app in mac_candidates:
            candidates.append(os.path.join(app, "Contents", "Resources", "app"))
    elif os.name == "posix":
        candidates.extend([
            "/usr/share/antigravity-ide",
            "/opt/Antigravity IDE",
            "/opt/Antigravity IDE/resources/app/out",
        ])

    if os.name == "nt":
        local_app_data = os.environ.get("LOCALAPPDATA")
        if local_app_data:
            candidates.append(os.path.join(local_app_data, "Programs", "Antigravity IDE"))
        pf = os.environ.get("PROGRAMFILES")
        if pf:
            candidates.append(os.path.join(pf, "Antigravity IDE"))
        pfx86 = os.environ.get("PROGRAMFILES(X86)")
        if pfx86:
            candidates.append(os.path.join(pfx86, "Antigravity IDE"))

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
            os.path.join("out", "main.js"),
            "main.js",
        ]:
            if os.path.exists(os.path.join(path, sub)):
                return path
    return ""


def find_main_js(root):
    # macOS: пользователь может передать путь к .app-бандлу напрямую
    if sys.platform == "darwin" and root.endswith(".app") and os.path.isdir(root):
        root = os.path.join(root, "Contents", "Resources", "app")

    for sub in [
        os.path.join("resources", "app", "out", "main.js"),
        os.path.join("resources", "app", "main.js"),
        os.path.join("out", "main.js"),
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
    """Читает версию Antigravity IDE из реестра Windows или package.json на Linux."""
    if os.name == "posix":
        # Пробуем менеджеры пакетов (apt, rpm) с разными именами
        pkg_names = ["antigravity-ide", "antigravity-ide-bin", "antigravity-ide-custom"]
        
        # dpkg-query (Debian/Ubuntu)
        for pkg in pkg_names:
            try:
                result = subprocess.run(
                    ["dpkg-query", "-W", "-f=${Version}", pkg],
                    capture_output=True, text=True,
                )
                if result.returncode == 0:
                    ver = result.stdout.strip()
                    if ver:
                        return ver
            except Exception:
                pass

        # rpm (Fedora/RHEL/openSUSE)
        for pkg in pkg_names:
            try:
                result = subprocess.run(
                    ["rpm", "-q", "--queryformat", "%{VERSION}", pkg],
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
    Проверяет версию Antigravity IDE.
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
# Бэкап — ТОЛЬКО main.js.bak, без метаданных
# ---------------------------------------------------------------------------


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


def find_app_bundle(path):
    """Поднимается вверх от path до первой директории, оканчивающейся на .app.

    Используется только на macOS, чтобы определить корень .app-бандла
    для переподписи после модификации main.js.
    """
    p = os.path.abspath(path)
    while p and p != os.path.dirname(p):
        if p.endswith(".app"):
            return p
        p = os.path.dirname(p)
    return ""


def resign_macos_bundle(main_js_path):
    """Переподписывает .app ad-hoc подписью после изменения main.js.

    На macOS любая модификация файла внутри подписанного .app-бандла
    нарушает code signature. Electron-приложения с Hardened Runtime
    после этого падают при запуске. codesign --force --sign - кладёт
    ad-hoc подпись (без Developer ID), чего достаточно для локального
    запуска. Дополнительно снимается атрибут com.apple.quarantine,
    чтобы Gatekeeper не показывал предупреждение.
    """
    if sys.platform != "darwin":
        return

    app_path = find_app_bundle(main_js_path)
    if not app_path:
        # main.js лежит не внутри .app (например, portable-копия) — пропускаем
        return

    print(f"  [*] Re-signing {os.path.basename(app_path)} (ad-hoc)...")
    try:
        subprocess.run(
            ["codesign", "--force", "--deep", "--sign", "-", app_path],
            check=True, capture_output=True, text=True,
        )
        print(color("  [+] Ad-hoc signature applied", COLOR_GREEN))
    except FileNotFoundError:
        print(color("  [!] codesign not found — install Xcode Command Line Tools", COLOR_YELLOW))
        return
    except subprocess.CalledProcessError as e:
        stderr = (e.stderr or "").strip()
        print(color(f"  [!] codesign failed: {stderr}", COLOR_YELLOW))
        return

    try:
        subprocess.run(
            ["xattr", "-dr", "com.apple.quarantine", app_path],
            check=False, capture_output=True,
        )
    except FileNotFoundError:
        pass


def format_bytes(size_bytes):
    if size_bytes >= 1024 * 1024:
        return f"{size_bytes / 1024 / 1024:.1f} MB"
    if size_bytes >= 1024:
        return f"{size_bytes / 1024:.1f} KB"
    return f"{size_bytes} B"


# ---------------------------------------------------------------------------
# Runtime settings workaround
# ---------------------------------------------------------------------------

def get_posix_invoking_user_home():
    """Returns the invoking user's home on POSIX, even when running via sudo."""
    if os.name != "posix":
        return ""

    if pwd is not None:
        sudo_uid = os.environ.get("SUDO_UID")
        if sudo_uid:
            try:
                return pwd.getpwuid(int(sudo_uid)).pw_dir
            except Exception:
                pass

        sudo_user = os.environ.get("SUDO_USER")
        if sudo_user:
            try:
                return pwd.getpwnam(sudo_user).pw_dir
            except Exception:
                pass

    home = os.environ.get("HOME")
    if home:
        return home

    return os.path.expanduser("~")


def get_user_settings_path():
    """Returns the Antigravity IDE user settings.json path for the current OS/user."""
    if os.name == "nt":
        app_data = os.environ.get("APPDATA")
        if app_data:
            return os.path.join(app_data, "Antigravity IDE", "User", "settings.json")
        return ""

    if sys.platform == "darwin":
        return os.path.join(
            get_posix_invoking_user_home(),
            "Library",
            "Application Support",
            "Antigravity IDE",
            "User",
            "settings.json",
        )

    if os.name == "posix":
        if os.environ.get("SUDO_USER") or os.environ.get("SUDO_UID"):
            config_home = os.path.join(get_posix_invoking_user_home(), ".config")
        else:
            config_home = os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")
        return os.path.join(config_home, "Antigravity IDE", "User", "settings.json")

    return ""


def get_user_data_dir():
    """Returns the Antigravity IDE user data directory."""
    path = get_user_settings_path()
    if not path:
        return ""
    # settings.json is in <data_dir>/User/settings.json
    return os.path.dirname(os.path.dirname(path))


def fix_posix_permissions(path):
    """Ensures the path and its contents are owned by the invoking user on POSIX when running via sudo."""
    if os.name != "posix" or os.getuid() != 0:
        return

    sudo_uid = os.environ.get("SUDO_UID")
    sudo_gid = os.environ.get("SUDO_GID")

    if sudo_uid and sudo_gid:
        try:
            subprocess.run(["chown", "-R", f"{sudo_uid}:{sudo_gid}", path], check=False)
        except Exception:
            pass


def backup_json_file(path):
    if not os.path.exists(path):
        return ""

    base = f"{path}.bak-{time.strftime('%Y%m%d-%H%M%S')}"
    backup_path = base
    counter = 1
    while os.path.exists(backup_path):
        counter += 1
        backup_path = f"{base}-{counter}"

    shutil.copy2(path, backup_path)
    return backup_path


def patch_runtime_settings(ag_version=None):
    """Temporary workaround: pins the stable endpoint and disables known bad experiments."""
    if ag_version is not None and ag_version < RUNTIME_SETTINGS_SWITCH_VERSION:
        return {
            "Name": "temporary runtime settings workaround",
            "Applied": False,
            "Detail": f"skipped for Antigravity IDE < {RUNTIME_SETTINGS_SWITCH_VERSION}",
        }

    settings_path = get_user_settings_path()
    if not settings_path:
        return {
            "Name": "temporary runtime settings workaround",
            "Applied": False,
            "Detail": "settings path not detected",
        }

    settings_dir = os.path.dirname(settings_path)
    if not os.path.isdir(settings_dir):
        try:
            os.makedirs(settings_dir, exist_ok=True)
            # Fix permissions on POSIX if we just created the dir as root
            fix_posix_permissions(settings_dir)
        except Exception as e:
            return {
                "Name": "temporary runtime settings workaround",
                "Applied": False,
                "Detail": f"could not create settings directory: {e}",
            }

    settings = {}
    if os.path.exists(settings_path):
        try:
            with open(settings_path, "r", encoding="utf-8") as f:
                raw = f.read()
            settings = json.loads(raw) if raw.strip() else {}
        except Exception as e:
            return {
                "Name": "temporary runtime settings workaround",
                "Applied": False,
                "Detail": f"settings.json parse error: {e}",
            }

        if not isinstance(settings, dict):
            return {
                "Name": "temporary runtime settings workaround",
                "Applied": False,
                "Detail": "settings.json root is not an object",
            }

    before = json.dumps(settings, sort_keys=True, ensure_ascii=False)

    settings["jetski.cloudCodeUrl"] = CLOUD_CODE_ENDPOINT
    settings["codeiumDev.forceDisableExperiments"] = RUNTIME_EXPERIMENTS_VALUE

    env = settings.get("codeiumDev.languageServerEnv", {})
    if not isinstance(env, dict):
        env = {}
    env["BORG_DISABLE_EXPERIMENTS"] = RUNTIME_EXPERIMENTS_VALUE
    env["BORG_EXPERIMENTS"] = ""
    settings["codeiumDev.languageServerEnv"] = env

    after = json.dumps(settings, sort_keys=True, ensure_ascii=False)
    if after == before:
        return {
            "Name": "temporary runtime settings workaround",
            "Applied": False,
            "Detail": "already present",
        }

    backup_path = ""
    try:
        backup_path = backup_json_file(settings_path)
        with open(settings_path, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=4, ensure_ascii=False)
            f.write("\n")
    except Exception as e:
        return {
            "Name": "temporary runtime settings workaround",
            "Applied": False,
            "Detail": f"write error: {e}",
        }

    detail = f"updated {settings_path}"
    if backup_path:
        detail += f"; backup: {os.path.basename(backup_path)}"
    return {
        "Name": "temporary runtime settings workaround",
        "Applied": True,
        "Detail": detail,
    }


def print_runtime_settings_result(result):
    icon = "  ✓" if result.get("Applied") else "  ✗"
    detail = f" — {result.get('Detail')}" if result.get("Detail") else ""
    print(f"{icon} {result['Name']}{detail}")


# ---------------------------------------------------------------------------
# Патчи (каждый патч — отдельная функция)
# ---------------------------------------------------------------------------

RE_AUTH_IS_GOOGLE_INTERNAL = re.compile(
    r'if\(\s*(?P<prefix>(?:this\.[A-Za-z_$][\w$]*\.send\(\{type:[^}]+\}\)\s*,\s*)?'
    r'this\.[A-Za-z_$][\w$]*\.resetIsTierGCPTos\(\)\s*,\s*)'
    r'this\.[A-Za-z_$][\w$]*\.isGoogleInternal\s*\)'
)
RE_AUTH_IS_GOOGLE_INTERNAL_OLD = re.compile(
    r'if\(\s*(?P<prefix>this\.[A-Za-z_$][\w$]*\.resetIsTierGCPTos\(\)\s*,\s*)'
    r'this\.[A-Za-z_$][\w$]*\.isGoogleInternal\s*\)'
)
RE_AUTH_IS_GOOGLE_INTERNAL_NEW = re.compile(
    r'if\(\s*(?P<prefix>this\.[A-Za-z_$][\w$]*\.send\(\{type:[^}]+\}\)\s*,\s*'
    r'this\.[A-Za-z_$][\w$]*\.resetIsTierGCPTos\(\)\s*,\s*)'
    r'this\.[A-Za-z_$][\w$]*\.isGoogleInternal\s*\)'
)


def _patch_is_google_internal(content):
    """if(isGoogleInternal) → if(true) — forces internal Google path bypassing geo/eligibility checks."""
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


def _patch_is_google_internal_comma(content, ag_version=None):
    """if(...resetIsTierGCPTos(),this.Y.isGoogleInternal) → if(...resetIsTierGCPTos(),true).

    Версионный выбор auth-паттерна:
    < 1.23:
    if(this.w.resetIsTierGCPTos(),this.t.isGoogleInternal){...}

    >= 1.23:
    if(this.t.send({type:t.isGcpTos?"GCP_SIGN_IN":"SIGN_IN"}),this.y.resetIsTierGCPTos(),this.w.isGoogleInternal){...}
    """
    if ag_version is not None and ag_version < AUTH_PATCH_SWITCH_VERSION:
        auth_regex = RE_AUTH_IS_GOOGLE_INTERNAL_OLD
        pattern_label = f"< {AUTH_PATCH_SWITCH_VERSION}"
    elif ag_version is not None:
        auth_regex = RE_AUTH_IS_GOOGLE_INTERNAL_NEW
        pattern_label = f">= {AUTH_PATCH_SWITCH_VERSION}"
    else:
        auth_regex = RE_AUTH_IS_GOOGLE_INTERNAL
        pattern_label = "auto"

    matches = [m.group(0) for m in auth_regex.finditer(content)]
    new_content = auth_regex.sub(r"if(\g<prefix>true)", content)
    applied = new_content != content
    return new_content, {
        "Name": "comma isGoogleInternal → true (auth)",
        "Applied": applied,
        "Detail": (
            f"replaced {len(matches)} auth occurrence(s) using {pattern_label} pattern"
            if applied else
            f"{pattern_label} pattern not found"
        ),
    }


def _patch_ide_name(content):
    """ideName → antigravity-insiders"""
    new_content = content.replace('ideName:"antigravity"', 'ideName:"antigravity-insiders"')
    return new_content, {
        "Name": "ideName → antigravity-insiders",
        "Applied": new_content != content,
        "Detail": "",
    }


def _patch_ineligible_screen(content):
    """Патч экрана ineligible (screen 4) в v1.22+.

    Заменяет spread тернар ...s?{}:{errorType:"ineligible",...}
    на ...s?{}:{} — ineligible ошибка не отправляется.
    """
    old = '...s?{}:{errorType:"ineligible",reason:a,verificationUrl:i}'
    new = '...s?{}:{}'
    if old in content:
        content = content.replace(old, new)
        return content, {
            "Name": "ineligible screen bypass (v1.22+)",
            "Applied": True,
            "Detail": "Replaced ineligible spread with empty object",
        }

    return content, {
        "Name": "ineligible screen bypass",
        "Applied": False,
        "Detail": "pattern not found",
    }


def apply_patches_minimal(content, ag_version=None):
    """Для v1.22+: version-aware auth patch + ideName + ineligible."""
    results = []
    for patch_fn in (_patch_is_google_internal, _patch_ide_name, _patch_ineligible_screen):
        content, result = patch_fn(content)
        results.append(result)
    content, result = _patch_is_google_internal_comma(content, ag_version=ag_version)
    results.insert(1, result)
    return content, results


def is_already_patched(content):
    # Убраны прямой и auth-вариант isGoogleInternal, ideName пропатчен
    has_unpatched_simple = bool(re.search(r'if\(this\.[a-zA-Z_$]+\.isGoogleInternal\)', content))
    has_unpatched_auth = bool(RE_AUTH_IS_GOOGLE_INTERNAL.search(content))
    has_ide = 'ideName:"antigravity-insiders"' in content
    return not has_unpatched_simple and not has_unpatched_auth and has_ide


# ---------------------------------------------------------------------------
# UI-утилиты
# ---------------------------------------------------------------------------

def clean_path(raw_path):
    return raw_path.strip().strip('"').strip("'")


def resolve_target_path(raw_path):
    if not raw_path:
        return ""
    cleaned = clean_path(raw_path)
    if not cleaned:
        return ""
    expanded = os.path.expandvars(os.path.expanduser(cleaned))
    resolved = os.path.abspath(expanded)
    
    # Если указана директория, пробуем найти в ней main.js
    if os.path.isdir(resolved):
        found = find_main_js(resolved)
        return found if found else resolved
    return resolved


def pause():
    input("  Press Enter to return to menu...")


def print_launch_examples():
    script_name = os.path.basename(sys.argv[0]) or "main.py"
    cmd = script_name if getattr(sys, "frozen", False) else f"python {script_name}"

    print(f"  [i] Usage examples with custom path:")
    print(f"      Windows: {color(f'{cmd} \"C:\\Path\\To\\Antigravity IDE\"', COLOR_YELLOW)}")
    print(f"      macOS:   {color(f'{cmd} \"/Applications/Antigravity IDE.app\"', COLOR_YELLOW)}")
    print(f"      Linux:   {color(f'{cmd} \"/usr/share/antigravity-ide\"', COLOR_YELLOW)}")


def print_path_examples():
    print(f"  [i] Path examples:")
    print(f"      Windows: {color(r'C:\\Users\\Name\\AppData\\Local\\Programs\\Antigravity IDE', COLOR_YELLOW)}")
    print(f"      macOS:   {color('/Applications/Antigravity IDE.app', COLOR_YELLOW)}")
    print(f"      Linux:   {color('/usr/share/antigravity-ide', COLOR_YELLOW)}")


def prompt_yn(question):
    question = question.rstrip()
    prompt = f"  [?] {question} ({color('y', COLOR_GREEN)}/{color('n', COLOR_RED)}): "
    return input(prompt).strip().lower()


def confirmed(question):
    """Возвращает True, если пользователь ответил 'y'."""
    return prompt_yn(question) == "y"


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
            
            ver_str = get_ag_version(main_js_path)
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


# ---------------------------------------------------------------------------
# Предупреждения о небезопасном бэкапе
# ---------------------------------------------------------------------------

def warn_about_unsafe_backup(main_js_path, installed_version_str=None, current_content=None):
    backup_path = main_js_path + ".bak"
    if not os.path.exists(backup_path):
        return True, False

    backup_size = file_size(backup_path)
    current_size = file_size(main_js_path)
    warnings = []

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
    elif backup_size < 4096 or (current_size > 0 and backup_size < current_size // 10):
        warnings.append(
            f"backup is much smaller than expected "
            f"({format_bytes(backup_size)} vs {format_bytes(current_size)})"
        )

    if not warnings:
        return True, False

    for warning in warnings:
        print(color(f"  [!] Backup warning: {warning}", COLOR_YELLOW))
    print(color("  [!] Restoring this backup may break Antigravity IDE.", COLOR_YELLOW))
    print(color(f"  [i] Backup kept: {os.path.basename(backup_path)}", COLOR_YELLOW))
    return True, True


# ---------------------------------------------------------------------------
# Операции: патч и восстановление
# ---------------------------------------------------------------------------

def do_patch(main_js_path, show_search_line=False):
    if not os.path.isfile(main_js_path):
        print(color(f"  [!] Target is not a file: {main_js_path}", COLOR_RED))
        print(color("  [i] Please select a valid main.js file or Antigravity IDE folder.", COLOR_YELLOW))
        return

    ver_status, ver_str = check_ag_version(main_js_path)
    parsed_version = parse_version_safe(ver_str)

    if ver_status == VersionStatus.TOO_OLD:
        print(color(f"  [!] Unsupported version: {ver_str}", COLOR_RED))
        print(color(f"  [!] Minimum required: {MIN_AG_VERSION}", COLOR_RED))
        print("  [i] Please update Antigravity IDE and try again.")
        if not confirmed("Proceed anyway?"):
            return
    elif ver_status == VersionStatus.NOT_FOUND:
        print(color("  [!] Could not detect Antigravity IDE version (registry key not found).", COLOR_YELLOW))
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
    runtime_settings_checked = False

    if current_is_patched:
        print("  [i] File appears already patched.")
        print("  [*] Applying runtime settings workaround...")
        print_runtime_settings_result(patch_runtime_settings(parsed_version))
        runtime_settings_checked = True
        if not confirmed("Apply main.js patches anyway?"):
            return

    # --- БЭКАП — копируем файл ДО любых изменений ---
    backup_path = main_js_path + ".bak"

    if not os.path.exists(backup_path) and not current_is_patched:
        print("  [*] Creating backup...")
        try:
            shutil.copy2(main_js_path, backup_path)
            print(f"  [+] Backup: {os.path.basename(backup_path)} "
                  f"({format_bytes(file_size(backup_path))})")
        except Exception as e:
            print(f"  [!] Backup error: {e}")
            return
    elif os.path.exists(backup_path):
        print("  [i] Backup already exists — skipping")
    elif current_is_patched:
        print(color("  [!] main.js is already patched — no backup needed", COLOR_YELLOW))

    hash_before = file_hash(main_js_path)

    print("  [*] Applying patches...")
    print()

    # Для v1.22+ auth-патч выбирается по версии: <1.23 старый, >=1.23 новый.
    new_content, results = apply_patches_minimal(content, ag_version=parsed_version)

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
    resign_macos_bundle(main_js_path)
    if not runtime_settings_checked:
        print("  [*] Applying runtime settings workaround...")
        print_runtime_settings_result(patch_runtime_settings(parsed_version))
    print(f"  [+] Patches: {applied}/{len(results)} applied")
    if hash_before and hash_after:
        print(f"  [+] Before:  {hash_before[:8]}...{hash_before[56:]}")
        print(f"  [+] After:   {hash_after[:8]}...{hash_after[56:]}")
    print(f"  [+] Done at  {time.strftime('%H:%M:%S')}")
    print()
    print("  Restart Antigravity IDE and sign in.")


def do_fix_429():
    data_dir = get_user_data_dir()
    if not data_dir or not os.path.isdir(data_dir):
        print(color("  [!] Antigravity IDE data directory not found.", COLOR_RED))
        return

    print(f"  [*] Data directory: {color(data_dir, COLOR_CYAN)}")
    print(color("  [!] This will reset your Antigravity IDE configuration (tokens, quota).", COLOR_YELLOW))
    print(color("  [!] Dialogues will be preserved, but you will need to sign in again.", COLOR_YELLOW))
    print(color("  [!] Ensure Antigravity IDE is COMPLETELY closed before proceeding.", COLOR_RED))

    if not confirmed("Proceed with the fix?"):
        return
    print()

    # Create backup name
    backup_base = data_dir + "_backup_" + time.strftime("%Y%m%d_%H%M%S")
    backup_dir = backup_base
    counter = 1
    while os.path.exists(backup_dir):
        backup_dir = f"{backup_base}_{counter}"
        counter += 1

    print(f"  [*] Moving current data to: {os.path.basename(backup_dir)}...")

    try:
        shutil.move(data_dir, backup_dir)
    except PermissionError:
        print(color("  [!] Permission denied: Could not move data directory.", COLOR_RED))
        print(color("  [!] Antigravity IDE is likely still running or holding files.", COLOR_RED))
        print("  [i] Close Antigravity IDE completely (check Task Manager) and try again.")
        return
    except Exception as e:
        print(color(f"  [!] Failed to move data directory: {e}", COLOR_RED))
        print("  [i] Try running the patcher as administrator.")
        return

    print(color("  [+] Data moved to backup", COLOR_GREEN))
    print("  [*] Creating fresh configuration...")

    try:
        # Recreate the data directory and User subfolder
        user_dir = os.path.join(data_dir, "User")
        os.makedirs(user_dir, exist_ok=True)

        # Restore storage folders (dialogues)
        storage_folders = ["globalStorage", "workspaceStorage"]
        restored_count = 0
        for folder in storage_folders:
            src = os.path.join(backup_dir, "User", folder)
            dst = os.path.join(user_dir, folder)
            if os.path.isdir(src):
                print(f"  [*] Restoring {folder}...")
                try:
                    shutil.copytree(src, dst)
                    restored_count += 1
                except Exception as e:
                    print(color(f"  [!] Could not restore {folder}: {e}", COLOR_YELLOW))
        
        if restored_count > 0:
            print(color(f"  [+] Restored {restored_count} storage folder(s)", COLOR_GREEN))
        else:
            print(color("  [i] No storage folders were restored", COLOR_YELLOW))

        # Fix permissions on POSIX if running as root
        fix_posix_permissions(data_dir)

        print(color("\n  [+] HTTP 429 fix applied successfully!", COLOR_GREEN, COLOR_BOLD))
        print("  [i] What to do now:")
        print("      1. Start Antigravity IDE.")
        print("      2. Sign in to your account.")
        print("      3. If you still see errors, run 'Apply patch' (Option 1) again.")
        print("      [!] Note: VPNs or other bypass methods might be detected by Google and cause 429 errors.")
        print(f"  [i] Your backup is safe at: {backup_dir}")

    except Exception as e:
        print(color(f"  [!] Error during restoration: {e}", COLOR_RED))
        print(color(f"  [i] Your backup is preserved at: {backup_dir}", COLOR_YELLOW))
        print("  [i] You can try to restore it manually if needed.")


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

    # Проверка размера бэкапа
    backup_size = file_size(backup_path)
    if backup_size <= 2048:
        print(color("  [!] Backup looks too small — may be corrupted!", COLOR_RED))
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
        os.replace(tmp_path, main_js_path)
    except Exception as e:
        print(f"\n  [!] Restore error: {e}")
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass
        return

    hash_after = file_hash(main_js_path)
    resign_macos_bundle(main_js_path)

    print_target_info(main_js_path, show_search_line=show_search_line)
    print()
    if hash_before and hash_after and hash_before != hash_after:
        print(f"  [+] Before: {hash_before[:8]}...{hash_before[56:]}")
        print(f"  [+] After:  {hash_after[:8]}...{hash_after[56:]}")
    print(f"  [+] Done at {time.strftime('%H:%M:%S')}")
    print("\n  [+] Restored from backup!")


# ---------------------------------------------------------------------------
# Antigravity (asar-based patching)
# ---------------------------------------------------------------------------

INTEGRITY_BLOCK_SIZE = 4 * 1024 * 1024
PACK_EXCLUDE_PATHS = {
    'downloaded_frontend_main.js',
    'frontend_patch_result.json',
    'dist/main.js.bak',
}

ANTIGRAVITY_INJECTION_CODE_TEMPLATE = """
    // Start local frontend patch server
    let localServerPort = 0;
    const frontendPatchCache = new Map();
    const frontendPatchFs = require('fs');
    const frontendPatchPath = require('path');
    const frontendPatchResultPath = frontendPatchPath.join('{dest_folder}', 'frontend_patch_result.json');
    const patchFrontendMainJs = (content) => {
        const results = [];
        if (content.includes('csrfToken') && content.includes('isGoogleInternal')) {
            let nextContent = content.split('isGoogleInternal:!1').join('isGoogleInternal:!0');
            let applied = nextContent !== content;
            results.push({
                name: 'isGoogleInternal:!1 -> isGoogleInternal:!0 (frontend)',
                applied,
                detail: applied ? 'Forced frontend isGoogleInternal to true' : 'isGoogleInternal:!1 not found',
            });
            content = nextContent;
            nextContent = content
                .split('SET_INELIGIBLE:{target:".loginError"')
                .join('SET_INELIGIBLE:{target:".signedIn"')
                .split('SET_ERROR:{target:".loginError"')
                .join('SET_ERROR:{target:".signedIn"');
            applied = nextContent !== content;
            results.push({
                name: 'SET_INELIGIBLE/SET_ERROR -> target:.signedIn (frontend)',
                applied,
                detail: applied ? 'Redirected ineligible/error states to signedIn' : 'loginError targets not found',
            });
            content = nextContent;
        }
        else {
            results.push({
                name: 'frontend marker check',
                applied: false,
                detail: 'csrfToken/isGoogleInternal markers not found',
            });
        }
        return { content, results };
    };
    const isFrontendMainPatched = (content) => {
        if (content.includes('csrfToken') && content.includes('isGoogleInternal')) {
            return !content.includes('isGoogleInternal:!1')
                && content.includes('SET_INELIGIBLE:{target:".signedIn"}');
        }
        return false;
    };
    const writeFrontendPatchResult = (sourceUrl, content, results) => {
        const verified = isFrontendMainPatched(content);
        try {
            frontendPatchFs.writeFileSync(frontendPatchResultPath, JSON.stringify({
                sourceUrl,
                verified,
                size: Buffer.byteLength(content, 'utf8'),
                results,
                at: new Date().toISOString(),
            }, null, 2));
        } catch (err) {
            console.error('[Debug] Failed to write frontend patch result:', err);
        }
        return verified;
    };
    const getPatchedFrontendMainJs = (sourceUrl) => {
        if (frontendPatchCache.has(sourceUrl)) {
            return frontendPatchCache.get(sourceUrl);
        }
        const patchPromise = new Promise((resolve, reject) => {
            const https = require('https');
            const agent = new https.Agent({ rejectUnauthorized: false });
            https.get(sourceUrl, { agent, headers: { 'Accept-Encoding': 'identity' } }, (upstream) => {
                const chunks = [];
                upstream.on('data', (chunk) => {
                    chunks.push(chunk);
                });
                upstream.on('end', () => {
                    const originalContent = Buffer.concat(chunks).toString('utf8');
                    const { content, results } = patchFrontendMainJs(originalContent);
                    for (const result of results) {
                        console.log(`[Debug] Frontend patch: ${result.name}; applied=${result.applied}; ${result.detail}`);
                    }
                    console.log(`[Debug] Frontend patch verification: ${writeFrontendPatchResult(sourceUrl, content, results) ? 'ok' : 'failed'}`);
                    resolve(Buffer.from(content, 'utf8'));
                });
                upstream.on('error', reject);
            }).on('error', reject);
        }).catch((err) => {
            frontendPatchCache.delete(sourceUrl);
            throw err;
        });
        frontendPatchCache.set(sourceUrl, patchPromise);
        return patchPromise;
    };
    try {
        const http = require('http');
        const localServer = http.createServer((req, res) => {
            const requestUrl = new URL(req.url || '/', `http://127.0.0.1:${localServerPort || 0}`);
            if (requestUrl.pathname === '/main.js') {
                const sourceUrl = requestUrl.searchParams.get('source');
                if (!sourceUrl) {
                    res.writeHead(400);
                    res.end();
                    return;
                }
                getPatchedFrontendMainJs(sourceUrl)
                    .then((content) => {
                    res.writeHead(200, {
                        'Content-Type': 'application/javascript; charset=utf-8',
                        'Access-Control-Allow-Origin': '*',
                        'Content-Length': content.length,
                    });
                    res.end(content);
                })
                    .catch((err) => {
                    console.error('[Debug] Local server failed to patch frontend main.js:', err);
                    res.writeHead(502);
                    res.end();
                });
                return;
            }
            res.writeHead(404);
            res.end();
        });
        localServer.listen(0, '127.0.0.1', () => {
            localServerPort = localServer.address().port;
            console.log(`[Debug] Local patch server listening on port ${localServerPort}`);
        });
    } catch (err) {
        console.error('[Debug] Failed to start local patch server:', err);
    }
    electron_1.session.defaultSession.webRequest.onBeforeRequest((details, callback) => {
        console.log(`[Network Request] ${details.url}`);
        if (details.url.endsWith('/main.js') && details.url.includes('127.0.0.1')) {
            if (localServerPort && !details.url.includes(`:${localServerPort}`)) {
                const redirectUrl = `http://127.0.0.1:${localServerPort}/main.js?source=${encodeURIComponent(details.url)}`;
                console.log(`[Debug] Redirecting main.js request to local patch server: ${redirectUrl}`);
                callback({ redirectURL: redirectUrl });
                return;
            }
        }
        callback({});
    });
"""

def align_to(value, alignment):
    remainder = value % alignment
    return value if remainder == 0 else value + (alignment - remainder)

def compute_integrity(file_path):
    full_hash = hashlib.sha256()
    block_hashes = []

    with open(file_path, 'rb') as f:
        while True:
            block = f.read(INTEGRITY_BLOCK_SIZE)
            if not block:
                break
            full_hash.update(block)
            block_hashes.append(hashlib.sha256(block).hexdigest())

    return {
        "algorithm": "SHA256",
        "hash": full_hash.hexdigest(),
        "blockSize": INTEGRITY_BLOCK_SIZE,
        "blocks": block_hashes,
    }

def find_unpacked_file(asar_path, current_path):
    resource_dir = os.path.dirname(asar_path)
    candidates = [
        asar_path + '.unpacked',
        os.path.join(resource_dir, 'app.asar.unpacked'),
        os.path.join(resource_dir, 'app1.asar.unpacked'),
    ]

    seen = set()
    for candidate_dir in candidates:
        if candidate_dir in seen:
            continue
        seen.add(candidate_dir)
        candidate_file = os.path.join(candidate_dir, current_path)
        if os.path.exists(candidate_file):
            return candidate_file

    return None

def extract_asar(asar_path, dest_dir):
    asar_path = os.path.abspath(asar_path)
    if not os.path.exists(asar_path):
        print(f"  [!] Error: ASAR file not found at '{asar_path}'")
        return False
        
    print(f"  [*] Extracting '{os.path.basename(asar_path)}' to temp directory...")
    
    with open(asar_path, 'rb') as f:
        try:
            pickle_header = struct.unpack('<I', f.read(4))[0]
            header_size = struct.unpack('<I', f.read(4))[0]
            json_size_plus_4 = struct.unpack('<I', f.read(4))[0]
            json_size = struct.unpack('<I', f.read(4))[0]
        except struct.error:
            print("  [!] Error: Invalid ASAR file format (unable to read header structure).")
            return False
        
        try:
            json_bytes = f.read(json_size)
            header = json.loads(json_bytes.decode('utf-8'))
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            print(f"  [!] Error: Failed to parse ASAR header JSON: {e}")
            return False
            
        payload_offset = 8 + header_size
        
        def extract_entry(entry, current_path):
            if 'files' in entry:
                dir_path = os.path.join(dest_dir, current_path)
                os.makedirs(dir_path, exist_ok=True)
                for name, child in entry['files'].items():
                    extract_entry(child, os.path.join(current_path, name))
            else:
                file_path = os.path.join(dest_dir, current_path)
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                
                if entry.get('unpacked'):
                    src_file = find_unpacked_file(asar_path, current_path)
                    if src_file:
                        shutil.copy2(src_file, file_path)
                    else:
                        print(f"  [!] Warning: Unpacked file '{current_path}' not found in external directory.")
                else:
                    offset = int(entry['offset'])
                    size = entry['size']
                    f.seek(payload_offset + offset)
                    data = f.read(size)
                    with open(file_path, 'wb') as out_f:
                        out_f.write(data)

        extract_entry(header, '')
        print("  [+] Extraction completed successfully.")
        return True

def get_unpacked_paths(asar_path):
    unpacked_paths = set()
    if not os.path.exists(asar_path):
        return unpacked_paths
        
    try:
        with open(asar_path, 'rb') as f:
            pickle_header = struct.unpack('<I', f.read(4))[0]
            header_size = struct.unpack('<I', f.read(4))[0]
            json_size_plus_4 = struct.unpack('<I', f.read(4))[0]
            json_size = struct.unpack('<I', f.read(4))[0]
            json_bytes = f.read(json_size)
            header = json.loads(json_bytes.decode('utf-8'))
            
            def collect_unpacked(entry, current_path):
                if 'files' in entry:
                    for name, child in entry['files'].items():
                        collect_unpacked(child, os.path.join(current_path, name) if current_path else name)
                else:
                    if entry.get('unpacked'):
                        unpacked_paths.add(current_path.replace('\\', '/'))
            
            collect_unpacked(header, '')
    except Exception as e:
        print(f"  [!] Warning: Could not read original ASAR header to check unpacked files: {e}")
        
    return unpacked_paths

def build_asar_tree(source_dir, unpacked_paths, payload_file, unpacked_dir):
    header = {"files": {}}
    current_offset = 0
    
    all_files = []
    for root, dirs, files in os.walk(source_dir):
        for file in files:
            full_path = os.path.join(root, file)
            rel_path = os.path.relpath(full_path, source_dir).replace('\\', '/')
            if rel_path in PACK_EXCLUDE_PATHS:
                continue
            all_files.append((rel_path, full_path))
            
    all_files.sort()
    
    for rel_path, full_path in all_files:
        size = os.path.getsize(full_path)
        is_unpacked = rel_path in unpacked_paths
        
        entry = {}
        entry["size"] = size
        entry["integrity"] = compute_integrity(full_path)
        if is_unpacked:
            entry["unpacked"] = True
            
            dest_unpacked_file = os.path.join(unpacked_dir, os.path.normpath(rel_path))
            os.makedirs(os.path.dirname(dest_unpacked_file), exist_ok=True)
            shutil.copy2(full_path, dest_unpacked_file)
        else:
            with open(full_path, 'rb') as f:
                data = f.read()
            payload_file.write(data)
            entry["offset"] = str(current_offset)
            current_offset += size
            
        parts = rel_path.split('/')
        current_node = header
        for part in parts[:-1]:
            if "files" not in current_node:
                current_node["files"] = {}
            if part not in current_node["files"]:
                current_node["files"][part] = {"files": {}}
            current_node = current_node["files"][part]
            
        if "files" not in current_node:
            current_node["files"] = {}
        current_node["files"][parts[-1]] = entry
        
    return header

def pack_asar(source_dir, asar_path, reference_asar_path=None):
    print(f"  [*] Packing '{source_dir}' to '{os.path.basename(asar_path)}'...")
    
    unpacked_paths = get_unpacked_paths(reference_asar_path or asar_path)
    if unpacked_paths:
        print(f"  [*] Found {len(unpacked_paths)} unpacked files to preserve.")
        
    unpacked_dir = asar_path + '.unpacked'
    if os.path.exists(unpacked_dir):
        try:
            shutil.rmtree(unpacked_dir)
        except Exception as e:
            print(f"  [!] Warning: Could not clear old unpacked directory: {e}")
    os.makedirs(unpacked_dir, exist_ok=True)
    
    temp_payload_fd, temp_payload_path = tempfile.mkstemp()
    try:
        with os.fdopen(temp_payload_fd, 'wb') as payload_file:
            header = build_asar_tree(source_dir, unpacked_paths, payload_file, unpacked_dir)
            
        json_bytes = json.dumps(header, separators=(',', ':')).encode('utf-8')
        json_size = len(json_bytes)
        json_payload_size = align_to(json_size + 4, 4)
        json_padding_size = json_payload_size - (json_size + 4)
        header_size = json_payload_size + 4
        pickle_header = 4
        
        temp_asar_fd, temp_asar_path = tempfile.mkstemp(dir=os.path.dirname(asar_path))
        try:
            with os.fdopen(temp_asar_fd, 'wb') as out_f:
                out_f.write(struct.pack('<I', pickle_header))
                out_f.write(struct.pack('<I', header_size))
                out_f.write(struct.pack('<I', json_payload_size))
                out_f.write(struct.pack('<I', json_size))
                out_f.write(json_bytes)
                if json_padding_size:
                    out_f.write(b'\0' * json_padding_size)
                
                with open(temp_payload_path, 'rb') as pay_f:
                    shutil.copyfileobj(pay_f, out_f)
            
            if os.path.exists(asar_path):
                try:
                    os.remove(asar_path)
                except PermissionError:
                    temp_old_path = asar_path + ".old"
                    if os.path.exists(temp_old_path):
                        try:
                            os.remove(temp_old_path)
                        except Exception:
                            pass
                    try:
                        os.rename(asar_path, temp_old_path)
                        print(f"  [*] Locked file renamed to {os.path.basename(temp_old_path)}")
                    except Exception as e:
                        print(f"  [!] Error: Could not overwrite or rename '{asar_path}' (locked by another process). {e}")
                        return False

            shutil.move(temp_asar_path, asar_path)
            print("  [+] Packing completed successfully.")
            
            if os.path.exists(unpacked_dir) and not os.listdir(unpacked_dir):
                os.rmdir(unpacked_dir)
                
            return True
        finally:
            if os.path.exists(temp_asar_path):
                try:
                    os.remove(temp_asar_path)
                except Exception:
                    pass
    finally:
        if os.path.exists(temp_payload_path):
            try:
                os.remove(temp_payload_path)
            except Exception:
                pass
    return False

def patch_antigravity_main_js(dest_folder, rollback=False):
    main_js_path = os.path.join(dest_folder, 'dist', 'main.js')
    backup_path = main_js_path + '.bak'
    
    if not os.path.exists(main_js_path):
        print(f"  [!] Error: main.js not found at {main_js_path}")
        return False

    with open(main_js_path, 'r', encoding='utf-8') as f:
        content = f.read()

    escaped_dest_folder = dest_folder.replace("\\", "/")
    injection_code = ANTIGRAVITY_INJECTION_CODE_TEMPLATE.replace("{dest_folder}", escaped_dest_folder)

    if rollback:
        if injection_code in content:
            patched_content = content.replace(injection_code, "")
            with open(main_js_path, 'w', encoding='utf-8') as f:
                f.write(patched_content)
            print("  [+] Successfully rolled back patch by removing the injected lines directly.")
            return True
        elif os.path.exists(backup_path):
            shutil.copy2(backup_path, main_js_path)
            print("  [+] Successfully rolled back patch using the backup file (main.js.bak).")
            return True
        else:
            print("  [!] Patch not found in main.js and backup file does not exist.")
            return False

    if not os.path.exists(backup_path):
        shutil.copy2(main_js_path, backup_path)
        print("  [*] Created backup of original main.js inside temp folder.")

    target_str = "(0, ipcHandlers_1.registerIpcHandlers)(storageManager);"
    if "patchFrontendMainJs" in content:
        print("  [i] Patch already applied to main.js.")
        return True
    if "downloaded_frontend_main.js" in content and os.path.exists(backup_path):
        with open(backup_path, 'r', encoding='utf-8') as f:
            content = f.read()
        print("  [i] Found old download-only patch; restored backup content before applying frontend patch proxy.")

    if target_str not in content:
        print(f"  [!] Error: Target line '{target_str}' not found in main.js")
        return False

    patched_content = content.replace(target_str, target_str + injection_code)
    
    with open(main_js_path, 'w', encoding='utf-8') as f:
        f.write(patched_content)
        
    print("  [+] Successfully patched main.js inside extracted ASAR.")
    return True

def find_antigravity_root():
    candidates = []

    if sys.platform == "darwin":
        mac_candidates = [
            "/Applications/Antigravity.app",
            os.path.expanduser("~/Applications/Antigravity.app"),
        ]
        for app in mac_candidates:
            if os.path.exists(app):
                candidates.append(app)
    elif os.name == "posix":
        candidates.extend([
            "/usr/share/antigravity",
            "/opt/Antigravity",
            "/opt/antigravity",
        ])

    if os.name == "nt":
        local_app_data = os.environ.get("LOCALAPPDATA")
        if local_app_data:
            candidates.append(os.path.join(local_app_data, "Programs", "Antigravity"))
            candidates.append(os.path.join(local_app_data, "Programs", "antigravity"))
        pf = os.environ.get("PROGRAMFILES")
        if pf:
            candidates.append(os.path.join(pf, "Antigravity"))
        pfx86 = os.environ.get("PROGRAMFILES(X86)")
        if pfx86:
            candidates.append(os.path.join(pfx86, "Antigravity"))

        try:
            import winreg
            hives = [
                (winreg.HKEY_CURRENT_USER, 'HKCU'),
                (winreg.HKEY_LOCAL_MACHINE, 'HKLM')
            ]
            subkeys = [
                r'SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall',
                r'SOFTWARE\Wow6432Node\Microsoft\Windows\CurrentVersion\Uninstall'
            ]
            for hive, hname in hives:
                for subkey in subkeys:
                    try:
                        with winreg.OpenKey(hive, subkey) as key:
                            info = winreg.QueryInfoKey(key)
                            for i in range(info[0]):
                                try:
                                    name = winreg.EnumKey(key, i)
                                    with winreg.OpenKey(key, name) as sub:
                                        disp = ''
                                        try:
                                            disp, _ = winreg.QueryValueEx(sub, 'DisplayName')
                                        except OSError:
                                            pass
                                        
                                        disp_lower = disp.lower()
                                        name_lower = name.lower()
                                        if ('antigravity' in disp_lower or 'antigravity' in name_lower) and \
                                           'ide' not in disp_lower and 'ide' not in name_lower and \
                                           'tools' not in disp_lower and 'tools' not in name_lower:
                                            
                                            try:
                                                icon_val, _ = winreg.QueryValueEx(sub, 'DisplayIcon')
                                                if icon_val:
                                                    icon_path = icon_val.split(',')[0].strip().strip('"')
                                                    if icon_path:
                                                        candidates.append(os.path.dirname(icon_path))
                                            except OSError:
                                                pass

                                            try:
                                                uninst_val, _ = winreg.QueryValueEx(sub, 'UninstallString')
                                                if uninst_val:
                                                    uninst_path = uninst_val.split('.exe')[0].strip().strip('"')
                                                    if uninst_path:
                                                        candidates.append(os.path.dirname(uninst_path + '.exe'))
                                            except OSError:
                                                pass
                                except OSError:
                                    pass
                    except OSError:
                        pass
        except ImportError:
            pass

    for path in candidates:
        path = os.path.abspath(path)
        if os.path.exists(os.path.join(path, "resources", "app.asar")) or \
           os.path.exists(os.path.join(path, "resources", "app1.asar")):
            return path
        if sys.platform == "darwin" and path.endswith(".app"):
            resources_path = os.path.join(path, "Contents", "Resources")
            if os.path.exists(os.path.join(resources_path, "app.asar")) or \
               os.path.exists(os.path.join(resources_path, "app1.asar")):
                return path

    for path in candidates:
        if os.path.isdir(path):
            return path

    return ""

def resolve_antigravity_paths(root):
    if sys.platform == "darwin" and root.endswith(".app"):
        asar = os.path.join(root, "Contents", "Resources", "app.asar")
        if not os.path.exists(asar):
            asar = os.path.join(root, "Contents", "Resources", "app1.asar")
        exe = os.path.join(root, "Contents", "MacOS", "Antigravity")
        return asar, exe

    asar = os.path.join(root, "resources", "app.asar")
    if not os.path.exists(asar):
        asar = os.path.join(root, "resources", "app1.asar")
    
    exe_name = "Antigravity"
    if os.name == "nt":
        exe_name += ".exe"
    exe = os.path.join(root, exe_name)
    return asar, exe

def is_antigravity_patched(asar_path):
    if not os.path.exists(asar_path):
        return False
    try:
        with open(asar_path, 'rb') as f:
            while True:
                chunk = f.read(1024 * 1024)
                if not chunk:
                    break
                if b"patchFrontendMainJs" in chunk:
                    return True
        return False
    except Exception:
        return False

def read_package_json_from_asar(asar_path):
    if not os.path.exists(asar_path):
        return None
    try:
        with open(asar_path, 'rb') as f:
            pickle_header = struct.unpack('<I', f.read(4))[0]
            header_size = struct.unpack('<I', f.read(4))[0]
            json_size_plus_4 = struct.unpack('<I', f.read(4))[0]
            json_size = struct.unpack('<I', f.read(4))[0]
            json_bytes = f.read(json_size)
            header = json.loads(json_bytes.decode('utf-8'))
            
            files = header.get('files', {})
            pkg_entry = files.get('package.json')
            if pkg_entry and 'offset' in pkg_entry and 'size' in pkg_entry:
                offset = int(pkg_entry['offset'])
                size = pkg_entry['size']
                payload_offset = 8 + header_size
                f.seek(payload_offset + offset)
                data = f.read(size)
                pkg_data = json.loads(data.decode('utf-8'))
                return pkg_data.get('version')
    except Exception:
        pass
    return None

def do_patch_antigravity(antigravity_root):
    if not antigravity_root or not os.path.isdir(antigravity_root):
        print(color(f"  [!] Antigravity root path not found: {antigravity_root}", COLOR_RED))
        return

    asar_path, exe_path = resolve_antigravity_paths(antigravity_root)
    if not os.path.exists(asar_path):
        print(color(f"  [!] ASAR file not found: {asar_path}", COLOR_RED))
        return

    if is_antigravity_patched(asar_path):
        print("  [i] Antigravity appears already patched.")
        if not confirmed("Apply patch anyway?"):
            return

    source_asar_path = asar_path + ".bak"
    legacy_backup = os.path.join(os.path.dirname(asar_path), "app_original.asar")
    if os.path.exists(legacy_backup) and not os.path.exists(source_asar_path):
        source_asar_path = legacy_backup

    if not os.path.exists(source_asar_path):
        print("  [*] Creating backup of original ASAR...")
        try:
            shutil.copy2(asar_path, source_asar_path)
            print(f"  [+] Backup: {os.path.basename(source_asar_path)} ({format_bytes(file_size(source_asar_path))})")
        except Exception as e:
            print(color(f"  [!] Backup error: {e}", COLOR_RED))
            return
    else:
        print(f"  [i] Backup of original ASAR already exists: {os.path.basename(source_asar_path)}")

    temp_dir = os.environ.get("TEMP")
    if not temp_dir:
        temp_dir = os.path.join(os.environ.get("LOCALAPPDATA"), "Temp")
    dest_folder = os.path.join(temp_dir, "ag_patcher_temp")

    if os.path.exists(dest_folder):
        try:
            shutil.rmtree(dest_folder)
        except Exception:
            pass
    os.makedirs(dest_folder, exist_ok=True)

    print("  [*] Extracting ASAR archive...")
    success = extract_asar(source_asar_path, dest_folder)
    if not success:
        print(color("  [!] Extraction failed.", COLOR_RED))
        return

    print("  [*] Modifying files...")
    if patch_antigravity_main_js(dest_folder, rollback=False):
        print("  [*] Packing ASAR archive...")
        if pack_asar(dest_folder, asar_path, reference_asar_path=source_asar_path):
            print(color("  [+] Antigravity app.asar patched successfully!", COLOR_GREEN))
            resign_macos_bundle(asar_path)
            
            if os.path.exists(exe_path):
                print(f"  [*] Launching application to verify: {exe_path}")
                target_file = os.path.join(dest_folder, "frontend_patch_result.json")
                if os.path.exists(target_file):
                    try:
                        os.remove(target_file)
                    except Exception:
                        pass
                
                try:
                    process = subprocess.Popen([exe_path], cwd=antigravity_root)
                    print("  [*] Waiting for frontend_patch_result.json to be written...")
                    
                    start_time = time.time()
                    timeout = 120
                    patched = False
                    
                    while time.time() - start_time < timeout:
                        if os.path.exists(target_file) and os.path.getsize(target_file) > 0:
                            patched = True
                            break
                        time.sleep(0.5)
                        
                    if patched:
                        print(color(f"  [+] Frontend patch result verified: {target_file}", COLOR_GREEN))
                    else:
                        print(color("  [!] Timeout: frontend_patch_result.json was not written.", COLOR_YELLOW))
                        print("  [i] The patch was applied, but verification timed out. You may need to sign in manually.")
                        
                    print("  [*] Stopping the application...")
                    process.terminate()
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        print("  [!] Forcing application to stop...")
                        process.kill()
                        process.wait()
                except Exception as e:
                    print(color(f"  [!] Error launching/stopping application: {e}", COLOR_YELLOW))
            else:
                print(color(f"  [!] Executable not found at {exe_path}. Cannot auto-verify.", COLOR_YELLOW))
        else:
            print(color("  [!] Packing failed.", COLOR_RED))
    else:
        print(color("  [!] Patching main.js failed.", COLOR_RED))

def do_restore_antigravity(antigravity_root):
    if not antigravity_root or not os.path.isdir(antigravity_root):
        print(color(f"  [!] Antigravity root path not found: {antigravity_root}", COLOR_RED))
        return

    asar_path, exe_path = resolve_antigravity_paths(antigravity_root)
    source_asar_path = asar_path + ".bak"
    legacy_backup = os.path.join(os.path.dirname(asar_path), "app_original.asar")
    if os.path.exists(legacy_backup) and not os.path.exists(source_asar_path):
        source_asar_path = legacy_backup

    if not os.path.exists(source_asar_path):
        print(color(f"  [!] Original ASAR backup not found: {source_asar_path}", COLOR_RED))
        print("  [*] Attempting in-place rollback by extracting and patching...")
        if not os.path.exists(asar_path):
            print(color(f"  [!] Target ASAR file not found: {asar_path}", COLOR_RED))
            return
            
        temp_dir = os.environ.get("TEMP")
        if not temp_dir:
            temp_dir = os.path.join(os.environ.get("LOCALAPPDATA"), "Temp")
        dest_folder = os.path.join(temp_dir, "ag_patcher_temp")

        if os.path.exists(dest_folder):
            try:
                shutil.rmtree(dest_folder)
            except Exception:
                pass
        os.makedirs(dest_folder, exist_ok=True)

        print("  [*] Extracting ASAR...")
        if not extract_asar(asar_path, dest_folder):
            print(color("  [!] Extraction failed.", COLOR_RED))
            return

        print("  [*] Performing rollback in main.js...")
        if patch_antigravity_main_js(dest_folder, rollback=True):
            print("  [*] Packing ASAR...")
            if pack_asar(dest_folder, asar_path):
                print(color("  [+] Antigravity rollback completed successfully!", COLOR_GREEN))
                resign_macos_bundle(asar_path)
            else:
                print(color("  [!] Packing failed.", COLOR_RED))
        else:
            print(color("  [!] Rollback failed (patch not found or backup missing).", COLOR_RED))
        return

    print(f"  [*] Found original ASAR backup: {os.path.basename(source_asar_path)}")
    if not confirmed("Restore original ASAR from backup?"):
        return

    try:
        if os.path.exists(asar_path):
            try:
                os.remove(asar_path)
            except PermissionError:
                temp_old_path = asar_path + ".old"
                if os.path.exists(temp_old_path):
                    try:
                        os.remove(temp_old_path)
                    except Exception:
                        pass
                os.rename(asar_path, temp_old_path)
        
        shutil.copy2(source_asar_path, asar_path)
        print(color("  [+] Restored original ASAR from backup!", COLOR_GREEN))
        resign_macos_bundle(asar_path)
        print(f"  [i] Backup file {os.path.basename(source_asar_path)} was kept.")
    except Exception as e:
        print(color(f"  [!] Failed to restore backup: {e}", COLOR_RED))

def assign_custom_path(raw_path):
    resolved = resolve_target_path(raw_path)
    if not os.path.exists(resolved):
        return None, None
        
    if os.path.isfile(resolved) and resolved.endswith("main.js"):
        return resolved, None
        
    asar_path, _ = resolve_antigravity_paths(resolved)
    if os.path.exists(asar_path):
        return None, resolved
        
    main_js = find_main_js(resolved)
    if main_js:
        return main_js, None
        
    if os.path.isfile(resolved):
        return resolved, None
    else:
        return None, resolved


# ---------------------------------------------------------------------------
# Точка входа
# ---------------------------------------------------------------------------

def main():
    print_banner()

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
            url = "https://github.com/AvenCores/open-antigravity-unlock"
            webbrowser.open(url)
            print(f"  [+] Opening: {color(url, COLOR_CYAN)}")
        elif choice == "7":
            print("  [i] Enter the path to Antigravity IDE folder, Antigravity folder, or main.js file.")
            print_path_examples()
            raw = input(color("\n  Path > ", COLOR_CYAN, COLOR_BOLD)).strip()
            if raw:
                new_main_js, new_ag_root = assign_custom_path(raw)
                if new_main_js or new_ag_root:
                    main_js_path = new_main_js if new_main_js else ""
                    antigravity_root = new_ag_root if new_ag_root else ""
                    searched = False
                    print(color("  [+] Target paths updated successfully!", COLOR_GREEN))
                else:
                    print(color("  [!] Could not resolve a valid target from the provided path.", COLOR_RED))
            handled = True
        else:
            handled = False
            print("  [!] Invalid choice")
        print()

        if handled:
            pause()
            redraw_main_screen(main_js_path, antigravity_root, show_search_line=searched)


if __name__ == "__main__":
    setup_console()
    if os.name == "nt" and not is_admin():
        if run_as_admin():
            sys.exit(0)
        else:
            print("  [!] Could not elevate privileges. The script may fail to modify files.")
    elif os.name == "posix" and not is_admin():
        print("  [!] Root access is required to patch files in /usr/share/antigravity-ide.")
        if confirmed("Re-launch with sudo?"):
            try:
                if getattr(sys, "frozen", False):
                    args = ["sudo", sys.executable] + sys.argv[1:]
                else:
                    args = ["sudo", sys.executable] + sys.argv
                os.execvp("sudo", args)
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