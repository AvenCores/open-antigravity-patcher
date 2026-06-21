import os
import hashlib
import time
import shutil
import subprocess

try:
    import pwd
except ImportError:
    pwd = None


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
    fix_posix_permissions(backup_path)
    return backup_path


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
    import sys
    if sys.platform != "darwin":
        return

    from patcher.utils.console import info, ok, warn

    app_path = find_app_bundle(main_js_path)
    if not app_path:
        # main.js лежит не внутри .app (например, portable-копия) — пропускаем
        return

    info(f"Re-signing {os.path.basename(app_path)} (ad-hoc)...")
    try:
        subprocess.run(
            ["codesign", "--force", "--deep", "--sign", "-", app_path],
            check=True, capture_output=True, text=True,
        )
        ok("Ad-hoc signature applied")
    except FileNotFoundError:
        warn("codesign not found - install Xcode Command Line Tools")
        return
    except subprocess.CalledProcessError as e:
        stderr = (e.stderr or "").strip()
        warn(f"codesign failed: {stderr}")
        return

    try:
        subprocess.run(
            ["xattr", "-dr", "com.apple.quarantine", app_path],
            check=False, capture_output=True,
        )
    except FileNotFoundError:
        pass
