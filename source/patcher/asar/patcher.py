import os
import json
import shutil
import subprocess
import tempfile
import time

try:
    import pwd
except ImportError:
    pwd = None

from patcher.constants import (
    ANTIGRAVITY_INJECTION_CODE_TEMPLATE,
    LOCAL_PATCH_SERVER_KEY,
    LOCAL_PATCH_SERVER_CERT,
)
from patcher.utils.console import (
    info,
    hint,
    ok,
    warn,
    err,
    step,
    print_panel,
)
from patcher.utils.file import (
    file_size,
    format_bytes,
    fix_posix_permissions,
    resign_macos_bundle,
)
from patcher.asar.discovery import resolve_antigravity_paths, is_antigravity_patched
from patcher.asar.archive import extract_asar, pack_asar


def patch_antigravity_main_js(dest_folder, rollback=False):
    main_js_path = os.path.join(dest_folder, 'dist', 'main.js')
    backup_path = main_js_path + '.bak'

    if not os.path.exists(main_js_path):
        err(f"main.js not found at {main_js_path}")
        return False

    with open(main_js_path, 'r', encoding='utf-8') as f:
        content = f.read()

    escaped_dest_folder = dest_folder.replace("\\", "/")
    injection_code = ANTIGRAVITY_INJECTION_CODE_TEMPLATE.replace(
        "{dest_folder}", escaped_dest_folder
    ).replace(
        "{key_pem}", LOCAL_PATCH_SERVER_KEY.replace("\n", "\\n")
    ).replace(
        "{cert_pem}", LOCAL_PATCH_SERVER_CERT.replace("\n", "\\n")
    )

    if rollback:
        if injection_code in content:
            patched_content = content.replace(injection_code, "")
            with open(main_js_path, 'w', encoding='utf-8') as f:
                f.write(patched_content)
            ok("Rolled back patch by removing the injected lines directly.")
            return True
        elif os.path.exists(backup_path):
            shutil.copy2(backup_path, main_js_path)
            ok("Rolled back patch using the backup file (main.js.bak).")
            return True
        else:
            err("Patch not found in main.js and backup file does not exist.")
            return False

    if not os.path.exists(backup_path):
        shutil.copy2(main_js_path, backup_path)
        info("Created backup of original main.js inside temp folder.")

    target_str = "(0, ipcHandlers_1.registerIpcHandlers)(storageManager);"
    if "patchFrontendMainJs" in content:
        hint("Patch already applied to main.js.")
        return True
    if "downloaded_frontend_main.js" in content and os.path.exists(backup_path):
        with open(backup_path, 'r', encoding='utf-8') as f:
            content = f.read()
        hint("Found old download-only patch; restored backup content before applying frontend patch proxy.")

    # On some systems (especially Windows with IPv6 enabled) the language server
    # binds to "localhost" which may resolve to ::1, while Electron loads
    # https://127.0.0.1:<port>/ and times out. Use localhost so the client resolves
    # to the same address family the server bound to.
    if "https://127.0.0.1:" in content:
        content = content.replace("https://127.0.0.1:", "https://localhost:")
        info("Switched language server URLs from 127.0.0.1 to localhost.")

    if target_str not in content:
        err(f"Target line '{target_str}' not found in main.js")
        return False

    patched_content = content.replace(target_str, target_str + injection_code)

    with open(main_js_path, 'w', encoding='utf-8') as f:
        f.write(patched_content)

    ok("Patched main.js inside extracted ASAR.")
    return True


def do_patch_antigravity(antigravity_root):
    from patcher.cli import confirmed
    from patcher.utils.captcha import confirm_with_captcha

    if not antigravity_root or not os.path.isdir(antigravity_root):
        err(f"Antigravity root path not found: {antigravity_root}")
        return

    asar_path, exe_path = resolve_antigravity_paths(antigravity_root)
    if not os.path.exists(asar_path):
        err(f"ASAR file not found: {asar_path}")
        return

    if is_antigravity_patched(asar_path):
        hint("Antigravity appears already patched.")
        if not confirm_with_captcha("Apply patch anyway?"):
            return

    source_asar_path = asar_path + ".bak"
    legacy_backup = os.path.join(os.path.dirname(asar_path), "app_original.asar")
    if os.path.exists(legacy_backup) and not os.path.exists(source_asar_path):
        source_asar_path = legacy_backup

    if not os.path.exists(source_asar_path):
        info("Creating backup of original ASAR...")
        try:
            shutil.copy2(asar_path, source_asar_path)
            fix_posix_permissions(source_asar_path)
            ok(f"Backup: {os.path.basename(source_asar_path)} ({format_bytes(file_size(source_asar_path))})")
        except Exception as e:
            err(f"Backup error: {e}")
            return
    else:
        hint(f"Backup of original ASAR already exists: {os.path.basename(source_asar_path)}")

    temp_dir = os.path.realpath(tempfile.gettempdir())
    dest_folder = os.path.join(temp_dir, "ag_patcher_temp")

    if os.path.exists(dest_folder):
        try:
            shutil.rmtree(dest_folder)
        except Exception:
            pass
    os.makedirs(dest_folder, exist_ok=True)
    fix_posix_permissions(dest_folder)

    print()

    # Checklist: extract -> patch -> pack -> verify.
    info("Extracting ASAR archive...")
    success = extract_asar(source_asar_path, dest_folder)
    step("Extract ASAR", success, os.path.basename(source_asar_path))
    if not success:
        err("Extraction failed.")
        return

    info("Modifying files...")
    patch_ok = patch_antigravity_main_js(dest_folder, rollback=False)
    step("Patch main.js", patch_ok)
    if not patch_ok:
        err("Patching main.js failed.")
        return

    info("Packing ASAR archive...")
    pack_ok = pack_asar(dest_folder, asar_path, reference_asar_path=source_asar_path)
    step("Pack ASAR", pack_ok)
    if not pack_ok:
        err("Packing failed.")
        return

    fix_posix_permissions(asar_path)
    if os.path.exists(asar_path + ".unpacked"):
        fix_posix_permissions(asar_path + ".unpacked")
    resign_macos_bundle(asar_path)

    verify_detail = "skipped (no executable)"
    verified_ok = None
    if os.path.exists(exe_path):
        info(f"Launching application to verify: {exe_path}")
        target_file = os.path.join(dest_folder, "frontend_patch_result.json")
        if os.path.exists(target_file):
            try:
                os.remove(target_file)
            except Exception:
                pass

        try:
            popen_kwargs = {"cwd": antigravity_root, "env": os.environ.copy()}
            if os.name == "posix" and os.getuid() == 0:
                sudo_uid = os.environ.get("SUDO_UID")
                sudo_gid = os.environ.get("SUDO_GID")
                if sudo_uid and sudo_gid:
                    def drop_privs():
                        os.setgid(int(sudo_gid))
                        os.setuid(int(sudo_uid))
                    popen_kwargs["preexec_fn"] = drop_privs

                    sudo_user = os.environ.get("SUDO_USER")
                    if sudo_user and pwd:
                        try:
                            user_info = pwd.getpwnam(sudo_user)
                            popen_kwargs["env"]["HOME"] = user_info.pw_dir
                            popen_kwargs["env"]["USER"] = sudo_user
                            popen_kwargs["env"]["LOGNAME"] = sudo_user
                        except Exception:
                            pass

            process = subprocess.Popen([exe_path], **popen_kwargs)
            info("Waiting for frontend_patch_result.json to be written...")

            start_time = time.time()
            timeout = 120
            patched = False
            verification = None

            while time.time() - start_time < timeout:
                if os.path.exists(target_file) and os.path.getsize(target_file) > 0:
                    patched = True
                    try:
                        with open(target_file, "r", encoding="utf-8") as f:
                            verification = json.load(f)
                    except Exception:
                        verification = None
                    break
                time.sleep(0.5)

            if patched and isinstance(verification, dict) and verification.get("verified"):
                verified_ok = True
                verify_detail = os.path.basename(target_file)
                ok(f"Frontend patch result verified: {target_file}")
            elif patched:
                verified_ok = False
                verify_detail = "verification failed"
                warn(f"Frontend patch result was written but verification failed: {target_file}")
                if isinstance(verification, dict):
                    for result in verification.get("results", []):
                        status = "applied" if result.get("applied") else "not applied"
                        detail = result.get("detail", "")
                        print(f"      - {result.get('name', 'patch')}: {status}; {detail}")
            else:
                verified_ok = False
                verify_detail = "verification timed out"
                warn("Timeout: frontend_patch_result.json was not written.")
                hint("The patch was applied, but verification timed out. You may need to sign in manually.")

            info("Stopping the application...")
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                warn("Forcing application to stop...")
                process.kill()
                process.wait()
        except Exception as e:
            verified_ok = False
            verify_detail = f"launch error: {e}"
            warn(f"Error launching/stopping application: {e}")
    else:
        warn(f"Executable not found at {exe_path}. Cannot auto-verify.")

    step("Verify frontend", verified_ok, verify_detail)
    print()
    print_panel("PATCH COMPLETE", [
        ("Target", os.path.basename(asar_path)),
        ("Backup", f"{os.path.basename(source_asar_path)} ({format_bytes(file_size(source_asar_path))})"),
    ])


def do_restore_antigravity(antigravity_root):
    from patcher.cli import confirmed

    if not antigravity_root or not os.path.isdir(antigravity_root):
        err(f"Antigravity root path not found: {antigravity_root}")
        return

    asar_path, exe_path = resolve_antigravity_paths(antigravity_root)
    source_asar_path = asar_path + ".bak"
    legacy_backup = os.path.join(os.path.dirname(asar_path), "app_original.asar")
    if os.path.exists(legacy_backup) and not os.path.exists(source_asar_path):
        source_asar_path = legacy_backup

    if not os.path.exists(source_asar_path):
        err(f"Original ASAR backup not found: {source_asar_path}")
        info("Attempting in-place rollback by extracting and patching...")
        if not os.path.exists(asar_path):
            err(f"Target ASAR file not found: {asar_path}")
            return

        temp_dir = os.path.realpath(tempfile.gettempdir())
        dest_folder = os.path.join(temp_dir, "ag_patcher_temp")

        if os.path.exists(dest_folder):
            try:
                shutil.rmtree(dest_folder)
            except Exception:
                pass
        os.makedirs(dest_folder, exist_ok=True)

        print()
        info("Extracting ASAR...")
        extract_ok = extract_asar(asar_path, dest_folder)
        step("Extract ASAR", extract_ok, os.path.basename(asar_path))
        if not extract_ok:
            err("Extraction failed.")
            return

        info("Performing rollback in main.js...")
        rollback_ok = patch_antigravity_main_js(dest_folder, rollback=True)
        step("Rollback main.js", rollback_ok)
        if not rollback_ok:
            err("Rollback failed (patch not found or backup missing).")
            return

        info("Packing ASAR...")
        pack_ok = pack_asar(dest_folder, asar_path)
        step("Pack ASAR", pack_ok)
        if not pack_ok:
            err("Packing failed.")
            return

        fix_posix_permissions(asar_path)
        if os.path.exists(asar_path + ".unpacked"):
            fix_posix_permissions(asar_path + ".unpacked")
        resign_macos_bundle(asar_path)
        print()
        print_panel("RESTORE COMPLETE", [
            ("Target", os.path.basename(asar_path)),
            ("Mode", "in-place rollback"),
        ])
        return

    info(f"Found original ASAR backup: {os.path.basename(source_asar_path)}")
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
        fix_posix_permissions(asar_path)
        resign_macos_bundle(asar_path)
        print()
        print_panel("RESTORE COMPLETE", [
            ("Target", os.path.basename(asar_path)),
            ("Backup", f"{os.path.basename(source_asar_path)} (kept)"),
        ])
    except Exception as e:
        err(f"Failed to restore backup: {e}")
