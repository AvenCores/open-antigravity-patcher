import os
import re
import mmap
import shutil
import contextlib
import filecmp
from packaging.version import Version
from enum import Enum

from patcher.constants import COLOR_CYAN, MIN_ANTIGRAVITY_VERSION
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
from patcher.utils.file import (
    file_hash,
    file_size,
    format_bytes,
    fix_posix_permissions,
    resign_macos_bundle,
    resign_macos_binary,
)
from patcher.utils.update import handle_patch_failure
from patcher.utils.admin import terminate_processes

BAK_EXT = ".agybak"


class VersionStatus(Enum):
    OK = "ok"
    TOO_OLD = "too_old"
    NOT_FOUND = "not_found"
    PARSE_ERROR = "parse_error"


class Gate:
    def __init__(self, sig, patched, fix, offset=0, desc=""):
        self.sig = re.compile(sig, re.S)
        self.patched = re.compile(patched, re.S)
        self.fix = fix
        self.offset = offset
        self.desc = desc

    def find(self, data):
        m = self.patched.search(data)
        if m:
            return ("patched", m.start() + self.offset)
        m = self.sig.search(data)
        if not m:
            raise LookupError("gate signature not found (unsupported version?)")
        if self.sig.search(data, m.end()):
            raise LookupError("gate signature is not unique — refusing to guess")
        return ("unpatched", m.start() + self.offset)


# language_server.exe / language_server (Go binary) auth validator gate:
# cmp byte[rax+8],0 ; je short  ->  mov byte[rax+8],1 ; nop*2 (x64)
# ldr x8, [x1, #8] -> movz x8, #1 (arm64)
# (hasValidAuth=true)
# (wildcarded/re.S displacements)
MANAGER_GATES = [
    Gate(
        rb"\x80\x78\x08\x00\x74.\x48\x8b.\x24.\x48\x89.\x60",
        rb"\xc6\x40\x08\x01\x90\x90\x48\x8b.\x24.\x48\x89.\x60",
        b"\xc6\x40\x08\x01\x90\x90",
        offset=0,
        desc="hasValidAuth=true (x64)",
    ),
    Gate(
        rb"\x60\x04\x00\xb4\xe0\x27\x00\xf9\xe1\x2b\x00\xf9\xe0\x03\x7c\xb2\x41\xc6\x01\xd0\x21\x20\x38\x91\xe2\x03\x40\xb2....\xe1\x27\x40\xf9\x61\x00\x00\xb4\x28\x04\x40\xf9\x02\x00\x00\x14\xe8\x03\x01\xaa\x08\x00\x00\xf9",
        rb"\x60\x04\x00\xb4\xe0\x27\x00\xf9\xe1\x2b\x00\xf9\xe0\x03\x7c\xb2\x41\xc6\x01\xd0\x21\x20\x38\x91\xe2\x03\x40\xb2....\xe1\x27\x40\xf9\x61\x00\x00\xb4\x28\x00\x80\xd2\x02\x00\x00\x14\xe8\x03\x01\xaa\x08\x00\x00\xf9",
        b"\x28\x00\x80\xd2",
        offset=40,
        desc="hasValidAuth=true (arm64)",
    )
]


from patcher.manager.discovery import find_asar_relative_to_manager, read_package_json_from_asar

def check_antigravity_version(asar_path):
    ver_str = read_package_json_from_asar(asar_path)
    if ver_str is None:
        return VersionStatus.NOT_FOUND, None

    try:
        detected = Version(ver_str)
        minimum = Version(MIN_ANTIGRAVITY_VERSION)
        status = VersionStatus.OK if detected >= minimum else VersionStatus.TOO_OLD
        return status, ver_str
    except Exception:
        return VersionStatus.PARSE_ERROR, ver_str


@contextlib.contextmanager
def _mapped(path):
    with open(path, "rb") as f:
        if os.fstat(f.fileno()).st_size == 0:
            yield b""
            return
        mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
        try:
            yield mm
        finally:
            mm.close()


def is_locked(path):
    try:
        with open(path, "r+b"):
            return False
    except OSError:
        return True


def get_status(path):
    if not path or not os.path.isfile(path):
        return ("unknown", None)
    try:
        with _mapped(path) as d:
            for gate in MANAGER_GATES:
                try:
                    state, off = gate.find(d)
                    return (state, gate)
                except LookupError:
                    continue
            return ("unknown", None)
    except OSError:
        return ("unknown", None)


def is_already_patched(path):
    return get_status(path)[0] == "patched"


def _make_backup(path):
    bak = path + BAK_EXT
    if os.path.exists(bak):
        if filecmp.cmp(path, bak, shallow=False):
            return
        info(f"Backup is stale (app updated) — refreshing {os.path.basename(path)}{BAK_EXT}")
    else:
        info(f"Creating backup -> {os.path.basename(path)}{BAK_EXT}")
    shutil.copy2(path, bak)
    fix_posix_permissions(bak)
    ok(f"Backup: {os.path.basename(bak)} ({format_bytes(file_size(bak))})")


def do_patch_manager(path):
    from patcher.cli import confirmed
    from patcher.utils.captcha import confirm_with_captcha

    if not path or not os.path.isfile(path):
        from patcher.cli import offer_download_and_block
        offer_download_and_block("Antigravity 2.0")
        return

    hash_before = file_hash(path)
    info(f"Target: {color(path, COLOR_CYAN)}")
    hint(f"Size: {color(format_bytes(file_size(path)), COLOR_CYAN)}")

    # Проверка версии Antigravity (считывается из package.json в app.asar)
    asar_path = find_asar_relative_to_manager(path)
    if asar_path:
        ver_status, ver_str = check_antigravity_version(asar_path)
        if ver_status == VersionStatus.TOO_OLD:
            err(f"Unsupported version: {ver_str}")
            err(f"Minimum required: {MIN_ANTIGRAVITY_VERSION}")
            hint("Please update Antigravity and try again.")
            if not confirmed("Proceed anyway?"):
                return
        elif ver_status == VersionStatus.NOT_FOUND:
            warn("Could not detect Antigravity version (package.json not found in ASAR).")
            if not confirmed("Proceed without version check?"):
                return
        elif ver_status == VersionStatus.PARSE_ERROR:
            warn(f"Could not parse version string: {ver_str}")
            if not confirmed("Proceed anyway?"):
                return
    print()

    write_success = False
    off = 0
    for attempt in range(2):
        if is_locked(path):
            if attempt == 0:
                warn("Binary is locked (Antigravity Manager is running).")
                if confirmed("Would you like to automatically close running Antigravity processes and retry?"):
                    terminate_processes(["Antigravity", "Antigravity IDE", "antigravity", "antigravity-ide", "language_server"])
                    import time
                    time.sleep(1.5)
                    continue
            err("File is locked — close the app first.")
            return

        matched_gate = None
        try:
            with _mapped(path) as d:
                kind = "unknown"
                for gate in MANAGER_GATES:
                    try:
                        kind, off = gate.find(d)
                        matched_gate = gate
                        break
                    except LookupError:
                        continue
                if not matched_gate:
                    err("gate signature not found (unsupported version?)")
                    handle_patch_failure()
                    return
                if kind == "patched":
                    hint("Antigravity Manager already patched.")
                    if not confirm_with_captcha("Apply patch anyway?"):
                        return
        except OSError as e:
            err(f"Read error: {e}")
            return

        _make_backup(path)

        try:
            with open(path, "r+b") as f:
                f.seek(off)
                f.write(matched_gate.fix)
                f.flush()
                os.fsync(f.fileno())
            write_success = True
            break
        except PermissionError as e:
            if attempt == 0:
                warn(f"Permission denied (file locked): {e}")
                if confirmed("Would you like to automatically close running processes and retry?"):
                    terminate_processes(["Antigravity", "Antigravity IDE", "antigravity", "antigravity-ide", "language_server"])
                    import time
                    time.sleep(1.5)
                    continue
            err(f"Write error (Permission denied): {e}")
            handle_patch_failure()
            return
        except Exception as e:
            err(f"Write error: {e}")
            handle_patch_failure()
            return

    if not write_success:
        handle_patch_failure()
        return

    hash_after = file_hash(path)
    resign_macos_bundle(path)
    resign_macos_binary(path)
    print()
    step("Patch manager binary", True, matched_gate.desc)
    print()
    panel_rows = [
        ("Target", os.path.basename(path)),
        ("Gate", f"{matched_gate.desc} @ 0x{off:x}"),
    ]
    if hash_before and hash_after:
        panel_rows.append(("Before", f"{hash_before[:8]}...{hash_before[56:]}"))
        panel_rows.append(("After", f"{hash_after[:8]}...{hash_after[56:]}"))
    print_panel("PATCH COMPLETE", panel_rows)
    hint("Restart Antigravity/Antigravity IDE for the changes to take effect.")


def do_restore_manager(path):
    from patcher.cli import confirmed

    if not os.path.isfile(path):
        err(f"Target is not a file: {path}")
        return

    bak = path + BAK_EXT
    if not os.path.exists(bak):
        warn(f"No backup for {os.path.basename(path)} (nothing to restore).")
        return

    status, _ = get_status(path)
    if status != "patched":
        warn("Manager is not patched — skipping restore (backup may be a different build).")
        if not confirmed("Restore from backup anyway?"):
            hint("Restore cancelled.")
            return

    if is_locked(path):
        err("Binary is locked — close the app first.")
        return

    if not confirmed("Restore Manager from backup?"):
        hint("Restore cancelled.")
        return

    hash_before = file_hash(path)
    try:
        shutil.copy2(bak, path)
        fix_posix_permissions(path)
    except Exception as e:
        err(f"Restore error: {e}")
        return

    hash_after = file_hash(path)
    resign_macos_bundle(path)
    resign_macos_binary(path)
    print()
    panel_rows = [("Target", os.path.basename(path))]
    if hash_before and hash_after and hash_before != hash_after:
        panel_rows.append(("Before", f"{hash_before[:8]}...{hash_before[56:]}"))
        panel_rows.append(("After", f"{hash_after[:8]}...{hash_after[56:]}"))
    print_panel("RESTORE COMPLETE", panel_rows)
