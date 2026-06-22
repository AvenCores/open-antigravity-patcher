import os
import sys
import json
import subprocess
from enum import Enum
from packaging.version import Version
from patcher.constants import AG_REGISTRY_SUBKEY, MIN_AG_VERSION


class VersionStatus(Enum):
    OK = "ok"
    TOO_OLD = "too_old"
    NOT_FOUND = "not_found"
    PARSE_ERROR = "parse_error"


def clean_path(raw_path):
    return raw_path.strip().strip('"').strip("'")


def find_portable_candidates(search_type="ide"):
    """Ищет портативные версии в пользовательских папках и на других дисках."""
    import string
    roots = []

    # 1. Получаем домашнюю папку пользователя
    from patcher.utils.file import get_posix_invoking_user_home
    home = ""
    if sys.platform != "win32":
        home = get_posix_invoking_user_home()
    if not home:
        home = os.path.expanduser("~")

    # Добавляем специфичные папки пользователя (включая русские локализации и нижний регистр)
    if home and os.path.isdir(home):
        standard_subs = [
            "Downloads", "Загрузки", "downloads", "загрузки",
            "Desktop", "Рабочий стол", "desktop", "рабочий стол",
            "Documents", "Документы", "documents", "документы"
        ]
        for sub in standard_subs:
            p = os.path.join(home, sub)
            if os.path.isdir(p):
                roots.append(p)

    # 2. На Linux просим систему дать точные пути через xdg-user-dir
    if sys.platform != "win32" and os.name == "posix":
        import subprocess
        sudo_user = os.environ.get("SUDO_USER")
        for folder_type in ["DOWNLOAD", "DESKTOP", "DOCUMENTS"]:
            try:
                cmd = ["xdg-user-dir", folder_type]
                if sudo_user:
                    cmd = ["sudo", "-u", sudo_user, "xdg-user-dir", folder_type]
                res = subprocess.run(cmd, capture_output=True, text=True, check=False)
                if res.returncode == 0:
                    path = res.stdout.strip()
                    if path and os.path.isdir(path):
                        roots.append(path)
            except Exception:
                pass

    # 3. Текущая директория запуска
    cwd = os.getcwd()
    if cwd and os.path.isdir(cwd):
        roots.append(cwd)

    # 4. Корни других дисков для Windows
    if os.name == "nt":
        for letter in string.ascii_uppercase:
            if letter == "C":
                continue
            drive = f"{letter}:\\"
            if os.path.exists(drive):
                roots.append(drive)

    # 5. Домашняя папка целиком (как крайний вариант в самом конце)
    if home and os.path.isdir(home):
        roots.append(home)

    # Убираем дубликаты, сохраняя порядок приоритетности
    seen = set()
    unique_roots = []
    for r in roots:
        r_abs = os.path.abspath(r)
        if r_abs not in seen:
            seen.add(r_abs)
            unique_roots.append(r_abs)
    roots = unique_roots

    candidates = []
    visited_dirs = 0
    max_dirs = 1500

    for root in roots:
        if not os.path.isdir(root):
            continue
        for dirpath, dirnames, filenames in os.walk(root):
            visited_dirs += 1
            if visited_dirs > max_dirs:
                break

            # Исключаем тяжелые/системные папки
            prune_dirs = {
                ".git", "node_modules", "AppData", "Application Data", "Library",
                "System Volume Information", "$RECYCLE.BIN", "Windows", "Program Files",
                "Program Files (x86)", "usr", "var", "sys", "proc", "dev", "dist", "build",
                "__pycache__", ".idea", ".vscode"
            }
            # Фильтруем dirnames на месте
            dirnames[:] = [d for d in dirnames if d.lower() not in [p.lower() for p in prune_dirs] and not d.startswith('.')]

            # Вычисляем глубину относительно корня поиска
            try:
                rel = os.path.relpath(dirpath, root)
                if rel == ".":
                    depth = 0
                else:
                    depth = len(rel.replace("\\", "/").split("/"))
            except ValueError:
                depth = 999

            if depth >= 3:
                dirnames[:] = []  # Не спускаемся глубже

            # Проверяем, подходит ли папка под критерий эвристики
            is_match = "antigravity" in dirpath.lower() or dirpath == root or root == cwd

            if is_match:
                if search_type == "ide":
                    # Ищем признаки Antigravity IDE
                    for sub in [
                        os.path.join("resources", "app", "out", "main.js"),
                        os.path.join("resources", "app", "main.js"),
                        os.path.join("out", "main.js"),
                        "main.js",
                    ]:
                        if os.path.exists(os.path.join(dirpath, sub)):
                            if dirpath not in candidates:
                                candidates.append(dirpath)
                                label = "Antigravity IDE"
                                try:
                                    from patcher.utils.console import ok
                                    ok(f"Found portable {label} at: {dirpath}")
                                except Exception:
                                    print(f"  [+] Found portable {label} at: {dirpath}")
                                break
                elif search_type == "antigravity":
                    # Ищем признаки Antigravity
                    if os.path.exists(os.path.join(dirpath, "resources", "app.asar")) or \
                       os.path.exists(os.path.join(dirpath, "resources", "app1.asar")):
                        if dirpath not in candidates:
                            candidates.append(dirpath)
                            label = "Antigravity"
                            try:
                                from patcher.utils.console import ok
                                ok(f"Found portable {label} at: {dirpath}")
                            except Exception:
                                print(f"  [+] Found portable {label} at: {dirpath}")

        if visited_dirs > max_dirs:
            break

    return candidates


def find_install_root():
    candidates = []

    if sys.platform == "darwin":
        # На macOS приложение — .app-бандл, main.js лежит внутри Contents/Resources/app
        mac_candidates = [
            "/Applications/Antigravity IDE.app",
            os.path.expanduser("~/Applications/Antigravity IDE.app"),
            "/Applications/antigravity ide.app",
            os.path.expanduser("~/Applications/antigravity ide.app"),
        ]
        for app in mac_candidates:
            candidates.append(os.path.join(app, "Contents", "Resources", "app"))
    elif os.name == "posix":
        candidates.extend([
            "/usr/share/antigravity-ide",
            "/opt/Antigravity IDE",
            "/opt/antigravity-ide",
            "/opt/antigravity ide",
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

    found_standard = ""
    for path in candidates:
        for sub in [
            os.path.join("resources", "app", "out", "main.js"),
            os.path.join("resources", "app", "main.js"),
            os.path.join("out", "main.js"),
            "main.js",
        ]:
            if os.path.exists(os.path.join(path, sub)):
                found_standard = path
                break
        if found_standard:
            break

    # Always execute portable search to print matches for visibility
    portable = find_portable_candidates("ide")

    if found_standard:
        return found_standard

    if portable:
        return portable[0]

    return ""

    return ""


def find_main_js(root):
    # macOS: пользователь может передать путь к .app-бандлу напрямую
    if sys.platform == "darwin" and root.lower().endswith(".app") and os.path.isdir(root):
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


def get_ag_version(main_js_path):
    """Читает версию Antigravity IDE из реестра Windows или package.json на Linux.
    Возвращает (version_str, is_pkg_mgr).
    """
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
                        return ver, True
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
                        return ver, True
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
                        return ver, False
                except Exception:
                    pass
        return None, False

    if os.name == "nt":
        try:
            import winreg
            for hive in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
                try:
                    with winreg.OpenKey(hive, AG_REGISTRY_SUBKEY) as key:
                        display_ver, _ = winreg.QueryValueEx(key, "DisplayVersion")
                        if display_ver and display_ver.strip():
                            return display_ver.strip(), True
                except OSError:
                    pass
        except ImportError:
            pass

    return None, False


def check_ag_version(main_js_path):
    """
    Проверяет версию Antigravity IDE.
    Возвращает (VersionStatus, detected_version_str | None).
    """
    ver_str, is_pkg_mgr = get_ag_version(main_js_path)

    if ver_str is None:
        return VersionStatus.NOT_FOUND, None

    try:
        detected = Version(ver_str)
        
        # Минимальная версия: 1.107.0 для кастомных Linux билдов, иначе MIN_AG_VERSION
        min_ver_str = MIN_AG_VERSION
        if os.name == "posix" and sys.platform != "darwin" and not is_pkg_mgr:
            min_ver_str = "1.107.0"
            
        minimum = Version(min_ver_str)
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


def assign_custom_path(raw_path):
    from patcher.asar.discovery import resolve_antigravity_paths

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
