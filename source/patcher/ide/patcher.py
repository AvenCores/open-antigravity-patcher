import os
import sys
import re
import json
import time
import shutil

from patcher.constants import (
    AUTH_PATCH_SWITCH_VERSION,
    RUNTIME_SETTINGS_SWITCH_VERSION,
    CLOUD_CODE_ENDPOINT,
    RUNTIME_EXPERIMENTS_VALUE,
    MIN_AG_VERSION,
    RE_AUTH_IS_GOOGLE_INTERNAL,
    RE_AUTH_IS_GOOGLE_INTERNAL_OLD,
    RE_AUTH_IS_GOOGLE_INTERNAL_NEW,
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
)
from patcher.ide.discovery import (
    check_ag_version,
    parse_version_safe,
    VersionStatus,
)


RE_IF_INTERNAL = re.compile(r"if\(this\.([a-zA-Z_$]+)\.isGoogleInternal\)")


def _patch_is_google_internal(content):
    """if(isGoogleInternal) → if(true) — forces internal Google path bypassing geo/eligibility checks."""
    matches = [m.group(0) for m in RE_IF_INTERNAL.finditer(content)]
    new_content = RE_IF_INTERNAL.sub("if(true)", content)
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
    data_dir = os.path.dirname(settings_dir)
    if not os.path.isdir(settings_dir):
        try:
            os.makedirs(settings_dir, exist_ok=True)
            # Fix permissions on POSIX if we just created the dir as root
            fix_posix_permissions(data_dir)
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
        fix_posix_permissions(settings_path)
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
    applied = result.get("Applied", False)
    detail = result.get("Detail", "")
    if not applied and detail.startswith("skipped"):
        applied = None
    step(result["Name"], applied, detail)


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
    runtime_settings_checked = False

    if current_is_patched:
        hint("File appears already patched.")
        info("Applying runtime settings workaround...")
        print_runtime_settings_result(patch_runtime_settings(parsed_version))
        runtime_settings_checked = True
        if not confirmed("Apply main.js patches anyway?"):
            return

    # --- БЭКАП — копируем файл ДО любых изменений ---
    backup_path = main_js_path + ".bak"

    if not os.path.exists(backup_path) and not current_is_patched:
        info("Creating backup...")
        try:
            shutil.copy2(main_js_path, backup_path)
            fix_posix_permissions(backup_path)
            ok(f"Backup: {os.path.basename(backup_path)} "
               f"({format_bytes(file_size(backup_path))})")
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

    # Для v1.22+ auth-патч выбирается по версии: <1.23 старый, >=1.23 новый.
    new_content, results = apply_patches_minimal(content, ag_version=parsed_version)

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

    hash_after = file_hash(main_js_path)
    resign_macos_bundle(main_js_path)
    if not runtime_settings_checked:
        info("Applying runtime settings workaround...")
        print_runtime_settings_result(patch_runtime_settings(parsed_version))

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

    # Разделяем "не найден" и "нечитаем"
    if not os.path.exists(backup_path):
        err(f"Backup file not found: {backup_path}")
        return
    try:
        with open(backup_path, "r", encoding="utf-8") as f:
            data = f.read()
    except Exception as e:
        err(f"Could not read backup: {e}")
        return

    # Проверка размера бэкапа
    backup_size = file_size(backup_path)
    if backup_size <= 2048:
        err("Backup looks too small — may be corrupted!")
        if not confirmed("Restore anyway?"):
            hint("Restore cancelled.")
            return

    # Предупреждение, если бэкап сам является пропатченной версией
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

    # Атомарная запись через временный файл
    tmp_path = main_js_path + ".tmp"
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            f.write(data)
        os.replace(tmp_path, main_js_path)
        fix_posix_permissions(main_js_path)
    except Exception as e:
        err(f"Restore error: {e}")
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass
        return

    hash_after = file_hash(main_js_path)
    resign_macos_bundle(main_js_path)

    from patcher.cli import print_target_info
    print_target_info(main_js_path, show_search_line=show_search_line)
    print()
    panel_rows = [("Target", os.path.basename(main_js_path))]
    if hash_before and hash_after and hash_before != hash_after:
        panel_rows.append(("Before", f"{hash_before[:8]}...{hash_before[56:]}"))
        panel_rows.append(("After", f"{hash_after[:8]}...{hash_after[56:]}"))
    panel_rows.append(("Done", time.strftime('%H:%M:%S')))
    print_panel("RESTORE COMPLETE", panel_rows)
