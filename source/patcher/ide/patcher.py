import os
import sys
import re
import time
import shutil

from patcher.constants import (
    MIN_AG_VERSION,
    COLOR_CYAN,
)
from patcher.utils.console import (
    color,
    info,
    hint,
    ok,
    warn,
    err,
    step,
    print_panel,
)
from patcher.utils.admin import terminate_processes
from patcher.utils.file import (
    file_hash,
    file_size,
    format_bytes,
    fix_posix_permissions,
    backup_json_file,
    get_posix_invoking_user_home,
    resign_macos_bundle,
    remove_macos_immutable_flags,
    remove_macos_quarantine,
    find_app_bundle,
)
from patcher.ide.discovery import (
    check_ag_version,
    parse_version_safe,
    VersionStatus,
)

IDE_RE = re.compile(r"(resetIsTierGCPTos\(\),)this\.[A-Za-z_$0-9]+\.isGoogleInternal")
IDE_DONE = "resetIsTierGCPTos(),true"


def _ide_cache_dirs():
    """VS Code CachedData / Code Cache dirs to drop after patching main.js, so the IDE
    recompiles the patched bytes instead of replaying a stale compile cache. The user-data
    folder is the product nameLong ('Antigravity IDE') under each OS's app-data root."""
    home = os.path.expanduser("~")
    if os.name == "nt":
        bases = [os.path.expandvars(p) for p in
                 (r"%USERPROFILE%\scoop\persist\antigravity-ide\data\user-data",
                  r"%APPDATA%\Antigravity IDE")]
    elif sys.platform == "darwin":
        bases = [os.path.join(home, "Library", "Application Support", "Antigravity IDE")]
    else:                                                  # Linux (respect XDG_CONFIG_HOME)
        cfg = os.environ.get("XDG_CONFIG_HOME") or os.path.join(home, ".config")
        bases = [os.path.join(cfg, "Antigravity IDE")]
    dirs = []
    for base in bases:
        dirs += [os.path.join(base, "CachedData"),
                 os.path.join(base, "Code Cache", "js")]
    return dirs


def apply_patches(content, ag_version=None):
    """Применяет патч isGoogleInternal для IDE из manager.py."""
    results = []
    matches = [m.group(0) for m in IDE_RE.finditer(content)]
    new_content = IDE_RE.sub(r"\1true", content)
    applied = new_content != content
    results.append({
        "Name": "isGoogleInternal -> true (auth)",
        "Applied": applied,
        "Detail": f"replaced {len(matches)} occurrences" if applied else "pattern not found",
    })
    return new_content, results


def is_already_patched(content):
    return IDE_DONE in content and not IDE_RE.search(content)


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


def warn_about_unsafe_backup(main_js_path, installed_version_str=None, current_content=None):
    backup_path = main_js_path + ".bak"
    if not os.path.exists(backup_path):
        return True, False

    backup_size = file_size(backup_path)
    current_size = file_size(main_js_path)
    warnings = []

    if backup_size <= 2048:
        try:
            with open(backup_path, "r", encoding="utf-8") as f:
                backup_content = f.read()
            if len(backup_content.strip()) <= 512:
                warnings.append(
                    f"backup size is only {format_bytes(backup_size)} and it looks almost empty"
                )
        except Exception as e:
            warn(f"Backup check error: {e}")
            return False, False
    elif backup_size < 4096 or (current_size > 0 and backup_size < current_size // 10):
        warnings.append(
            f"backup is much smaller than expected "
            f"({format_bytes(backup_size)} vs {format_bytes(current_size)})"
        )

    if not warnings:
        return True, False

    for warning in warnings:
        warn(f"Backup warning: {warning}")
    warn("Restoring this backup may break Antigravity IDE.")
    warn(f"Backup kept: {os.path.basename(backup_path)}")
    return True, True


def do_patch(main_js_path, show_search_line=False):
    from patcher.cli import confirmed
    from patcher.utils.captcha import confirm_with_captcha

    if not os.path.isfile(main_js_path):
        err(f"Target is not a file: {main_js_path}")
        hint("Please select a valid main.js file or Antigravity IDE folder.")
        return

    ver_status, ver_str = check_ag_version(main_js_path)
    parsed_version = parse_version_safe(ver_str)

    if ver_status == VersionStatus.TOO_OLD:
        err(f"Unsupported version: {ver_str}")
        err(f"Minimum required: {MIN_AG_VERSION}")
        hint("Please update Antigravity IDE and try again.")
        if not confirmed("Proceed anyway?"):
            return
    elif ver_status == VersionStatus.NOT_FOUND:
        warn("Could not detect Antigravity IDE version (registry key not found).")
        if not confirmed("Proceed without version check?"):
            return
    elif ver_status == VersionStatus.PARSE_ERROR:
        warn(f"Could not parse version string: {ver_str}")
        if not confirmed("Proceed anyway?"):
            return
    # VersionStatus.OK — продолжаем без вопросов

    try:
        with open(main_js_path, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        err(f"Read error: {e}")
        return

    current_is_patched = is_already_patched(content)

    if current_is_patched:
        hint("File appears already patched.")
        if not confirm_with_captcha("Apply main.js patches anyway?"):
            return

    # --- БЭКАП ---
    backup_path = main_js_path + ".bak"

    if not os.path.exists(backup_path) and not current_is_patched:
        info("Creating backup...")
        if sys.platform == "darwin":
            app_path = find_app_bundle(main_js_path)
            if app_path:
                remove_macos_immutable_flags(app_path)
                remove_macos_quarantine(app_path)
        try:
            shutil.copy2(main_js_path, backup_path)
            fix_posix_permissions(backup_path)
            ok(f"Backup: {os.path.basename(backup_path)} "
               f"({format_bytes(file_size(backup_path))})")
        except PermissionError as e:
            if sys.platform == "darwin":
                warn(f"Permission denied, retrying after removing flags...")
                app_path = find_app_bundle(main_js_path)
                if app_path:
                    remove_macos_immutable_flags(app_path)
                    remove_macos_quarantine(app_path)
                try:
                    shutil.copy2(main_js_path, backup_path)
                    fix_posix_permissions(backup_path)
                    ok(f"Backup: {os.path.basename(backup_path)} "
                       f"({format_bytes(file_size(backup_path))})")
                except Exception as e2:
                    err(f"Backup error: {e2}")
                    return
            else:
                err(f"Backup error: {e}")
                return
        except Exception as e:
            err(f"Backup error: {e}")
            return
    elif os.path.exists(backup_path):
        hint("Backup already exists — skipping")
    elif current_is_patched:
        warn("main.js is already patched — no backup needed")

    hash_before = file_hash(main_js_path)

    info("Applying patches...")
    print()

    new_content, results = apply_patches(content, ag_version=parsed_version)

    applied = 0
    for r in results:
        if r.get("Applied"):
            applied += 1
        step(r["Name"], r.get("Applied", False), r.get("Detail", ""))
    print()

    if applied == 0:
        err("No patches applied.")
        return

    write_success = False
    for attempt in range(2):
        try:
            with open(main_js_path, "w", encoding="utf-8") as f:
                f.write(new_content)
            fix_posix_permissions(main_js_path)
            write_success = True
            break
        except PermissionError as e:
            if attempt == 0:
                if sys.platform == "darwin":
                    warn(f"Permission denied, retrying after removing flags...")
                    app_path = find_app_bundle(main_js_path)
                    if app_path:
                        remove_macos_immutable_flags(app_path)
                        remove_macos_quarantine(app_path)
                    time.sleep(0.5)
                    continue
                warn(f"Permission denied (file locked): {e}")
                if confirmed("Would you like to automatically close running Antigravity processes and retry?"):
                    terminate_processes(["Antigravity", "Antigravity IDE", "antigravity", "antigravity-ide"])
                    time.sleep(1.5)
                    continue
            err(f"Write error (Permission denied): {e}")
            return
        except Exception as e:
            err(f"Write error: {e}")
            return

    if not write_success:
        return

    # Очистка кэша скомпилированных JS файлов VS Code (CachedData / Code Cache)
    info("Clearing IDE compile caches...")
    for c in _ide_cache_dirs():
        try:
            if os.path.isdir(c):
                shutil.rmtree(c, ignore_errors=True)
        except Exception:
            pass

    hash_after = file_hash(main_js_path)
    resign_macos_bundle(main_js_path)

    panel_rows = [
        ("Target", os.path.basename(main_js_path)),
        ("Patches", f"{applied}/{len(results)} applied"),
    ]
    if os.path.exists(backup_path):
        panel_rows.append(
            ("Backup", f"{os.path.basename(backup_path)} ({format_bytes(file_size(backup_path))})")
        )
    if hash_before and hash_after:
        panel_rows.append(("Before", f"{hash_before[:8]}...{hash_before[56:]}"))
        panel_rows.append(("After", f"{hash_after[:8]}...{hash_after[56:]}"))
    panel_rows.append(("Done", time.strftime('%H:%M:%S')))
    print_panel("PATCH COMPLETE", panel_rows)
    hint("Restart Antigravity IDE and sign in.")


def do_fix_429():
    from patcher.cli import confirmed

    data_dir = get_user_data_dir()
    if not data_dir or not os.path.isdir(data_dir):
        err("Antigravity IDE data directory not found.")
        return

    info(f"Data directory: {color(data_dir, COLOR_CYAN)}")
    warn("This will reset your Antigravity IDE configuration (tokens, quota).")
    warn("Dialogues will be preserved, but you will need to sign in again.")
    err("Ensure Antigravity IDE is COMPLETELY closed before proceeding.")

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

    info(f"Moving current data to: {os.path.basename(backup_dir)}...")

    move_success = False
    for attempt in range(2):
        try:
            shutil.move(data_dir, backup_dir)
            move_success = True
            break
        except PermissionError as e:
            if attempt == 0:
                warn(f"Permission denied (files locked): {e}")
                if confirmed("Would you like to automatically close running Antigravity processes and retry?"):
                    terminate_processes(["Antigravity", "Antigravity IDE", "antigravity", "antigravity-ide"])
                    time.sleep(1.5)
                    continue
            err("Permission denied: Could not move data directory.")
            err("Antigravity IDE is likely still running or holding files.")
            hint("Close Antigravity IDE completely (check Task Manager) and try again.")
            return
        except Exception as e:
            err(f"Failed to move data directory: {e}")
            hint("Try running the patcher as administrator.")
            return

    if not move_success:
        return

    ok("Data moved to backup")
    info("Creating fresh configuration...")

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
                info(f"Restoring {folder}...")
                try:
                    shutil.copytree(src, dst)
                    restored_count += 1
                except Exception as e:
                    warn(f"Could not restore {folder}: {e}")

        if restored_count > 0:
            ok(f"Restored {restored_count} storage folder(s)")
        else:
            hint("No storage folders were restored")

        # Fix permissions on POSIX if running as root
        fix_posix_permissions(data_dir)

        print_panel("HTTP 429 FIX APPLIED", [
            ("Backup", os.path.basename(backup_dir)),
            ("Folders", f"{restored_count} restored"),
        ])
        hint("What to do now:")
        print("      1. Start Antigravity IDE.")
        print("      2. Sign in to your account.")
        print("      3. If you still see errors, run 'Apply patch' (Option 1) again.")
        warn("Note: VPNs or other bypass methods might be detected by Google and cause 429 errors.")
        hint(f"Your backup is safe at: {backup_dir}")

    except Exception as e:
        err(f"Error during restoration: {e}")
        warn(f"Your backup is preserved at: {backup_dir}")
        hint("You can try to restore it manually if needed.")


def do_restore(main_js_path, show_search_line=False):
    from patcher.cli import confirmed

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

    if not os.path.exists(backup_path):
        err(f"Backup file not found: {backup_path}")
        return
    try:
        with open(backup_path, "r", encoding="utf-8") as f:
            data = f.read()
    except Exception as e:
        err(f"Could not read backup: {e}")
        return

    backup_size = file_size(backup_path)
    if backup_size <= 2048:
        err("Backup looks too small — may be corrupted!")
        if not confirmed("Restore anyway?"):
            hint("Restore cancelled.")
            return

    if is_already_patched(data):
        warn("Backup itself appears to be patched!")
        if not confirmed("Restore this patched backup?"):
            hint("Restore cancelled.")
            return

    restore_question = "Restore this backup anyway?" if backup_has_warnings else "Restore backup?"
    if not confirmed(restore_question):
        hint("Restore cancelled.")
        return

    hash_before = file_hash(main_js_path)

    tmp_path = main_js_path + ".tmp"
    try:
        if sys.platform == "darwin":
            app_path = find_app_bundle(main_js_path)
            if app_path:
                remove_macos_immutable_flags(app_path)
                remove_macos_quarantine(app_path)
        with open(tmp_path, "w", encoding="utf-8") as f:
            f.write(data)
        os.replace(tmp_path, main_js_path)
        fix_posix_permissions(main_js_path)
    except Exception as e:
        if sys.platform == "darwin":
            warn(f"Restore failed, retrying after removing flags...")
            app_path = find_app_bundle(main_js_path)
            if app_path:
                remove_macos_immutable_flags(app_path)
                remove_macos_quarantine(app_path)
            try:
                if not os.path.exists(tmp_path):
                     with open(tmp_path, "w", encoding="utf-8") as f:
                         f.write(data)
                os.replace(tmp_path, main_js_path)
                fix_posix_permissions(main_js_path)
            except Exception as e2:
                err(f"Restore error: {e2}")
                if os.path.exists(tmp_path):
                    try:
                        os.remove(tmp_path)
                    except Exception:
                        pass
                return
        else:
            err(f"Restore error: {e}")
            if os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass
            return

    hash_after = file_hash(main_js_path)
    resign_macos_bundle(main_js_path)

    panel_rows = [("Target", os.path.basename(main_js_path))]
    if hash_before and hash_after and hash_before != hash_after:
        panel_rows.append(("Before", f"{hash_before[:8]}...{hash_before[56:]}"))
        panel_rows.append(("After", f"{hash_after[:8]}...{hash_after[56:]}"))
    panel_rows.append(("Done", time.strftime('%H:%M:%S')))
    print_panel("RESTORE COMPLETE", panel_rows)
